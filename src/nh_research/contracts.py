"""Offline request construction. This module never opens a network connection."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlencode

DOMAINS = {"demo": "https://apidemo.futures.co.kr", "live": "https://api.futures.co.kr"}
MARKET_CHANNELS = frozenset({"KA", "KB", "KC", "KD", "FA", "FB"})


@dataclass(frozen=True)
class Credentials:
    appkey: str = field(repr=False)
    appsecret: str = field(repr=False)

    def __post_init__(self):
        if not self.appkey.strip() or not self.appsecret.strip():
            raise ValueError("Both appkey and appsecret must be configured")


@dataclass(frozen=True)
class RequestPlan:
    method: str
    url: str
    headers: dict = field(repr=False)
    body: bytes | None = field(repr=False)

    def public_summary(self) -> dict:
        # Intentionally excludes all body values and authorization values.
        return {"method": self.method, "url": self.url,
                "header_names": sorted(self.headers),
                "content_type": self.headers.get("Content-Type"),
                "body_bytes": len(self.body) if self.body is not None else 0,
                "network_sent": False}


def base_url(environment: str) -> str:
    if environment not in DOMAINS:
        raise ValueError("environment must be demo or live")
    return DOMAINS[environment]


def token_request(credentials: Credentials, environment: str = "demo") -> RequestPlan:
    body = urlencode({"grant_type": "client_credentials", "appkey": credentials.appkey,
                      "appsecret": credentials.appsecret}).encode("ascii")
    return RequestPlan("POST", base_url(environment) + "/auth-service/v1/token",
                       {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}, body)


def market_request(spec: dict, parameters: dict, token: str, environment: str = "demo") -> RequestPlan:
    metadata = spec["metadata"]
    # Explicit allowlist: catalog classifications or names cannot enable orders.
    allowed = {
        "domestic/price", "domestic/price-bid", "domestic/chart-daily", "domestic/chart-minute",
        "domestic/price-all-futures", "domestic/price-all-option", "domestic/trend-investor",
        "domestic/price-expect-fill", "domestic/product-detail", "domestic/price-night",
        "domestic/price-all-option-night", "overseas/price", "overseas/bid-price",
        "overseas/chart-daily", "overseas/chart-minute", "overseas/price-all-option",
        "overseas/product-detail", "overseas/market-operations", "overseas/product-expiry",
    }
    document = metadata["document"]
    if (document not in allowed or metadata["transport"] != "HTTP" or
            metadata["method"] != "POST" or metadata["path"] != f"/trade/v1/{document}"):
        raise ValueError("Only catalogued read-only market queries are supported")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    definitions = {f["key"]: f for f in spec["input"] if not f.get("parent")}
    if set(parameters) - definitions.keys():
        raise ValueError("Unknown request fields")
    body = {}
    for key, definition in definitions.items():
        value = parameters.get(key, definition.get("default"))
        if value is None or value == "":
            if definition["requirement"] == "Y":
                raise ValueError(f"Required field is missing: {key}")
            continue
        if not isinstance(value, str):
            raise ValueError(f"NH request field must be a string: {key}")
        body[key] = value
    if environment == "demo" and (document.endswith("-night") or
            (document.startswith("domestic/chart-") and body.get("nght_tp") == "2")):
        raise ValueError("Domestic night data is not supported by the documented demo environment")
    if document.startswith("domestic/chart-"):
        if body.get("nght_tp") not in {"1", "2"}:
            raise ValueError("nght_tp must be 1 or 2")
        if not body.get("req_qty", "").isdigit() or not 1 <= int(body["req_qty"]) <= 9999:
            raise ValueError("req_qty must be between 1 and 9999")
    if not token or any(ch in token for ch in "\r\n"):
        raise ValueError("A nonempty token without newlines is required")
    return RequestPlan("POST", base_url(environment) + metadata["path"],
                       {"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                       json.dumps(body, ensure_ascii=False).encode("utf-8"))


def websocket_key_request(token: str, environment: str = "demo") -> RequestPlan:
    if not token or any(ch in token for ch in "\r\n"):
        raise ValueError("A nonempty token without newlines is required")
    return RequestPlan("GET", base_url(environment) + "/permission/v1/web-socket-key",
                       {"Authorization": "Bearer " + token}, None)


def session_init(token: str) -> dict:
    if not token:
        raise ValueError("A session token is required")
    return {"header": {"api_ver": "1", "action": "0"},
            "body": {"action_code": "session_init", "session_token": token}}


def subscription_plan(pairs: list[tuple[str, str]], other_account_subscriptions: int = 0) -> list[dict]:
    """Plan only; send after INIT_SUCCESS, then track each RT_INIT/RT_FAIL acknowledgement."""
    if not 0 <= other_account_subscriptions <= 20:
        raise ValueError("Invalid number of other account subscriptions")
    pairs = list(dict.fromkeys(pairs))
    if len(pairs) + other_account_subscriptions > 20:
        raise ValueError("Account-wide subscription budget exceeds 20")
    if any(code not in MARKET_CHANNELS or not symbol.strip() for code, symbol in pairs):
        raise ValueError("Only market-data channels with nonempty symbols are supported")
    return [{"header": {"api_ver": "1", "action": "A"},
             "body": {"action_code": code, "action_sym": symbol}} for code, symbol in pairs]


def classify_message(message: dict) -> str:
    if message == {"code": "pingpong", "msg": "pingpong"}:
        return "echo_pingpong"
    if message.get("code") == "INIT":
        return "session_ready" if message.get("msg") == "INIT_SUCCESS" else "session_failed"
    if isinstance(message.get("header"), dict) and isinstance(message.get("body"), dict):
        return "market_event"
    if message.get("rt_cd") in {"RT_INIT", "RT_FAIL"}:
        return "subscription_ok" if message["rt_cd"] == "RT_INIT" else "subscription_failed"
    return "unknown"
