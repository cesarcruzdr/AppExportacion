from django.db import models
import os
import barcode
import locale
from barcode.writer import ImageWriter
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

# Constantes: peso del pallet
PESO_PALLET_KG = 25.0    # Ejemplo: 5 kg
PESO_PALLET_LB = 55.0   # Ejemplo: 11 lb


class Paleta(models.Model):
    TIPO_BATERIA = [
        ('BAU', 'Batería Automotriz'),
        ('B6V', 'Baterías 6 Voltios'),
        ('BI', 'Baterías Industriales'),
        ('MOT', 'Baterías para motocicleta'),  
        ('MIX', 'Baterías Mixtas'),
    ]
    LOCALIDAD = [('EXH','EX-Haina'),
        ('BIO','Bido'),
        ('HAI','Haina'),
        ('HER','Herrera'),
        ('STGO','Santiago'),        
    ]
    usuario_creador = models.CharField(max_length=255, blank=True, null=True)
    # Código de paleta: 8 dígitos, generado automáticamente.
    localidad = models.CharField(max_length=100, choices=LOCALIDAD, blank=True, null=True)
    codigo_barra = models.CharField(max_length=8, unique=True, blank=True, null=True)
    tipo_bateria = models.CharField(max_length=3, choices=TIPO_BATERIA)
    # Peso que se ingresa (bruto). Si se ingresa uno, se calcula el otro.
    peso_bruto_lb = models.FloatField(blank=True, null=True)
    peso_bruto_kg = models.FloatField(blank=True, null=True)
    cantidad_baterias = models.PositiveIntegerField()
    # Fecha de creación (automática)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Usuario que crea la paleta.
    usuario_creador = models.CharField(max_length=100)
    


    # Propiedades para peso neto (bruto - constante)
    @property
    def peso_neto_lb(self):
        return round((self.peso_bruto_lb or 0) - PESO_PALLET_LB,2)

    @property
    def peso_neto_kg(self):
        return round((self.peso_bruto_kg or 0) - PESO_PALLET_KG,2)
    
    @property
    def peso_promedio_kg(self):
        if self.cantidad_baterias > 0:
            return round(self.peso_bruto_kg / self.cantidad_baterias, 2)
        return 0


    def save(self, *args, **kwargs):      
        if not self.codigo_barra:
            ultimo = Paleta.objects.all().order_by('-id').first()
            nuevo_codigo = int(ultimo.codigo_barra) + 1 if ultimo and ultimo.codigo_barra and ultimo.codigo_barra.isdigit() else 1
            self.codigo_barra = str(nuevo_codigo).zfill(8)

        try:
            original = Paleta.objects.get(pk=self.pk)
        except Paleta.DoesNotExist:
            original = None

        # Lógica de conversión inteligente
        if original:
            kg_cambiado = self.peso_bruto_kg != original.peso_bruto_kg
            lb_cambiado = self.peso_bruto_lb != original.peso_bruto_lb

            if kg_cambiado and self.peso_bruto_kg:
                self.peso_bruto_lb = round(self.peso_bruto_kg * 2.20462, 2)
            elif lb_cambiado and self.peso_bruto_lb:
                self.peso_bruto_kg = round(self.peso_bruto_lb * 0.453592, 2)
        else:
            # Si es una nueva instancia
            if self.peso_bruto_kg and not self.peso_bruto_lb:
                self.peso_bruto_lb = round(self.peso_bruto_kg * 2.20462, 2)
            elif self.peso_bruto_lb and not self.peso_bruto_kg:
                self.peso_bruto_kg = round(self.peso_bruto_lb * 0.453592, 2)

        super().save(*args, **kwargs)

        # Generar código de barras
        ruta_carpeta = os.path.join('media', 'codigos')
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)
        ruta_archivo = os.path.join(ruta_carpeta, self.codigo_barra)
        ean = barcode.get('code128', self.codigo_barra, writer=ImageWriter())
        ean.save(ruta_archivo)

    def __str__(self):
        return self.codigo_barra or ""

##Modelo PackingList
class PackingList(models.Model):
    # El nombre se genera automáticamente en el formato "PL" + 7 dígitos.
    nombre = models.CharField(max_length=9, unique=True, blank=True, null=True)
    # Relación ManyToMany con Paleta.
    paletas = models.ManyToManyField(Paleta, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    ##Agregado para modelos
    def total_peso_bruto_lb(self):
        return sum(p.peso_bruto_lb for p in self.paletas.all())

    def total_peso_bruto_kg(self):
        return sum(p.peso_bruto_kg for p in self.paletas.all())

    # Campos para almacenar peso neto y peso bruto.
    peso_neto_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_neto_lb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_bruto_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_bruto_lb = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calcular_pesos(self):
        # Sumar el peso bruto de todas las paletas asociadas
        total_bruto_kg = sum(p.peso_bruto_kg for p in self.paletas.all())
        total_bruto_lb = sum(p.peso_bruto_lb for p in self.paletas.all())
        # Calcular peso neto restando la constante por cada paleta
        self.peso_bruto_kg = total_bruto_kg
        self.peso_bruto_lb = total_bruto_lb
        self.peso_neto_kg = total_bruto_kg - (self.paletas.count() * PESO_PALLET_KG)
        self.peso_neto_lb = total_bruto_lb - (self.paletas.count() * PESO_PALLET_LB)
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

##CONFIGURACION PARA FORMATO DE IMPRESION
class ConfiguracionImpresionEtiqueta(models.Model):
    nombre = models.CharField(max_length=50, help_text="Ej: Etiqueta 4x6 pulgadas")
    ancho_pulgadas = models.FloatField(default=4.0)
    alto_pulgadas = models.FloatField(default=6.0)

    def __str__(self):
        return self.nombre

##MODELO HISTORIAL DE LIMPIEZA
class HistorialLimpieza(models.Model):
    usuario = models.CharField(max_length=100)
    ip_usuario = models.GenericIPAddressField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    def __str__(self):
        return f"{self.fecha.strftime('%d/%m/%Y %H:%M:%S')} - {self.usuario}"