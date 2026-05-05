from starlette.requests import Request
from slowapi import Limiter


def get_real_ip(request: Request) -> str:
    # Cloudflare injecte l'IP réelle du client dans ce header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_real_ip)
