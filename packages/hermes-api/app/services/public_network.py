"""yt-dlp transport that confines every connection, including redirects, to public IPs.

Use only the guarded urllib handler. Connecting directly to the validated DNS
answer prevents a second lookup from bypassing validation through DNS rebinding.
"""

import functools
import http.client
import http.cookiejar
import socket
import ssl
import urllib.request
from collections.abc import Iterable
from typing import Protocol, cast

import yt_dlp
from yt_dlp.networking._urllib import HTTPHandler, UrllibRH
from yt_dlp.networking.common import RequestDirector, RequestHandler

from app.utils.urls import public_addresses, validate_public_url


def public_connection(
    address: tuple[str, int],
    timeout: float | None = None,
    source_address: tuple[str, int] | None = None,
) -> socket.socket:
    addresses = public_addresses(*address)
    last_error = None
    for family, socktype, proto, _, sockaddr in addresses:
        connection = socket.socket(family, socktype, proto)
        try:
            connection.settimeout(timeout)
            if source_address:
                connection.bind(source_address)
            connection.connect(sockaddr)
            return connection
        except OSError as error:
            last_error = error
            connection.close()
    raise OSError("Unable to connect to public host") from last_error


def _connection(
    connection_class: type[http.client.HTTPConnection],
    host: str,
    *,
    timeout: float | None = None,
    context: ssl.SSLContext | None = None,
) -> http.client.HTTPConnection:
    connection: http.client.HTTPConnection
    if issubclass(connection_class, http.client.HTTPSConnection):
        connection = connection_class(host, timeout=timeout, context=context)
    else:
        connection = connection_class(host, timeout=timeout)
    # http.client's private socket factory is intentionally replaced on this
    # connection instance only, preserving Host headers and TLS hostname checks.
    setattr(connection, "_create_connection", public_connection)
    return connection


class _OpenerHandlers(Protocol):
    handlers: list[urllib.request.BaseHandler]


class PublicHTTPHandler(HTTPHandler):
    def http_open(self, request: urllib.request.Request) -> http.client.HTTPResponse:
        validate_public_url(request.full_url, resolve=False)
        return self.do_open(
            functools.partial(_connection, http.client.HTTPConnection), request
        )

    def https_open(self, request: urllib.request.Request) -> http.client.HTTPResponse:
        validate_public_url(request.full_url, resolve=False)
        return self.do_open(
            functools.partial(_connection, http.client.HTTPSConnection),
            request,
            context=self._context,
        )


class PublicUrllibRH(UrllibRH):
    _SUPPORTED_URL_SCHEMES = ("http", "https")
    _SUPPORTED_PROXY_SCHEMES = ()

    def _create_instance(
        self,
        proxies: dict[str, str | None],
        cookiejar: http.cookiejar.CookieJar,
        legacy_ssl_support: bool | None = None,
    ) -> urllib.request.OpenerDirector:
        opener = super()._create_instance({}, cookiejar, legacy_ssl_support)
        guarded = urllib.request.OpenerDirector()
        for handler in cast(_OpenerHandlers, opener).handlers:
            if not isinstance(
                handler,
                (
                    HTTPHandler,
                    urllib.request.FTPHandler,
                    urllib.request.DataHandler,
                    urllib.request.FileHandler,
                ),
            ):
                guarded.add_handler(handler)
        guarded.add_handler(
            PublicHTTPHandler(
                context=self._make_sslcontext(legacy_ssl_support=legacy_ssl_support),
            )
        )
        guarded.addheaders = []
        return guarded


class PublicYoutubeDL(yt_dlp.YoutubeDL):
    def build_request_director(
        self, handlers: Iterable[type[RequestHandler]], preferences: object = None
    ) -> RequestDirector:
        return super().build_request_director([PublicUrllibRH])

    def dl(
        self,
        name: str,
        info: dict[str, object],
        subtitle: bool = False,
        test: bool = False,
    ) -> tuple[bool, bool]:
        # External/live downloaders bypass the guarded request director. Refuse
        # them; native HTTP, HLS and DASH keep fragment requests inside it.
        from yt_dlp.downloader import get_suitable_downloader
        from yt_dlp.downloader.dash import DashSegmentsFD
        from yt_dlp.downloader.hls import HlsFD
        from yt_dlp.downloader.http import HttpFD
        from yt_dlp.utils import DownloadError

        downloader = get_suitable_downloader(info, self.params)
        if downloader not in {HttpFD, HlsFD, DashSegmentsFD} or (
            test and info.get("is_live")
        ):
            raise DownloadError("This media requires an unsupported network downloader")
        if downloader is HlsFD:
            # HlsFD delegates unsupported manifests to ffmpeg internally.
            # Preflight the manifest and cache it to prevent that escape hatch.
            from yt_dlp.dependencies import Cryptodome

            hls = HlsFD(self, self.params)
            cached_manifest = info.get("hls_media_playlist_data")
            manifest = cached_manifest if isinstance(cached_manifest, str) else ""
            if not manifest:
                url = info.get("url")
                if not isinstance(url, str):
                    raise DownloadError("Missing HLS URL")
                with self.urlopen(hls._prepare_url(info, url)) as response:
                    manifest = response.read().decode("utf-8", "ignore")
                    info = {**info, "url": response.url}
            if not HlsFD.can_download(manifest, info) or (
                "#EXT-X-KEY:METHOD=AES-128" in manifest and not Cryptodome.AES
            ):
                raise DownloadError(
                    "This HLS stream requires an unsupported network downloader"
                )
            info = {**info, "hls_media_playlist_data": manifest}
            if test:
                # yt-dlp's test mode discards the external_downloader setting.
                # Pin the native protocol so format probes cannot invoke ffmpeg.
                info = {**info, "protocol": "m3u8_native"}
        return super().dl(name, info, subtitle=subtitle, test=test)
