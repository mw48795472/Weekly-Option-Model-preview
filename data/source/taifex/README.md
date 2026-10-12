# TAIFEX public source data and attribution

Provider / 출처: Taiwan Futures Exchange (TAIFEX, 臺灣期貨交易所).
Retrieved / 수집: 2026-10-12 KST. Market dates are stored separately from retrieval times.

Public option market data are listed on Taiwan's government open-data portal under the **Open Government Data License, version 1.0**:
- Daily option market data: https://data.gov.tw/dataset/11320
- Option delta: https://data.gov.tw/dataset/11321
- Put/call statistics: https://data.gov.tw/dataset/11322
- Large-trader option OI: https://data.gov.tw/dataset/11338
- Stock-option underlyings: https://data.gov.tw/dataset/22646
- License and attribution terms: https://data.gov.tw/license
- TAIFEX website terms and open-data exception: https://www.taifex.com.tw/cht/edu/userTerms

The data are provided by TAIFEX and have been cleaned, joined and aggregated by this research project. These transformations are not endorsed by TAIFEX. Retain this source attribution and the source URLs when reusing the data. Code licensing does not replace the source-data terms.

## Files and reproduction

The dated folder contains losslessly compressed responses and a manifest with request URL, retrieval time, HTTP status, byte length, SHA-256 of the **uncompressed response**, observed format and completeness. No credentials are used.

- API: https://openapi.taifex.com.tw/v1/
- Schema: https://openapi.taifex.com.tw/swagger.json
- Historical download form: https://www.taifex.com.tw/cht/3/optDailyMarketView?menuid1=03
- Read-only historical POST: https://www.taifex.com.tw/cht/3/optDataDown
- Contract catalog: https://www.taifex.com.tw/cht/3/getOptcontractDl.do
- Product names/specifications: https://www.taifex.com.tw/cht/4/contractName1 and https://www.taifex.com.tw/cht/2/tXO

Historical requests cover 2026-09-09 through 2026-10-08, seven stock families plus TXO. Original historical bodies are CP950 CSV despite the HTML Content-Type. The large-trader endpoint returned UTF-8 BOM CSV. Other saved market endpoints returned JSON arrays. The schema and history catalog are JSON objects.

The incomplete tick download is **not** included as a dataset. The date-query experiment is recorded as a probe: its response hash equals the ordinary latest-market response. It is not evidence of a historical query capability.

## Derived ZIP / field guide

- latest_weekly.csv: latest **regular-session** weekly option contracts with actual prices/OI; monthly contracts excluded.
- weekly_history.csv.gz: weekly observations for the downloaded month, retaining regular/after-hours sessions. Decompress before importing into Excel.
- ticker_catalog.csv: unique contracts observed in either source, including monthly and adjusted contracts. It is not a current active-order-symbol list.
- product_tickers.csv: underlying stock code/name and explicit standard/adjusted product mappings.
- expiry_summary.csv: regular-session weekly aggregates by product and expiry.
- oi_decomposition.csv: continuing-contract change + entering OI - exiting OI = total OI change.
- put_call_history.csv: published **TXO all-expiry** put/call ratios, in ratio units (1 = 100%).
- api_coverage.csv: actual response format, observed dates and row counts.
- api_csv_comparison.csv: every matching date/contract/session with source-specific fields; preserves bid/ask discrepancies.
- summary.json: coverage, provenance, quality checks and analysis limitations.

contract_id is an **internal research ID**, e.g. TAIFEX:CDO:202610W2:P:2450; it is not an executable exchange/broker symbol. underlying_code is text (preserve leading zeroes); product is the API product code; expiry_code is the source month/week code; expiry_date has an explicit source; side is C/P; strike_text preserves canonical decimal notation; adjusted marks a corporate-action variant.

close is the last traded price; settlement is the official settlement price, never used to fill a missing last trade. volume/oi are contract counts. Premiums are in the source contract quotation unit, not currency-normalized P&L. bid/ask are end-of-session snapshots. Missing values remain blank; actual zero remains zero. After-hours OI is missing in this snapshot and must not be counted as zero or added to regular-session OI.

Date is the source trading date, not a UTC timestamp. Delta has no observation-date field, so only its expiry reference is used; Delta is not used as a time-aligned predictive feature. Current adjusted share/cash metadata must not be applied retroactively to every historical date.

The available 20 trading days support descriptive analysis, not conclusions about causality, strategy returns, HAR/RV/REV prediction or cross-market model transfer.
