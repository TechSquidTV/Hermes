"""Validate actual connection destinations without making network requests."""

import io
import socket
from unittest.mock import Mock

import pytest
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import DownloadError

from app.services.public_network import PublicYoutubeDL, public_connection
from app.utils.urls import validate_public_url


def addresses(ip, port=80):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "192.168.1.1",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fc00::1",
        "fec0::1",
        "64:ff9b::7f00:1",
        "fe80::1",
        "::ffff:127.0.0.1",
    ],
)
def test_private_addresses_never_open_a_socket(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: addresses(ip))
    make_socket = Mock()
    monkeypatch.setattr(socket, "socket", make_socket)
    with pytest.raises(ValueError, match="public IP"):
        public_connection(("example.test", 80))
    make_socket.assert_not_called()


def test_mixed_dns_answer_is_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: addresses("93.184.216.34") + addresses("10.0.0.1"),
    )
    with pytest.raises(ValueError):
        validate_public_url("https://mixed.test/")


def test_connection_uses_validated_address_without_resolving_again(monkeypatch):
    lookup = Mock(return_value=addresses("93.184.216.34"))
    connection = Mock()
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    monkeypatch.setattr(socket, "socket", Mock(return_value=connection))
    assert public_connection(("example.test", 80), timeout=10) is connection
    lookup.assert_called_once_with("example.test", 80, type=socket.SOCK_STREAM)
    connection.connect.assert_called_once_with(("93.184.216.34", 80))


class FakeSocket:
    def __init__(self, response):
        self.response = response
        self.sent = []

    def settimeout(self, value):
        pass

    def setsockopt(self, *args):
        pass

    def connect(self, address):
        self.address = address

    def sendall(self, data):
        self.sent.append(data)

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.response)

    def close(self):
        pass


@pytest.mark.parametrize(
    "location",
    [
        "http://127.0.0.1/secret",
        "http://169.254.169.254/metadata",
        "ftp://example.test/secret",
    ],
)
def test_redirects_are_confined_by_the_real_request_handler(monkeypatch, location):
    connection = FakeSocket(
        f"HTTP/1.1 302 Found\r\nLocation: {location}\r\nContent-Length: 0\r\n\r\n".encode()
    )
    make_socket = Mock(return_value=connection)
    original = socket.getaddrinfo

    def lookup(host, port, **kwargs):
        return (
            addresses("93.184.216.34", port)
            if host == "example.test"
            else original(host, port, **kwargs)
        )

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    monkeypatch.setattr(socket, "socket", make_socket)
    with PublicYoutubeDL({"quiet": True, "proxy": ""}) as downloader:
        with pytest.raises(RequestError):
            downloader.urlopen(Request("http://example.test/redirect"))
    make_socket.assert_called_once()
    assert connection.address[0] == "93.184.216.34"
    assert b"Host: example.test" in connection.sent[0]


def test_dns_rebinding_is_checked_again_at_connection_time(monkeypatch):
    lookup = Mock(side_effect=[addresses("93.184.216.34"), addresses("127.0.0.1")])
    make_socket = Mock()
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    monkeypatch.setattr(socket, "socket", make_socket)
    validate_public_url("http://example.test/")
    with PublicYoutubeDL({"quiet": True, "proxy": ""}) as downloader:
        with pytest.raises(RequestError):
            downloader.urlopen(Request("http://example.test/"))
    make_socket.assert_not_called()


def test_http_download_uses_guarded_transport_and_preserves_host(monkeypatch, tmp_path):
    connection = FakeSocket(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nmedia")
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, **kwargs: addresses("93.184.216.34", port),
    )
    monkeypatch.setattr(socket, "socket", Mock(return_value=connection))
    with PublicYoutubeDL(
        {
            "quiet": True,
            "proxy": "",
            "external_downloader": "native",
            "noprogress": True,
        }
    ) as downloader:
        success, _ = downloader.dl(
            str(tmp_path / "video.mp4"),
            {"url": "http://example.test/video.mp4", "ext": "mp4"},
        )
    assert success
    assert (tmp_path / "video.mp4").read_bytes() == b"media"
    assert connection.address == ("93.184.216.34", 80)
    assert b"Host: example.test" in connection.sent[0]


