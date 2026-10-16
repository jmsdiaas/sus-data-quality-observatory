# SUS Data Quality Observatory — São Paulo (V2)

Auditoria reprodutível de qualidade cadastral dos estabelecimentos registrados no **CNES/DATASUS, competência 202609**. O CNES inclui estabelecimentos públicos e privados; este estudo **não mede a qualidade da assistência médica**.

## Resultados

- `reports/resumo_qualidade.json`: indicadores estaduais
- `reports/indicadores_municipios.csv`: indicadores por município
- `reports/cnes_repetidos.csv`: possíveis duplicidades de CO_CNES
- `reports/unidades_repetidas.csv`: possíveis duplicidades de CO_UNIDADE

## Método

A seleção de SP usa os seis primeiros dígitos de `CO_UNIDADE`, que correspondem ao código municipal IBGE/CNES, confirmados pela tabela oficial `tbMunicipio202609.csv` (`CO_SIGLA_ESTADO = SP`). `CO_MUNICIPIO_GESTOR` é analisado separadamente, pois o município gestor pode diferir do município da unidade. O processamento utiliza leitura em streaming com a biblioteca padrão do Python, sem Pandas ou Colab.

Indicadores de completude e formato são **sinais de qualidade cadastral**, não evidências de fraude ou de mau atendimento. Repetições são alertas para investigação, não erros confirmados. Coordenadas inválidas verificam limites globais, não a posição exata dentro do estado. Dados de contato pessoal e identificação sensível não são exportados.

## Reprodução

Coloque os arquivos oficiais `tbEstabelecimento202609.csv` e `tbMunicipio202609.csv` em uma pasta local e execute na raiz do projeto:

```bash
python -m src.analyze_cnes --estabelecimentos /caminho/tbEstabelecimento202609.csv --municipios /caminho/tbMunicipio202609.csv --saida reports
python -m unittest discover -s tests -v
```

Os CSVs brutos oficiais não estão incluídos no ZIP, pois são grandes. Os relatórios gerados a partir deles estão incluídos.

## Fonte

Ministério da Saúde / DATASUS — Cadastro Nacional de Estabelecimentos de Saúde (CNES), competência setembro de 2026. Dados consultados a partir dos arquivos fornecidos para o projeto.
