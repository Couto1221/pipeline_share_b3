# B3 Share Pipeline

This pipeline updates the database for the B3 share calculation study by joining B3 tickers with CNPJs extracted from the official API.

## Overview
The architecture follows a layered data organization:
- `data/staging/`: ingestion and staging layer where raw and normalized data is stored
- `data/marts/`: final consumption layer with clean data ready for analysis and downstream

## What it does
- collects the ticker table from `https://www.dadosdemercado.com.br/acoes`
- makes paginated requests to the B3 API at `https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/...`
- joins data using the first 4 characters of the ticker matched with the API's `issuingCompany` field
- saves the final result to `data/marts/b3_ticker_cnpj.csv`
- filters output to include only tickers ending in 3, 4, 5, or 6 (standard B3 equity types)

## How to use
1. Run:

```bash
python scripts/b3_share_pipeline.py
```

2. Generated output files:

- `data/staging/dadosdemercado_tickers.csv`
- `data/staging/b3_api_raw.json`
- `data/staging/b3_api_normalized.csv`
- `data/marts/b3_ticker_cnpj.csv`

## Data structure
- `staging/`: contains intermediate data and consolidated versions before final transformation
- `marts/`: contains clean data ready for studies, reports, or consumption in analytical models

## Data engineering best practices applied
- clear separation between ingestion (`staging`) and final product (`marts`)
- persistence of raw and normalized data for auditability and reprocessing
- deterministic paths to facilitate reprocessing and idempotency
- well-defined names and normalized fields before the join operation
- documented business rules: join by first 4 characters of ticker

## Business rules
- join key: first 4 characters of the ticker extracted from `dadosdemercado.com.br`
- the B3 API provides `cnpj` and `issuingCompany`; the script uses `issuingCompany[:4]` to match with the ticker when available
- tickets are filtered to keep only those ending in 3, 4, 5, or 6 (standard equity types on B3)
- if a ticker has no match, the final file will keep the record with an empty `cnpj` field for further analysis
