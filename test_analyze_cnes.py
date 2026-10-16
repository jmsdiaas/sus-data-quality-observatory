import csv
import tempfile
import unittest
from pathlib import Path
from src.analyze_cnes import audit

class AuditTest(unittest.TestCase):
    def test_sp_filter_and_missing_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (root / 'municipios.csv').open('w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['CO_MUNICIPIO', 'NO_MUNICIPIO', 'CO_SIGLA_ESTADO'])
                writer.writerow(['355030', 'SAO PAULO', 'SP'])
            with (root / 'estabelecimentos.csv').open('w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['CO_UNIDADE', 'CO_CNES', 'CO_MUNICIPIO_GESTOR', 'NO_FANTASIA', 'CO_CEP', 'NU_LATITUDE', 'NU_LONGITUDE'])
                writer.writerow(['3550301234567', '1234567', '355030', 'UNIDADE', '01001000', '', ''])
                writer.writerow(['2609607654321', '7654321', '260960', 'OUTRA', '50000000', '', ''])
            metrics = audit(root / 'estabelecimentos.csv', root / 'municipios.csv', root / 'reports')['metricas']
            self.assertEqual(metrics['registros_sp'], 1)
            self.assertEqual(metrics['coordenadas_ausentes_ou_incompletas'], 1)

if __name__ == '__main__':
    unittest.main()
