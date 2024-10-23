from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Item

# @receiver(pre_save, sender=Item)
# def validate_item(sender, instance, **kwargs):
#     if Item.objects.filter(store=instance.store, code=instance.code).exclude(pk=instance.pk).exists():
#         raise ValidationError("Item com este Store e Code já existe.")
        
#     if instance.cfop == 5405 and instance.icms_cst != '60':
#         raise ValueError('Para CFOP 5405, o ICMS CST deve ser 60.')
    
#     if instance.cfop != 5405 and instance.icms_cst == '60':
#         raise ValueError('O ICMS CST 60 só pode ser usado com CFOP 5405.')

#     # if instance.icms_cst != '20' and instance.icms_aliquota != instance.icms_aliquota_reduzida:
#     #     instance.icms_aliquota_reduzida = instance.icms_aliquota

#     # if instance.cbenef and instance.cbenef.icms_cst != instance.icms_cst:
#     #     raise ValueError('O CBENEF selecionado não é válido para o ICMS CST escolhido.')

#     if instance.piscofins_cst:
#         instance.pis_aliquota = instance.pis_cst.aliquota
    
#     if instance.piscofins_cst:
#         instance.cofins_aliquota = instance.cofins_cst.aliquota

#     if instance.piscofins_cst and instance.piscofins_cst.code == '01' and instance.naturezareceita:
#         raise ValueError('Natureza Receita deve estar em branco quando PIS CST é 01.')

# @receiver(post_save, sender=Item)
# def update_status_item(sender, instance, **kwargs):
#     print(f"Item salvo: {instance.description}, Tipo: {instance.type_product}")
#     # Verifica se o type_product é diferente de 'Revenda'
#     if instance.type_product != 'Revenda':
#         print("Produto não é 'Revenda', atualizando o status para 3")
#         # Verifica se o status_item já não é 3
#         if instance.status_item != 3:
#             instance.status_item = 3
#             instance.save(update_fields=['status_item'])  # Atualiza o campo status_item
            
@receiver(pre_save, sender=Item)
def check_and_update_status_item(sender, instance, **kwargs):
    try:
        # Obtenha a instância original (antes da alteração)
        original_item = Item.objects.get(pk=instance.pk)
        # print(f"Codigo: {instance.code} - {instance.description}")

        # Verifique se o 'type_product' mudou
        if original_item.type_product != instance.type_product:
            print(f"Type_product alterado de {original_item.type_product} para {instance.type_product}")
            
            # Se o novo 'type_product' for diferente de 'Revenda', altere o 'status_item'
            if instance.type_product != 'Revenda':
                print("Novo type_product não é 'Revenda', alterando o status_item para 3")
                instance.status_item = 3
    except Item.DoesNotExist:
        # Se o item não existir (novo item), apenas continue
        print("Item novo, não há comparação com valores anteriores")            