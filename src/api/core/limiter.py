from typing import Callable, Optional
from starlette.requests import Request
from slowapi import Limiter


class _KeyFunc:
    """Callable mutable — permet de remplacer la logique en tests sans recréer le limiter."""

    _override: Optional[Callable[[Request], str]] = None

    def __call__(self, request: Request) -> str:
        if self._override is not None:
            return self._override(request)
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip
        return request.client.host if request.client else "unknown"


key_func = _KeyFunc()
limiter = Limiter(key_func=key_func)
