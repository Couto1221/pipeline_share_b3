# Pipeline de Junção de Tickers B3 e CNPJs

Esta pipeline atualiza a base de dados para o estudo de cálculo de share B3, reunindo tickers da B3 com CNPJs extraídos da API oficial.

## Visão geral
A arquitetura segue uma organização em camadas:
- `data/staging/`: camada de ingestão e staging onde os dados brutos e normalizados ficam armazenados
- `data/marts/`: camada de consumo final, com o conjunto de dados pronto para análise e downstream

## O que faz
- coleta a tabela de tickers do site `https://www.dadosdemercado.com.br/acoes`
- faz requisições paginadas à API B3 em `https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/...`
- junta os dados usando os 4 primeiros caracteres do ticker com o campo `issuingCompany` da API
- salva o resultado final em `data/marts/b3_ticker_cnpj.csv`

## Como usar
1. Execute:

```bash
python b3_share_pipeline.py
```

2. Os arquivos gerados serão:

- `data/staging/dadosdemercado_tickers.csv`
- `data/staging/b3_api_raw.json`
- `data/staging/b3_api_normalized.csv`
- `data/marts/b3_ticker_cnpj.csv`

## Estrutura de dados
- `staging`: contém dados intermediários e versões consolidadas antes da transformação final
- `marts`: contém dados prontos para estudos, relatórios ou consumo em modelos analíticos

## Boas práticas de engenharia de dados aplicadas
- separação clara entre ingestão (`staging`) e produto final (`marts`)
- persistência de dados brutos e normalizados para auditabilidade e reprovação
- uso de caminhos determinísticos para facilitar reprocessamento e idempotência
- trabalho com nomes bem definidos e campos normalizados antes do join
- documentação de regras de negócio: join por prefixo de 4 caracteres do ticker

## Observações de negócio
- a chave de junção é o prefixo de 4 caracteres do ticker extraído de `dadosdemercado.com.br`
- a API B3 fornece `cnpj` e `issuingCompany`; o script usa `issuingCompany[:4]` para casar com o ticker quando disponível
- caso existam tickers sem match, o arquivo final manterá o registro com `cnpj` vazio para análise posterior
