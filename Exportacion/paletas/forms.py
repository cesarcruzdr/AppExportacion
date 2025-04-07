from django import forms
from .models import Paleta, PackingList

class PaletaForm(forms.ModelForm):
    class Meta:
        model = Paleta
        fields = ['tipo_bateria', 'peso_kg', 'peso_lb']

class PackingListForm(forms.ModelForm):
    class Meta:
        model = PackingList
        # Excluir 'nombre' para que se genere automáticamente
        fields = ['paletas']
    
    def clean_paletas(self):
        paletas = self.cleaned_data.get('paletas')
        for paleta in paletas:
            qs = PackingList.objects.filter(paletas=paleta)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"La paleta {paleta.codigo_barra} ya está asignada a otro Packing List.")
        return paletas
