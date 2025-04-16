from django.contrib import admin
from .models import (
    Cfop, IcmsCst, CBENEF, IcmsAliquota, 
    IcmsAliquotaReduzida, Protege, PisCofinsCst, NaturezaReceita
)

class CfopAdmin(admin.ModelAdmin):
    list_display = ('cfop', 'description', 'operation')
    search_fields = ('cfop', 'description')
    list_filter = ('operation',)

class IcmsCstAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

class CBENEFAdmin(admin.ModelAdmin):
    list_display = ('code', 'icms_cst', 'description')
    search_fields = ('code', 'icms_cst__code', 'description')
    list_filter = ('icms_cst',)

class IcmsAliquotaAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

class IcmsAliquotaReduzidaAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

class ProtegeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

class PisCofinsCstAdmin(admin.ModelAdmin):
    list_display = ('code', 'pis_aliquota', 'description', 'cofins_aliquota', 'type_company')
    search_fields = ('code', 'type_company', )

class NaturezaReceitaAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'ncm', 'piscofins_cst', 'category')
    search_fields = ('code', 'description', 'ncm', 'category')
    list_filter = ('piscofins_cst',)

admin.site.register(Cfop, CfopAdmin)
admin.site.register(IcmsCst, IcmsCstAdmin)
admin.site.register(CBENEF, CBENEFAdmin)
admin.site.register(IcmsAliquota, IcmsAliquotaAdmin)
admin.site.register(IcmsAliquotaReduzida, IcmsAliquotaReduzidaAdmin)
admin.site.register(Protege, ProtegeAdmin)
admin.site.register(PisCofinsCst, PisCofinsCstAdmin)
admin.site.register(NaturezaReceita, NaturezaReceitaAdmin)
