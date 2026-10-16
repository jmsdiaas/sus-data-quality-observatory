"""CNES 202609: reproducible streaming data-quality audit of São Paulo establishments."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ('CO_UNIDADE', 'CO_CNES', 'CO_MUNICIPIO_GESTOR', 'NO_FANTASIA', 'CO_CEP', 'NU_LATITUDE', 'NU_LONGITUDE')

def audit(establishments: Path, municipalities: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with municipalities.open(encoding='latin-1', newline='') as f:
        municipalities_sp = {r['CO_MUNICIPIO'].strip(): r['NO_MUNICIPIO'].strip() for r in csv.DictReader(f, delimiter=';') if r['CO_SIGLA_ESTADO'].strip() == 'SP'}
    stats = Counter()
    city_stats = defaultdict(Counter)
    cnes_counts = Counter()
    unit_counts = Counter()
    with establishments.open(encoding='latin-1', newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        missing_cols = set(FIELDS) - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(f'Colunas ausentes: {sorted(missing_cols)}')
        for row in reader:
            stats['registros_brasil'] += 1
            unit = row['CO_UNIDADE'].strip()
            municipality_from_unit = unit[:6] if len(unit) >= 6 else ''
            if municipality_from_unit not in municipalities_sp:
                continue
            stats['registros_sp'] += 1
            city = city_stats[municipality_from_unit]
            city['registros'] += 1
            cnes = row['CO_CNES'].strip()
            if not cnes:
                stats['cnes_ausente'] += 1
                city['cnes_ausente'] += 1
            else:
                cnes_counts[cnes] += 1
                if not re.fullmatch(r'\d{7}', cnes):
                    stats['cnes_formato_invalido'] += 1
                    city['cnes_formato_invalido'] += 1
            if unit:
                unit_counts[unit] += 1
            else:
                stats['unidade_ausente'] += 1
            if row['CO_MUNICIPIO_GESTOR'].strip() != municipality_from_unit:
                stats['municipio_gestor_diferente_municipio_unidade'] += 1
                city['municipio_gestor_diferente_municipio_unidade'] += 1
            if not row['NO_FANTASIA'].strip():
                stats['nome_fantasia_ausente'] += 1
                city['nome_fantasia_ausente'] += 1
            cep = row['CO_CEP'].strip()
            if not cep:
                stats['cep_ausente'] += 1
                city['cep_ausente'] += 1
            elif not re.fullmatch(r'\d{8}', cep):
                stats['cep_formato_invalido'] += 1
                city['cep_formato_invalido'] += 1
            lat, lon = row['NU_LATITUDE'].strip(), row['NU_LONGITUDE'].strip()
            if not lat or not lon:
                stats['coordenadas_ausentes_ou_incompletas'] += 1
                city['coordenadas_ausentes_ou_incompletas'] += 1
            else:
                try:
                    latitude, longitude = float(lat.replace(',', '.')), float(lon.replace(',', '.'))
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or latitude == 0 and longitude == 0:
                        stats['coordenadas_invalidas'] += 1
                        city['coordenadas_invalidas'] += 1
                except ValueError:
                    stats['coordenadas_invalidas'] += 1
                    city['coordenadas_invalidas'] += 1
    duplicate_cnes = [(c, n) for c, n in cnes_counts.items() if n > 1]
    duplicate_units = [(c, n) for c, n in unit_counts.items() if n > 1]
    stats['cnes_distintos_nao_vazios'] = len(cnes_counts)
    stats['cnes_repetidos_identificadores'] = len(duplicate_cnes)
    stats['cnes_repetidos_registros_excedentes'] = sum(n-1 for _, n in duplicate_cnes)
    stats['co_unidade_repetidas_identificadores'] = len(duplicate_units)
    stats['co_unidade_repetidas_registros_excedentes'] = sum(n-1 for _, n in duplicate_units)
    stats['municipios_sp_na_referencia'] = len(municipalities_sp)
    stats['municipios_sp_com_registros'] = len(city_stats)
    result = {'competencia': '202609', 'fonte': 'DATASUS CNES', 'escopo': 'SP por prefixo de 6 dígitos de CO_UNIDADE validado contra tbMunicipio', 'metricas': dict(stats)}
    (output / 'resumo_qualidade.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'indicadores_municipios.csv').open('w', encoding='utf-8-sig', newline='') as f:
        columns = ['codigo_municipio', 'municipio', 'registros', 'cnes_ausente', 'cnes_formato_invalido', 'nome_fantasia_ausente', 'cep_ausente', 'cep_formato_invalido', 'coordenadas_ausentes_ou_incompletas', 'coordenadas_invalidas', 'municipio_gestor_diferente_municipio_unidade']
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for code, values in sorted(city_stats.items(), key=lambda x: -x[1]['registros']):
            writer.writerow({'codigo_municipio': code, 'municipio': municipalities_sp[code], **{k: values[k] for k in columns[2:]}})
    with (output / 'cnes_repetidos.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['co_cnes', 'ocorrencias']); writer.writerows(sorted(duplicate_cnes, key=lambda x: -x[1]))
    with (output / 'unidades_repetidas.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['co_unidade', 'ocorrencias']); writer.writerows(sorted(duplicate_units, key=lambda x: -x[1]))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--estabelecimentos', type=Path, required=True)
    parser.add_argument('--municipios', type=Path, required=True)
    parser.add_argument('--saida', type=Path, default=Path('reports'))
    args = parser.parse_args()
    print(json.dumps(audit(args.estabelecimentos, args.municipios, args.saida), ensure_ascii=False, indent=2))
