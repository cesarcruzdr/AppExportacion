from django.db import models

# Create your models here.
import os
from django.db import models
import barcode
from barcode.writer import ImageWriter

# Constantes: peso del pallet
PESO_PALLET_KG = 5.0    # Ejemplo: 5 kg
PESO_PALLET_LB = 11.0   # Ejemplo: 11 lb

class Paleta(models.Model):
    TIPO_BATERIA = [
        ('BAU', 'Batería Automotriz'),
        ('B6V', 'Baterías 6 Voltios'),
    ]
    
    # Código de paleta: 8 dígitos, generado automáticamente.
    codigo_barra = models.CharField(max_length=8, unique=True, blank=True, null=True)
    tipo_bateria = models.CharField(max_length=3, choices=TIPO_BATERIA)
    # Peso que se ingresa (neto). Si se ingresa uno, se calcula el otro.
    peso_lb = models.FloatField(blank=True, null=True)
    peso_kg = models.FloatField(blank=True, null=True)
    # Fecha de creación (automática)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Usuario que crea la paleta.
    usuario_creador = models.CharField(max_length=100)
    
    # Propiedades para peso bruto (neto + constante)
    @property
    def peso_bruto_lb(self):
        return (self.peso_lb or 0) + PESO_PALLET_LB
    
    @property
    def peso_bruto_kg(self):
        return (self.peso_kg or 0) + PESO_PALLET_KG

    def save(self, *args, **kwargs):
        # Generar código automático si no existe
        if not self.codigo_barra:
            ultimo = Paleta.objects.all().order_by('-id').first()
            nuevo_codigo = int(ultimo.codigo_barra) + 1 if ultimo and ultimo.codigo_barra.isdigit() else 1
            self.codigo_barra = str(nuevo_codigo).zfill(8)
        
        # Conversión automática de pesos: si se ingresa un valor, se calcula el otro.
        if self.peso_lb and not self.peso_kg:
            self.peso_kg = round(self.peso_lb * 0.453592, 2)
        if self.peso_kg and not self.peso_lb:
            self.peso_lb = round(self.peso_kg * 2.20462, 2)
        
        super().save(*args, **kwargs)  # Se guarda para asignar ID

        # Generar el código de barras en la carpeta media/codigos
        ruta_carpeta = os.path.join('media', 'codigos')
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)
        ruta_archivo = os.path.join(ruta_carpeta, self.codigo_barra)
        ean = barcode.get('code128', self.codigo_barra, writer=ImageWriter())
        ean.save(ruta_archivo)
    
    def __str__(self):
        return self.codigo_barra or ""

##Modelo PackingList
from django.core.exceptions import ValidationError

class PackingList(models.Model):
    # El nombre se genera automáticamente en el formato "PL" + 7 dígitos.
    nombre = models.CharField(max_length=9, unique=True, blank=True, null=True)
    # Relación ManyToMany con Paleta.
    paletas = models.ManyToManyField(Paleta, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    ##Agregado para modelos
    def total_peso_lb(self):
        return sum(p.peso_lb for p in self.paletas.all()) + self.paletas.count() * PESO_PALLET_LB

    def total_peso_kg(self):
        return sum(p.peso_kg for p in self.paletas.all()) + self.paletas.count() * PESO_PALLET_KG
    # Campos para almacenar peso neto y peso bruto.
    peso_neto_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_neto_lb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_bruto_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_bruto_lb = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calcular_pesos(self):
        # Sumar el peso neto de todas las paletas asociadas
        total_neto_kg = sum(p.peso_kg for p in self.paletas.all())
        total_neto_lb = sum(p.peso_lb for p in self.paletas.all())
        # Calcular peso bruto sumando la constante por cada paleta
        self.peso_neto_kg = total_neto_kg
        self.peso_neto_lb = total_neto_lb
        self.peso_bruto_kg = total_neto_kg + (self.paletas.count() * PESO_PALLET_KG)
        self.peso_bruto_lb = total_neto_lb + (self.paletas.count() * PESO_PALLET_LB)
        # Se guarda la instancia actualizada
        super().save()

    def clean(self):
        # Validación: evitar que una paleta se asocie a más de un PackingList.
        for paleta in self.paletas.all():
            qs = PackingList.objects.filter(paletas=paleta)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(f"La paleta {paleta.codigo_barra} ya está asignada a otro Packing List.")

    def save(self, *args, **kwargs):
        if not self.nombre:
            ultimo = PackingList.objects.all().order_by('-id').first()
            if ultimo and ultimo.nombre and ultimo.nombre.startswith("PL") and ultimo.nombre[2:].isdigit():
                nuevo_codigo = int(ultimo.nombre[2:]) + 1
            else:
                nuevo_codigo = 1
            self.nombre = "PL" + str(nuevo_codigo).zfill(7)
        super().save(*args, **kwargs)
        # Una vez guardado, actualizamos los pesos
        self.calcular_pesos()

    def __str__(self):
        return self.nombre or ""
