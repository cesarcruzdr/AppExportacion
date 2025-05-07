from django.contrib import admin
from .models import Paleta, PackingList, ConfiguracionImpresionEtiqueta

@admin.register(Paleta)
class PaletaAdmin(admin.ModelAdmin):
    list_display = ('codigo_barra', 'tipo_bateria', 'peso_bruto_lb', 'peso_bruto_kg','cantidad_baterias', 'fecha_creacion', 'usuario_creador')
    readonly_fields = ('codigo_barra',)

@admin.register(PackingList)
class PackingListAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_creacion', 'peso_neto_kg', 'peso_neto_lb', 'peso_bruto_kg', 'peso_bruto_lb')

##MODELO DE IMPRESION AGREGADO
admin.site.register(ConfiguracionImpresionEtiqueta)
