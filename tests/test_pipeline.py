import csv
from src.pipeline import run


def test_detects_quality_issues(tmp_path):
    p = tmp_path / 'sample.csv'
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['cnes','codigo_ibge','uf','municipio','cep','latitude','longitude'])
        w.writeheader()
        w.writerows([
            {'cnes':'1234567','codigo_ibge':'3550308','uf':'SP','municipio':'São Paulo','cep':'74000000','latitude':'-16.68','longitude':'-49.25'},
            {'cnes':'1234567','codigo_ibge':'3550308','uf':'SP','municipio':'São Paulo','cep':'bad','latitude':'999','longitude':'-49.25'},
            {'cnes':'','codigo_ibge':'','uf':'SP','municipio':'','cep':'','latitude':'','longitude':''},
            {'cnes':'7654321','codigo_ibge':'5208707','uf':'GO','municipio':'Goiânia','cep':'74000000','latitude':'-16.68','longitude':'-49.25'},
        ])
    report = run(str(p), str(tmp_path / 'out'))
    counts = {r['rule']: r['failures'] for r in report['rules']}
    assert report['record_count'] == 3
    assert counts['duplicate_cnes_in_snapshot'] == 2
    assert counts['missing_cnes'] == 1
    assert counts['invalid_cep_format'] == 1
    assert counts['invalid_latitude_br'] == 1
    assert (tmp_path / 'out' / 'quality_summary.md').exists()


def test_rejects_non_sp_only(tmp_path):
    p = tmp_path / 'other.csv'
    p.write_text('cnes,codigo_ibge,uf,municipio\n1234567,5208707,GO,Goiânia\n', encoding='utf-8')
    import pytest
    with pytest.raises(ValueError, match='No rows with UF=SP'):
        run(str(p), str(tmp_path / 'out'))
