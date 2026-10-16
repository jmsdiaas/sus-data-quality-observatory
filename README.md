# SUS Data Quality Observatory — São Paulo 🇧🇷

**How Reliable Is Public Healthcare Facility Data in São Paulo, Brazil?**

A reproducible Data Quality Engineering project using **Python, SQL, DuckDB, pytest and GitHub Actions** to investigate the reliability of CNES healthcare-establishment records in São Paulo state.

## Scope and caveats

- The V1 pipeline accepts a CNES CSV containing the columns `cnes`, `codigo_ibge`, `uf`, `municipio` and filters **UF = SP** before calculating metrics.
- The national CNES contains public and private establishments, not only SUS providers. This project does not label all CNES entries as SUS facilities.
- Input columns vary across CNES exports. Adapt field names using the official data dictionary if necessary; do not silently substitute columns.
- Missing or unassignable UF records cannot be included in an SP-only analysis and are excluded; `source_rows` and `record_count` are recorded to make the scope explicit.
- Data-quality issues do **not** establish lack of healthcare access or clinical quality.

## Official source

National CNES open-data catalog: https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude

Download a relevant **national or São Paulo CSV** from the official source, inspect its dictionary, and confirm its column names. No live CNES dataset is bundled in this repository. The sample is synthetic.

## Quickstart

```bash
pip install -r requirements.txt
python -m pytest -q
python -m src.pipeline --input data/sample/cnes_synthetic.csv --output outputs
```

## Real data

1. Download an official CNES CSV containing São Paulo records.
2. Place it at `data/raw/cnes.csv` (ignored by Git).
3. Ensure the required field names match the input schema above.
4. Execute:

```bash
python -m src.pipeline --input data/raw/cnes.csv --output outputs
```

Outputs: `quality.duckdb`, `record_checks.csv`, `quality_report.json`, `quality_summary.md`. The JSON includes the state filter and both source and SP row counts.

## Checks

- Completeness: CNES, municipality code, UF, municipality name
- Format: CNES, IBGE code, UF, CEP
- Broad Brazilian geographic plausibility: latitude and longitude (not precise SP boundaries)
- Repeated CNES identifier **within the SP snapshot**

Failures can overlap. Optional blanks are not automatically considered invalid. The pipeline flags records but does not silently discard SP records.

## Roadmap

- **V2:** authoritative IBGE municipality cross-checks, SP-specific geospatial boundaries, dbt models and tests, dashboards by municipality and health region.
- **V3:** temporal snapshots, drift/freshness monitoring, scheduled alerts.

**Publication policy:** do not publish empirical failure rates until the pipeline has been run against a documented official CNES export.
