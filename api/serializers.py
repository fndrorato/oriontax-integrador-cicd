from rest_framework import serializers
from items.models import Item, ImportedItem

class ItemModelSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source='code')
    codigo_barras = serializers.CharField(source='barcode')
    descricao = serializers.CharField(source='description')
    icms_cst = serializers.SerializerMethodField()    
    icms_aliquota = serializers.IntegerField(source='icms_aliquota_id')
    icms_aliquota_reduzida = serializers.SerializerMethodField()    
    redbcde = serializers.SerializerMethodField()
    redbcpara = serializers.SerializerMethodField()
    cbenef = serializers.SerializerMethodField()
    cofins_cst = serializers.SerializerMethodField()
    pis_cst = serializers.SerializerMethodField()
    natureza_receita = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'codigo',
            'codigo_barras',
            'ncm',
            'descricao',
            'cest',
            'cfop',
            'icms_cst',
            'icms_aliquota',
            'icms_aliquota_reduzida',
            'redbcde',
            'redbcpara',
            'cbenef',
            'protege',
            'pis_cst',
            'pis_aliquota',
            'cofins_cst',
            'cofins_aliquota',
            'natureza_receita',
        ]
        
    def get_icms_cst(self, obj):
        # Converte a string para inteiro
        try:
            return int(obj.icms_cst_id)
        except (ValueError, TypeError):
            return None  # Retorna None se a conversão falhar  
                
    def get_icms_aliquota_reduzida(self, obj):
        # Converte a string para inteiro
        try:
            return int(obj.icms_aliquota_reduzida)
        except (ValueError, TypeError):
            return None  # Retorna None se a conversão falhar        
        
    def get_redbcde(self, obj):
        aliquota_id = obj.icms_aliquota_id  # ID do modelo relacionado  
        icms_aliquota_reduzida = int(obj.icms_aliquota_reduzida)
        
        if aliquota_id == 0:
            return ''  # ou 0, dependendo do que você preferir
        return round((1 - (icms_aliquota_reduzida / aliquota_id)) * 100, 2)
    
    def get_redbcpara(self, obj):
        aliquota_id = obj.icms_aliquota_id  # ID do modelo relacionado 
        icms_aliquota_reduzida = int(obj.icms_aliquota_reduzida)
         
        if aliquota_id == 0:
            return ''  # ou 0, dependendo do que você preferir
        return round((icms_aliquota_reduzida / aliquota_id) * 100, 2)
    
    def get_cofins_cst(self, obj):
        # Obtém o código do modelo PisCofinsCst através da ForeignKey cofins_cst
        return obj.piscofins_cst.code if obj.piscofins_cst else None

    def get_pis_cst(self, obj):
        # Obtém o código do modelo PisCofinsCst através da ForeignKey pis_cst
        return obj.piscofins_cst.code if obj.piscofins_cst else None
    
    def get_cbenef(self, obj):
        return obj.cbenef.code if obj.cbenef else ''    
    
    def get_natureza_receita(self, obj):
        return obj.naturezareceita.code if obj.naturezareceita else ''        
    
        
class ItemImportedModelSerializer(serializers.ModelSerializer):
    percentual_redbcde = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = ImportedItem
        exclude = ['client']

    def validate(self, data):
        percentual = data.get('percentual_redbcde')
        if percentual is not None:
            aliquota = data.get('icms_aliquota', 0)
            if aliquota == 0:
                data['icms_aliquota_reduzida'] = 0
            else:
                data['icms_aliquota_reduzida'] = round(aliquota * (1 - percentual / 100), 2)
        return data


                