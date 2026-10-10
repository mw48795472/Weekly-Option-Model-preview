"""No credentials, tokens or orders: probe public portal and auth rejection only."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Fixed scope: public site + one quote query per environment, no authorization.
    requests = [Request("https://apidev.futures.co.kr/")]
    for domain in ("api", "apidemo"):
        requests.append(Request(f"https://{domain}.futures.co.kr/trade/v1/domestic/price",
                                data=b'{"sym":"A016C000"}',
                                headers={"Content-Type": "application/json"}, method="POST"))
    results = []
    opener = build_opener(NoRedirect())
    for request in requests:
        row = {"url": request.full_url, "method": request.get_method(),
               "checked_at_utc": datetime.now(timezone.utc).isoformat(), "authorization_sent": False}
        try:
            response = opener.open(request, timeout=10)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError, OSError) as exc:
            row.update(status=None, error_type=type(exc).__name__, error=str(exc))
            results.append(row)
            continue
        with response:
            row.update(status=response.status, content_type=response.headers.get("Content-Type"),
                       server_date=response.headers.get("Date"))
            raw = response.read(2048)
            if "json" in (row["content_type"] or ""):
                try:
                    data = json.loads(raw)
                    # Only standard error identifiers, never arbitrary response bodies.
                    row["error_fields"] = {k: data[k] for k in ("error", "error_description", "code", "message", "msg")
                                           if isinstance(data, dict) and k in data}
                except ValueError:
                    row["json_parseable"] = False
        results.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
