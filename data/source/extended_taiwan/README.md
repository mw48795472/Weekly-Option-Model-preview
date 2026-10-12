# Extended Taiwan source attribution

Collected 2026-10-12 KST, bounded monthly requests for 2025-01 through 2026-10-08.

- **TAIFEX**: [official historical option CSV](https://www.taifex.com.tw/cht/3/optDailyMarketView), [final index-option settlements](https://www.taifex.com.tw/cht/5/optIndxFSP). Related government open-data listings: [daily options 11320](https://data.gov.tw/dataset/11320), [option final settlements 22654](https://data.gov.tw/dataset/22654).
- **Taiwan Stock Exchange (TWSE)**: [TAIEX historical OHLC](https://www.twse.com.tw/en/indices/taiex/mi-5min-hist.html), [government listing 11755](https://data.gov.tw/dataset/11755). The listing identifies daily date/open/high/low/close fields and Open Government Data License 1.0; the public historical page supplies earlier monthly observations.
- [Open Government Data License 1.0](https://data.gov.tw/license). Attribution is retained in the repository, report and downloads. Calculations and interpretations are this project's, not endorsed by the providers. This attribution does not cover paid intraday feeds or HKEX material.

Every request records URL, method, form parameters, UTC retrieval time, HTTP status, byte count and SHA-256 of the **decompressed original bytes**. Gzip mtime is fixed; market CSV uses CP950, TWSE JSON and settlement HTML use UTF-8. HTTP complete is a transport flag; the offline analyzer independently verifies schemas, dates, OHLC order, duplicates, nonmissing regular OI and joins.

TAIFEX's scheduled expiry column was introduced 2025-12-08. Historical final settlement dates are a separate ex-post calendar. One difference (202607F2, scheduled July 10 vs actual July 13) is preserved in the audit output. Current finalized daily data and calendars do not establish point-in-time publication or revision history.

No HKEX prices, response bodies or derived market series are included in this public directory. HKEX automated access/derived databases/public use require permission under its [terms section 5](https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en).
