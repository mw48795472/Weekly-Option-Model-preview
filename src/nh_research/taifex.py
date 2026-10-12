"""TAIFEX public data parsing and descriptive analysis; no orders or credentials."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import io
import json
import math
import re

import numpy as np
import pandas as pd

BASE_URL = "https://openapi.taifex.com.tw/v1"
API_NAMES = (
    "DailyMarketReportOpt", "DailyOptionsDelta", "SSOLists", "SSFAdjustedInfo",
    "PutCallRatio", "OpenInterestOfLargeTradersOptions", "ContractAdj",
    "FinalSettlementPriceOptions", "SettledPositionsSSO", "OptionsTimeAndSalesData",
)
CN_FIELDS = {
    "交易日期": "Date", "日期": "Date", "契約": "Contract", "到期月份(週別)": "ContractMonth(Week)",
    "履約價": "StrikePrice", "履約價格": "StrikePrice", "買賣權": "CallPut", "開盤價": "Open",
    "最高價": "High", "最低價": "Low", "收盤價": "Close", "最後成交價": "Close", "成交量": "Volume",
    "結算價": "SettlementPrice", "未沖銷契約數": "OpenInterest", "未沖銷契約量": "OpenInterest",
    "最後最佳買價": "BestBid", "最後最佳賣價": "BestAsk", "交易時段": "TradingSession",
    "契約到期日": "ContractSettlementDay",
}
NUMBERS = {"Open": "open", "High": "high", "Low": "low", "Close": "close",
           "Volume": "volume", "SettlementPrice": "settlement", "OpenInterest": "oi",
           "BestBid": "bid", "BestAsk": "ask"}
SIDES = {"買權": "C", "賣權": "P", "Call": "C", "Put": "P", "C": "C", "P": "P"}
SESSIONS = {"一般": "regular", "盤後": "after_hours", "Regular": "regular", "After-hours": "after_hours"}
TXO_WEEK_CODES = {"W1": "TX1", "W2": "TX2", "W4": "TX4", "W5": "TX5",
                  "F1": "TXU", "F2": "TXV", "F3": "TXX", "F4": "TXY", "F5": "TXZ"}
INDEX_PRODUCTS = {"TXO": ("TAIEX", "臺指選擇權", "index"),
                  "TEO": ("ELECTRONICS", "電子選擇權", "index"),
                  "TFO": ("FINANCE", "金融選擇權", "index"),
                  "TGO": ("GOLD", "黃金選擇權", "commodity")}


def decode_response(raw: bytes) -> tuple[list[dict], str]:
    """Sniff actual body: some nominal JSON endpoints return BOM CSV."""
    for encoding in ("utf-8-sig", "cp950"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Unsupported response encoding")
    stripped = text.lstrip()
    if stripped.startswith("<"):
        raise ValueError("HTML response is not market data")
    if stripped.startswith(("[", "{")):
        rows = json.loads(text)
        if not isinstance(rows, list) or not all(isinstance(x, dict) for x in rows):
            raise ValueError("Expected an array of records")
        return rows, "json"
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError("Unrecognized CSV response")
    rows = []
    for row in reader:
        if None in row:
            raise ValueError("CSV row has more cells than its header")
        # The historical download includes an empty trailing header.
        if row.get("") not in (None, ""):
            raise ValueError("Unexpected data under the blank trailing header")
        rows.append({CN_FIELDS.get(k.strip(), k.strip()): (v or "").strip()
                     for k, v in row.items() if k})
    return rows, "csv"


def canonical_strike(value) -> str:
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid strike") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Strike must be finite and positive")
    return format(number.normalize(), "f")


def contract_id(product: str, expiry_code: str, side: str, strike) -> str:
    """Internal composite ID, explicitly NOT a broker/order symbol."""
    if not re.fullmatch(r"[A-Z0-9]{3}", product):
        raise ValueError("Invalid product code")
    if not re.fullmatch(r"\d{4}(?:0[1-9]|1[0-2])(?:[WF][1-5])?", expiry_code):
        raise ValueError("Invalid month/week code")
    if side not in ("C", "P"):
        raise ValueError("Invalid option side")
    return f"TAIFEX:{product}:{expiry_code}:{side}:{canonical_strike(strike)}"


def date_iso(values, allow_blank=False):
    clean = values.astype(str).str.strip().str.replace("/", "", regex=False).str.replace("-", "", regex=False)
    parsed = pd.to_datetime(clean, format="%Y%m%d", errors="coerce")
    bad = parsed.isna() & (clean.ne("") if allow_blank else True)
    if bad.any():
        raise ValueError("Invalid or missing source date")
    return parsed.dt.strftime("%Y-%m-%d").fillna("")


def normalize_market(rows: list[dict], source: str) -> pd.DataFrame:
    if not rows:
        raise ValueError("Empty market response")
    frame = pd.DataFrame(rows)
    required = {"Date", "Contract", "ContractMonth(Week)", "StrikePrice", "CallPut", "TradingSession", *NUMBERS}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing market fields: {sorted(required-set(frame.columns))}")
    frame = frame.fillna("").astype(str).apply(lambda s: s.str.strip())
    out = pd.DataFrame({
        "date": date_iso(frame.Date), "product": frame.Contract,
        "expiry_code": frame["ContractMonth(Week)"],
        "side": frame.CallPut.map(SIDES), "session": frame.TradingSession.map(SESSIONS),
    })
    if out[["side", "session"]].isna().any().any():
        raise ValueError("Unknown option side or trading session")
    strike_map = {s: canonical_strike(s) for s in frame.StrikePrice.unique()}
    out["strike_text"] = frame.StrikePrice.map(strike_map)
    out["strike"] = out.strike_text.astype(float)
    out["contract_id"] = [contract_id(p, e, c, k) for p, e, c, k in
                          zip(out["product"], out.expiry_code, out.side, out.strike_text)]
    out["is_weekly"] = out.expiry_code.str.contains(r"[WF]", regex=True)
    for raw, normalized in NUMBERS.items():
        clean = frame[raw].str.replace(",", "", regex=False).mask(frame[raw].isin(["", "-", "--"]))
        out[normalized] = pd.to_numeric(clean, errors="coerce")
        if (clean.notna() & out[normalized].isna()).any() or ((out[normalized].dropna() < 0) | ~np.isfinite(out[normalized].dropna())).any():
            raise ValueError(f"Invalid nonnegative number: {raw}")
        if normalized in ("oi", "volume") and ((out[normalized].dropna() % 1) != 0).any():
            raise ValueError(f"Noninteger contract count: {raw}")
    out["expiry_date"] = date_iso(frame.get("ContractSettlementDay", pd.Series("", index=frame.index)), True)
    out["expiry_date_source"] = np.where(out.expiry_date.ne(""), "historical_csv_scheduled_last_trading_day", "")
    out["source"] = source
    if out.duplicated(["date", "contract_id", "session"]).any():
        raise ValueError("Duplicate date/contract/session observations")
    # End-of-session quotes are not a simultaneous intraday order book.
    out["valid_two_sided_quote"] = out.bid.gt(0) & out.ask.gt(0) & out.ask.ge(out.bid)
    out["quote_mid"] = ((out.bid + out.ask) / 2).where(out.valid_two_sided_quote)
    out["relative_spread_pct"] = (100 * (out.ask - out.bid) / out.quote_mid).where(out.valid_two_sided_quote)
    out["has_trade_price"] = out.volume.gt(0) & out.close.notna()
    return out


def expiry_reference(delta_rows):
    result = {}
    for row in delta_rows:
        key = contract_id(row["Contract"].strip(), row["ContractMonth(Week)"].strip(),
                          SIDES[row["CallPut"].strip()], row["StrikePrice"])
        value = row.get("ContractSettlementDay", "").strip()
        if value:
            iso = pd.to_datetime(value, format="%Y%m%d").strftime("%Y-%m-%d")
            if key in result and result[key] != iso:
                raise ValueError("Conflicting reference expiries")
            result[key] = iso
    return result


def product_metadata(sso, history_catalog, adjusted):
    """Use explicit master/catalog joins; do not infer adjusted symbols by truncating."""
    result = {}
    for row in sso:
        product = row["Contract"].strip()
        result[product] = dict(product=product, underlying_code=row["StockCode"].strip(),
                               name=row["StockName"].strip(), legal_name=row["UnderlyingStock"].strip(),
                               asset_type="etf" if "ETF" in row["Type"] else "stock",
                               adjusted=False, mapping_source="SSOLists")
    for row in history_catalog:
        standard = row["commodity_id"].strip()
        if row["flag"] == 1 and standard in result:
            for alias in row["marketids"].split(","):
                alias = alias.strip()
                if alias and alias not in result:
                    result[alias] = {**result[standard], "product": alias, "adjusted": True,
                                     "mapping_source": "historical_download_commodityList"}
    for row in adjusted:
        if row.get("Futures/Options") != "股票選擇權":
            continue
        product = row["Contract"].strip()
        if product not in result:
            result[product] = dict(product=product, underlying_code=row["StockCode"].strip(),
                                   name=row["ContractName"].strip(), legal_name="",
                                   asset_type="stock", adjusted=True, mapping_source="SSFAdjustedInfo")
        result[product]["adjusted_reference_date"] = row["Date"]
        result[product]["adjusted_reference_shares"] = row["UnderlyingSecurityShares"]
        result[product]["adjusted_reference_cash"] = row["UnderlyingSecurityDistributionofCashDividends"]
    for product, (code, name, kind) in INDEX_PRODUCTS.items():
        result[product] = dict(product=product, underlying_code=code, name=name, legal_name="",
                               asset_type=kind, adjusted=False, mapping_source="official_contract_specification")
    return pd.DataFrame(result.values()).fillna("")


def enrich(frame, metadata):
    result = frame.merge(metadata, on="product", how="left", validate="many_to_one")
    if result.name.isna().any():
        raise ValueError("Unmapped product in market observations")
    result["trading_product_code"] = result["product"]
    tx_weekly = result["product"].eq("TXO") & result.is_weekly
    result.loc[tx_weekly, "trading_product_code"] = result.loc[tx_weekly, "expiry_code"].str[6:].map(TXO_WEEK_CODES)
    if result.loc[tx_weekly, "trading_product_code"].isna().any():
        raise ValueError("Unknown TXO weekly trading-system product code")
    result["label"] = (result["name"] + " · " + result["product"] + " · " + result.expiry_code
                       + " · " + result.side + " · K " + result.strike_text)
    return result


def ratio(numerator, denominator):
    return float(numerator / denominator) if pd.notna(denominator) and denominator > 0 and pd.notna(numerator) else None


def describe_groups(frame):
    """Regular-session weekly per-product/expiry stats; no inter-session OI addition."""
    selected = frame.loc[frame.session.eq("regular") & frame.is_weekly]
    rows = []
    for (date, product, expiry), group in selected.groupby(["date", "product", "expiry_code"], sort=True):
        oi = group.oi.sum(min_count=1)
        by_strike = group.groupby("strike").oi.sum(min_count=1)
        shares = by_strike / oi if pd.notna(oi) and oi > 0 else pd.Series(dtype=float)
        call = group.loc[group.side.eq("C")]
        put = group.loc[group.side.eq("P")]
        rows.append(dict(date=date, product=product, name=group.name.iloc[0], expiry_code=expiry,
                         expiry_date=group.expiry_date.iloc[0], contracts=len(group),
                         oi=oi, volume=group.volume.sum(min_count=1),
                         call_oi=call.oi.sum(min_count=1), put_oi=put.oi.sum(min_count=1),
                         put_call_oi_ratio=ratio(put.oi.sum(min_count=1), call.oi.sum(min_count=1)),
                         traded_contracts=int(group.has_trade_price.sum()),
                         trade_price_coverage_pct=100*group.has_trade_price.mean(),
                         two_sided_quote_coverage_pct=100*group.valid_two_sided_quote.mean(),
                         median_relative_spread_pct=group.relative_spread_pct.median(),
                         strike_oi_hhi=float((shares**2).sum()) if len(shares) else None,
                         top3_strike_oi_share=float(shares.nlargest(3).sum()) if len(shares) else None))
    return pd.DataFrame(rows)


def decompose_oi(frame):
    """Exact observed-universe decomposition, never label entries/exits as investor flows."""
    selected = frame.loc[frame.session.eq("regular") & frame.is_weekly]
    rows = []
    for product, group in selected.groupby("product", sort=True):
        previous = None
        previous_date = None
        for date, current in group.groupby("date", sort=True):
            series = current.set_index("contract_id").oi
            if series.index.has_duplicates or series.isna().any():
                raise ValueError("OI decomposition requires unique, observed regular-session OI")
            if previous is not None:
                common = series.index.intersection(previous.index)
                enters = series.index.difference(previous.index)
                exits = previous.index.difference(series.index)
                matched = float((series.loc[common] - previous.loc[common]).sum())
                entering = float(series.loc[enters].sum())
                exiting = float(previous.loc[exits].sum())
                total_change = float(series.sum()-previous.sum())
                if not math.isclose(matched+entering-exiting, total_change, abs_tol=1e-8):
                    raise ValueError("OI decomposition identity failed")
                rows.append(dict(date=date, previous_observed_date=previous_date, product=product,
                                 name=current.name.iloc[0], previous_oi=float(previous.sum()),
                                 oi=float(series.sum()), total_change=total_change,
                                 matched_change=matched, entering_oi=entering, exiting_oi=exiting,
                                 matched_contracts=len(common), entering_contracts=len(enters),
                                 exiting_contracts=len(exits)))
            previous, previous_date = series, date
    return pd.DataFrame(rows)
