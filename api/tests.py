from django.test import TestCase
from api.serializers import ItemImportedModelSerializer

class ItemImportedModelSerializerTest(TestCase):
    def test_icms_aliquota_reduzida_sobrescrita_com_percentual_redbcde(self):
        data = {
            "code": "123",
            "barcode": "7890000000000",
            "description": "Produto Teste",
            "ncm": "12345678",
            "cest": "",
            "cfop": 5102,
            "icms_cst": 0,
            "icms_aliquota": 18.0,
            "icms_aliquota_reduzida": 18.0,  # será sobrescrito
            "protege": 0,
            "cbenef": "",
            "piscofins_cst": 1,
            "pis_aliquota": 0,
            "cofins_aliquota": 0,
            "naturezareceita": 0,
            "percentual_redbcde": 33.33
        }

        serializer = ItemImportedModelSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        validated = serializer.validated_data
        self.assertEqual(validated['icms_aliquota_reduzida'], 12.0)

    def test_icms_aliquota_reduzida_mantida_quando_sem_percentual_redbcde(self):
        data = {
            "code": "124",
            "barcode": "7890000000001",
            "description": "Produto Sem Percentual",
            "ncm": "12345678",
            "cest": "",
            "cfop": 5102,
            "icms_cst": 0,
            "icms_aliquota": 18.0,
            "icms_aliquota_reduzida": 15.0,  # deve manter este valor
            "protege": 0,
            "cbenef": "",
            "piscofins_cst": 1,
            "pis_aliquota": 0,
            "cofins_aliquota": 0,
            "naturezareceita": 0
        }

        serializer = ItemImportedModelSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        validated = serializer.validated_data
        self.assertEqual(validated['icms_aliquota_reduzida'], 15.0)
