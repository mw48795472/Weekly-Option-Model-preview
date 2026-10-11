"""Read-only NH demo transport. Credentials and tokens never enter saved results."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .contracts import Credentials, RequestPlan, market_request, token_request


class APIError(RuntimeError):
    """A deliberately sanitized error without response bodies or secrets."""


def redact(value, secrets=()):
    sensitive = {"appkey", "appsecret", "access_token", "session_token", "access_key", "authorization"}
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if str(key).lower() in sensitive else redact(item, secrets))
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def load_demo_credentials(path: Path) -> Credentials:
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                raise ValueError("Local configuration must contain KEY=value lines")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key.strip()] = value
    for key in ("NH_ENV", "NH_APPKEY", "NH_APPSECRET"):
        if key in os.environ:
            values[key] = os.environ[key]
    if values.get("NH_ENV", "demo") != "demo":
        raise ValueError("This collector supports the demo environment only")
    return Credentials(values.get("NH_APPKEY", ""), values.get("NH_APPSECRET", ""))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPSJSONTransport:
    def __init__(self, timeout=20):
        self.timeout = timeout
        self.opener = build_opener(NoRedirect())

    def __call__(self, plan: RequestPlan) -> dict:
        if not plan.url.startswith("https://apidemo.futures.co.kr/"):
            raise APIError("Only the fixed NH demo HTTPS host is allowed")
        request = Request(plan.url, data=plan.body, headers=plan.headers, method=plan.method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise APIError("Response exceeded 16 MiB")
                result = json.loads(raw)
        except HTTPError as exc:
            secrets = [plan.headers.get("Authorization", "").removeprefix("Bearer ")]
            if plan.headers.get("Content-Type") == "application/x-www-form-urlencoded" and plan.body:
                form = parse_qs(plan.body.decode("ascii"))
                secrets += form.get("appkey", []) + form.get("appsecret", [])
            detail = {}
            try:
                raw_error = exc.read(8192)
                error = json.loads(raw_error)
                if isinstance(error, dict):
                    detail = {key: redact(error[key], secrets) for key in
                              ("code", "error", "error_description", "message", "msg", "rsp_cd", "rsp_msg",
                               "msg_cd", "msg1", "errorCode", "errorMessage", "error_code", "error_msg")
                              if key in error and isinstance(error[key], (str, int))}
                    detail["response_field_names"] = [redact(str(key), secrets) for key in error]
            except (ValueError, OSError):
                detail = {"response_format": "non_json", "content_type": exc.headers.get("Content-Type", "")}
            raise APIError(f"NH demo HTTP {exc.code}; " + json.dumps(detail, ensure_ascii=False)) from None
        except (URLError, TimeoutError, OSError):
            raise APIError("NH demo transport failed; credentials and request contents omitted") from None
        except (ValueError, UnicodeError):
            raise APIError("NH demo returned a non-JSON response") from None
        if not isinstance(result, dict):
            raise APIError("NH demo response must be an object")
        return result


@dataclass(repr=False)
class DemoClient:
    credentials: Credentials = field(repr=False)
    catalog: dict
    transport: object = field(default=None, repr=False)
    interval: float = 0.25
    _token: str = field(default="", init=False, repr=False)
    _expires: float = field(default=0, init=False, repr=False)
    _last_request: float = field(default=0, init=False, repr=False)
    auth_summary: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        if self.interval < 0.1:
            raise ValueError("Request interval must be at least 0.1 seconds")
        if self.transport is None:
            self.transport = HTTPSJSONTransport()

    def _send(self, plan):
        delay = self.interval - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        self._last_request = time.monotonic()
        return self.transport(plan)

    def authenticate(self) -> dict:
        response = self._send(token_request(self.credentials, "demo"))
        token = response.get("access_token")
        if not isinstance(token, str) or not token or response.get("token_type", "").lower() != "bearer":
            raise APIError("Authentication did not return a valid Bearer token")
        if response.get("scopes") != "S":
            raise APIError("Authentication scope is not the documented demo scope S")
        try:
            lifetime = int(response["expires_in"])
        except (KeyError, ValueError, TypeError):
            raise APIError("Authentication response has invalid expiry") from None
        if lifetime <= 0:
            raise APIError("Authentication returned an expired token")
        self._token, self._expires = token, time.monotonic() + lifetime
        self.auth_summary = {"status": "authenticated", "environment": "demo", "scopes": "S",
                             "expires_in_seconds": lifetime}
        return dict(self.auth_summary)

    def query(self, document: str, parameters: dict) -> dict:
        if not self._token or time.monotonic() >= self._expires:
            raise APIError("Authenticate before querying; the token is missing or expired")
        spec = self.catalog.get(document)
        if spec is None:
            raise ValueError("Unknown API document")
        plan = market_request(spec, parameters, self._token, "demo")
        return redact(self._send(plan), (self.credentials.appkey, self.credentials.appsecret, self._token))


def paged_query(client, document, parameters, cursor_field="nxt_key", max_pages=3):
    """Bounded pagination. Unknown or repeated cursors stop explicitly, never loop."""
    if not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be 1..20")
    params = dict(parameters)
    seen = {str(params.get(cursor_field, "99999999"))}
    pages = []
    stop = "page_limit"
    for _ in range(max_pages):
        payload = client.query(document, params)
        pages.append(payload)
        records = payload.get("Occurs1")
        # Preserve unexpected live schemas for review, rather than fabricate rows.
        if not isinstance(records, list):
            stop = "schema_unverified"
            break
        if not records:
            stop = "empty_page"
            break
        cursor = payload.get(cursor_field)
        if cursor is None or str(cursor).strip() in {"", "0"}:
            stop = "empty_cursor"
            break
        if str(cursor) in seen:
            stop = "repeated_cursor"
            break
        seen.add(str(cursor))
        params[cursor_field] = str(cursor)
    return {"pages": pages, "stop_reason": stop, "page_count": len(pages)}
