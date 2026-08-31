from __future__ import annotations

from fastapi import Request, Response

from apps.api.services.tokens import REFRESH_TTL_SEC

REFRESH_COOKIE = "whiteshop_refresh"
COOKIE_PATH = "/api/v1/auth"


def cookie_secure(request: Request) -> bool:
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if forwarded == "https" or request.url.scheme == "https":
        return True
    host = (request.headers.get("host") or "").split(":")[0].lower()
    return host in {"whiteshop.tech", "www.whiteshop.tech"}


def attach_refresh_cookie(request: Request, response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TTL_SEC,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(request),
        path=COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)


def refresh_token_from_request(request: Request, body_token: str | None) -> str | None:
    token = (body_token or "").strip()
    if token:
        return token
    cookie = (request.cookies.get(REFRESH_COOKIE) or "").strip()
    return cookie or None
