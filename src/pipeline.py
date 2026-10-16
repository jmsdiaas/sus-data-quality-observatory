"""CNES data-quality pipeline: raw data is never silently modified or discarded."""
import argparse
import json
from pathlib import Path
import duckdb

SOURCE_URL = 'https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude'
REQUIRED = ('cnes', 'codigo_ibge', 'uf', 'municipio')


def run(input_path: str, output_dir: str = 'outputs') -> dict:
    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f'CSV not found: {source}. Download it from {SOURCE_URL}')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(out / 'quality.duckdb'))
    try:
        con.execute('CREATE OR REPLACE TABLE raw AS SELECT * FROM read_csv(?, all_varchar=true, normalize_names=true, sample_size=-1)', [str(source.resolve())])
        columns = {r[1] for r in con.execute('PRAGMA table_info(raw)').fetchall()}
        missing = set(REQUIRED) - columns
        if missing:
            raise ValueError(f'Missing required columns: {sorted(missing)}; found: {sorted(columns)}')
        # Restrict the analysis to São Paulo before evaluating duplicates or completeness.
        # Rows with missing UF cannot be assigned to SP and are excluded from the SP scope.
        con.execute("CREATE OR REPLACE TABLE raw_sp AS SELECT * FROM raw WHERE upper(trim(uf)) = 'SP'")
        source_count = con.execute('SELECT count(*) FROM raw').fetchone()[0]
        sp_count = con.execute('SELECT count(*) FROM raw_sp').fetchone()[0]
        if sp_count == 0:
            raise ValueError('No rows with UF=SP found. Provide a national or São Paulo CNES CSV with expected columns.')
        con.execute('DROP TABLE raw')
        con.execute('ALTER TABLE raw_sp RENAME TO raw')
        # Add absent optional columns as NULL, not as fabricated source values.
        for col in ('cep', 'latitude', 'longitude', 'nome_fantasia'):
            if col not in columns:
                con.execute(f'ALTER TABLE raw ADD COLUMN {col} VARCHAR')
        con.execute('''CREATE OR REPLACE TABLE checks AS
            WITH normalized AS (
              SELECT *, nullif(trim(cnes),'') AS cnes_clean,
                  nullif(trim(codigo_ibge),'') AS ibge_clean,
                  nullif(trim(uf),'') AS uf_clean,
                  nullif(trim(municipio),'') AS municipio_clean,
                  nullif(trim(cep),'') AS cep_clean,
                  nullif(trim(latitude),'') AS lat_clean,
                  nullif(trim(longitude),'') AS lon_clean
              FROM raw
            ), flags AS (
              SELECT *,
                (cnes_clean IS NULL) AS missing_cnes,
                (ibge_clean IS NULL) AS missing_ibge,
                (uf_clean IS NULL) AS missing_uf,
                (municipio_clean IS NULL) AS missing_municipio,
                (cnes_clean IS NOT NULL AND NOT regexp_full_match(cnes_clean,'[0-9]{7}')) AS invalid_cnes_format,
                (ibge_clean IS NOT NULL AND NOT regexp_full_match(ibge_clean,'[0-9]{6,7}')) AS invalid_ibge_format,
                (uf_clean IS NOT NULL AND NOT regexp_full_match(upper(uf_clean),'[A-Z]{2}')) AS invalid_uf_format,
                (cep_clean IS NOT NULL AND NOT regexp_full_match(replace(cep_clean,'-',''),'[0-9]{8}')) AS invalid_cep_format,
                (lat_clean IS NOT NULL AND (try_cast(replace(lat_clean,',','.') AS DOUBLE) IS NULL OR try_cast(replace(lat_clean,',','.') AS DOUBLE) NOT BETWEEN -34 AND 6)) AS invalid_latitude_br,
                (lon_clean IS NOT NULL AND (try_cast(replace(lon_clean,',','.') AS DOUBLE) IS NULL OR try_cast(replace(lon_clean,',','.') AS DOUBLE) NOT BETWEEN -74 AND -28)) AS invalid_longitude_br,
                (cnes_clean IS NOT NULL AND count(*) OVER (PARTITION BY cnes_clean)>1) AS duplicate_cnes_in_snapshot
              FROM normalized
            )
            SELECT cnes, codigo_ibge, uf, municipio, missing_cnes, missing_ibge,
                   missing_uf, missing_municipio, invalid_cnes_format, invalid_ibge_format,
                   invalid_uf_format, invalid_cep_format, invalid_latitude_br,
                   invalid_longitude_br, duplicate_cnes_in_snapshot
            FROM flags''')
        rule_names = [r[1] for r in con.execute('PRAGMA table_info(checks)').fetchall()][4:]
        total = con.execute('SELECT count(*) FROM checks').fetchone()[0]
        results = []
        for name in rule_names:
            failures = con.execute(f'SELECT count(*) FROM checks WHERE {name}').fetchone()[0]
            results.append({'rule': name, 'failures': failures, 'failure_rate': round(failures / total, 6) if total else None})
        export_path = str((out / 'record_checks.csv').resolve()).replace("'", "''")
        con.execute(f"COPY checks TO '{export_path}' (FORMAT CSV, HEADER TRUE)")
        report = {'source_file': source.name, 'source_reference': SOURCE_URL, 'state_filter': 'SP', 'source_rows': source_count, 'record_count': total,
                  'note': 'Counts are per-rule and may overlap. No record is automatically excluded.', 'rules': results}
        (out / 'quality_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        with (out / 'quality_summary.md').open('w', encoding='utf-8') as f:
            f.write(f'# CNES Data Quality Report\n\nRows: **{total:,}**\n\n| Rule | Failures | Failure rate |\n|---|---:|---:|\n')
            for r in results:
                rate = 'N/A' if r['failure_rate'] is None else f"{r['failure_rate']:.2%}"
                f.write(f"| {r['rule']} | {r['failures']} | {rate} |\n")
            f.write('\nRules may overlap. These checks are exploratory and do not establish healthcare service quality.\n')
        return report
    finally:
        con.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to downloaded CNES CSV')
    parser.add_argument('--output', default='outputs')
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output), indent=2, ensure_ascii=False))
