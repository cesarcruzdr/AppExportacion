from django import forms
from .models import Paleta, PackingList

class PaletaForm(forms.ModelForm):
    class Meta:
        model = Paleta
        fields = ['tipo_bateria', 'peso_bruto_kg', 'peso_bruto_lb', 'cantidad_baterias','localidad']
        widgets = {
            'cantidad_baterias': forms.NumberInput(attrs={'min': 1}),
            'localidad': forms.TextInput(attrs={'class': 'Ingrese la localidad'}),
        }

#Cantidad de baterias no puede ir en blanco
    def clean_cantidad_baterias(self):
        cantidad_baterias = self.cleaned_data.get('cantidad_baterias')
        if cantidad_baterias is None or cantidad_baterias <= 0:
            raise forms.ValidationError("La cantidad de baterías no puede estar en blanco, Favor colocar las cantidades.")
        return cantidad_baterias

    def clean(self):
        cleaned_data = super().clean()
        peso_bruto_kg = cleaned_data.get('peso_bruto_kg')
        peso_bruto_lb = cleaned_data.get('peso_bruto_lb')
       
        return cleaned_data

class PackingListForm(forms.ModelForm):
    paletas = forms.ModelMultipleChoiceField(
        queryset=Paleta.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Paletas Asociadas"
    )
    class Meta:
        model = PackingList
        fields = ['nombre', 'paletas']

    def clean_paletas(self):
        paletas = self.cleaned_data.get('paletas')
        for paleta in paletas:
            qs = PackingList.objects.filter(paletas=paleta)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"La paleta {paleta.codigo_barra} ya está asignada a otro Packing List.")
        return paletas
