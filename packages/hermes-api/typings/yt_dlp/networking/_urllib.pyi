import http.client
import http.cookiejar
import ssl
import urllib.request
from collections.abc import Callable

from .common import RequestHandler

class HTTPHandler(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    _context: ssl.SSLContext
    def __init__(
        self, context: ssl.SSLContext | None = ..., **kwargs: object
    ) -> None: ...
    def do_open(
        self,
        http_class: Callable[..., http.client.HTTPConnection],
        req: urllib.request.Request,
        **http_args: object,
    ) -> http.client.HTTPResponse: ...

class UrllibRH(RequestHandler):
    _SUPPORTED_URL_SCHEMES: tuple[str, ...]
    _SUPPORTED_PROXY_SCHEMES: tuple[str, ...]
    def _create_instance(
        self,
        proxies: dict[str, str | None],
        cookiejar: http.cookiejar.CookieJar,
        legacy_ssl_support: bool | None = ...,
    ) -> urllib.request.OpenerDirector: ...
    def _make_sslcontext(
        self, legacy_ssl_support: bool | None = ...
    ) -> ssl.SSLContext: ...
