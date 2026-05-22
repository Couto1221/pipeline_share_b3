import base64
import csv
import json
import os
import re
import urllib.request
from html.parser import HTMLParser


class StocksTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_tbody = False
        self.in_td = False
        self.current_row = []
        self.rows = []
        self.current_text = []
        self.table_id = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "stocks":
            self.in_table = True
            self.table_id = attrs.get("id")
        elif self.in_table and tag == "tbody":
            self.in_tbody = True
        elif self.in_tbody and tag == "td":
            self.in_td = True
            self.current_text = []
        elif self.in_td and tag == "a":
            self.current_text = []

    def handle_endtag(self, tag):
        if tag == "table" and self.in_table:
            self.in_table = False
            self.in_tbody = False
        elif tag == "tbody" and self.in_tbody:
            self.in_tbody = False
        elif tag == "td" and self.in_td:
            value = "".join(self.current_text).strip()
            self.current_row.append(value)
            self.current_text = []
            self.in_td = False
        elif tag == "tr" and self.current_row:
            if len(self.current_row) >= 1:
                self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data):
        if self.in_td:
            self.current_text.append(data)


def fetch_url_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                          " (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_dadosdemercado_tickers(html):
    parser = StocksTableParser()
    parser.feed(html)
    tickers = []
    for row in parser.rows:
        if len(row) >= 1:
            ticker = row[0].strip()
            if ticker:
                tickers.append({"ticker": ticker, "ticker_prefix": ticker[:4]})
    return tickers


def ensure_dir_for_path(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def save_csv(path, fieldnames, rows):
    ensure_dir_for_path(path)
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        filtered_rows = [
            {key: row.get(key, "") for key in fieldnames}
            for row in rows
        ]
        writer.writerows(filtered_rows)


def decode_payload_from_url(url):
    payload = url.rsplit("/", 1)[-1]
    decoded = base64.b64decode(payload).decode("utf-8")
    return json.loads(decoded)


def build_payload_url(base_url, payload):
    json_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(json_payload.encode("utf-8")).decode("utf-8")
    return f"{base_url}/{encoded}"


def fetch_b3_api_pages(initial_url):
    payload = decode_payload_from_url(initial_url)
    base_url = initial_url.rsplit("/", 1)[0]
    results = []

    page_number = payload.get("pageNumber", 1)
    while True:
        payload["pageNumber"] = page_number
        payload_url = build_payload_url(base_url, payload)
        print(f"Fetching page {page_number} -> {payload_url}")
        page_text = fetch_url_text(payload_url)
        data = json.loads(page_text)
        page_results = data.get("results", [])
        if not page_results:
            break
        results.extend(page_results)

        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages")
        if not total_pages or page_number >= total_pages:
            break
        page_number += 1

    return results


def normalize_api_rows(rows):
    normalized = []
    for row in rows:
        issuing_company = str(row.get("issuingCompany", "")).strip()
        trading_name = str(row.get("tradingName", "")).strip()
        cnpj = str(row.get("cnpj", "")).strip()
        prefix = issuing_company[:4] if issuing_company else trading_name[:4]
        normalized.append({
            "issuingCompany": issuing_company,
            "tradingName": trading_name,
            "cnpj": cnpj,
            "api_prefix": prefix,
            "raw": row,
        })
    return normalized


def build_api_lookup(api_rows):
    lookup = {}
    for row in api_rows:
        key = row["api_prefix"]
        if not key:
            continue
        if key not in lookup:
            lookup[key] = row
    return lookup


def join_tickers_and_cnpjs(tickers, api_lookup):
    joined = []
    for ticker_row in tickers:
        prefix = ticker_row["ticker_prefix"]
        api_row = api_lookup.get(prefix)
        joined.append({
            "ticker": ticker_row["ticker"],
            "ticker_prefix": prefix,
            "cnpj": api_row["cnpj"] if api_row else "",
            "issuingCompany": api_row["issuingCompany"] if api_row else "",
            "tradingName": api_row["tradingName"] if api_row else "",
        })
    return joined


def summarize(joined_rows):
    matched = sum(1 for r in joined_rows if r["cnpj"])
    total = len(joined_rows)
    unmatched = [r for r in joined_rows if not r["cnpj"]]
    print(f"Total tickers: {total}")
    print(f"Matched with CNPJ: {matched}")
    print(f"Unmatched tickers: {len(unmatched)}")
    if unmatched:
        print("Primeiros tickers sem CNPJ:")
        for row in unmatched[:10]:
            print(f"  {row['ticker']} ({row['ticker_prefix']})")


def main():
    dados_url = "https://www.dadosdemercado.com.br/acoes"
    print("Buscando tickers de dadosdemercado.com.br...")
    html = fetch_url_text(dados_url)
    tickers = parse_dadosdemercado_tickers(html)
    save_csv("data/staging/dadosdemercado_tickers.csv", ["ticker", "ticker_prefix"], tickers)
    print(f"Tickers extraídos: {len(tickers)}")

    initial_api_url = (
        "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/"
        "eyJsYW5ndWFnZSI6InB0LWJyIiwicGFnZU51bWJlciI6MSwicGFnZVNpemUiOjEyMH0="
    )
    print("Buscando dados da API B3...")
    api_rows = fetch_b3_api_pages(initial_api_url)
    raw_path = "data/staging/b3_api_raw.json"
    ensure_dir_for_path(raw_path)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(api_rows, f, ensure_ascii=False, indent=2)
    print(f"Registros API B3 coletados: {len(api_rows)}")

    normalized_api = normalize_api_rows(api_rows)
    save_csv(
        "data/staging/b3_api_normalized.csv",
        ["issuingCompany", "tradingName", "cnpj", "api_prefix"],
        normalized_api,
    )

    api_lookup = build_api_lookup(normalized_api)
    joined = join_tickers_and_cnpjs(tickers, api_lookup)
    save_csv(
        "data/marts/b3_ticker_cnpj.csv",
        ["ticker", "ticker_prefix", "cnpj", "issuingCompany", "tradingName"],
        joined,
    )

    summarize(joined)
    print("Resultado final salvo em data/marts/b3_ticker_cnpj.csv")


if __name__ == "__main__":
    main()