@pytest.mark.parametrize("protocol", ["m3u8", "rtmp", "websocket_frag"])
def test_unguarded_downloaders_are_refused(protocol, tmp_path):
    with PublicYoutubeDL(
        {"quiet": True, "proxy": "", "external_downloader": "native"}
    ) as downloader:
        with pytest.raises(DownloadError, match="unsupported network downloader"):
            downloader.dl(
                str(tmp_path / "video.mp4"),
                {
                    "url": "http://example.test/live",
                    "protocol": protocol,
                    "is_live": True,
                    "ext": "mp4",
                },
            )


def test_hls_cannot_fall_back_to_ffmpeg(monkeypatch, tmp_path):
    # Byte ranges requiring unsupported encryption cause native HLS to delegate.
    manifest = '#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="http://127.0.0.1/key"\n#EXTINF:1,\nhttp://127.0.0.1/segment.ts\n#EXT-X-ENDLIST'
    with PublicYoutubeDL(
        {"quiet": True, "proxy": "", "external_downloader": "native"}
    ) as downloader:
        with pytest.raises(DownloadError, match="unsupported network downloader"):
            downloader.dl(
                str(tmp_path / "video.mp4"),
                {
                    "url": "http://example.test/video.m3u8",
                    "protocol": "m3u8_native",
                    "ext": "mp4",
                    "hls_media_playlist_data": manifest,
                },
            )


def test_hls_format_probes_cannot_select_external_downloader(monkeypatch, tmp_path):
    import yt_dlp

    native_download = Mock(return_value=(True, True))
    monkeypatch.setattr(yt_dlp.YoutubeDL, "dl", native_download)
    manifest = "#EXTM3U\n#EXTINF:1,\nhttp://example.test/segment.ts\n#EXT-X-ENDLIST"
    with PublicYoutubeDL(
        {"quiet": True, "proxy": "", "external_downloader": "native"}
    ) as downloader:
        downloader.dl(
            str(tmp_path / "probe.mp4"),
            {
                "url": "http://example.test/video.m3u8",
                "protocol": "m3u8",
                "ext": "mp4",
                "hls_media_playlist_data": manifest,
            },
            test=True,
        )
    assert native_download.call_args.args[1]["protocol"] == "m3u8_native"


def test_live_dash_format_probes_cannot_select_ffmpeg(tmp_path):
    with PublicYoutubeDL(
        {"quiet": True, "proxy": "", "external_downloader": "native"}
    ) as downloader:
        with pytest.raises(DownloadError, match="unsupported network downloader"):
            downloader.dl(
                str(tmp_path / "probe.mp4"),
                {
                    "url": "http://example.test/live",
                    "protocol": "http_dash_segments",
                    "is_live": True,
                    "ext": "mp4",
                },
                test=True,
            )


def test_https_preserves_tls_hostname_and_certificate_checks(monkeypatch):
    import ssl

    from app.services.public_network import PublicUrllibRH

    connection = FakeSocket(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nmedia")
    context = ssl.create_default_context()
    wrap = Mock(return_value=connection)
    monkeypatch.setattr(context, "wrap_socket", wrap)
    monkeypatch.setattr(PublicUrllibRH, "_make_sslcontext", Mock(return_value=context))
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, **kwargs: addresses("93.184.216.34", port),
    )
    monkeypatch.setattr(socket, "socket", Mock(return_value=connection))
    with PublicYoutubeDL({"quiet": True, "proxy": ""}) as downloader:
        with downloader.urlopen(Request("https://example.test/video.mp4")) as response:
            assert response.read() == b"media"
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    wrap.assert_called_once_with(connection, server_hostname="example.test")
    assert connection.address == ("93.184.216.34", 443)
