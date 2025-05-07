from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth.decorators import login_required
from .models import Paleta, PackingList
from .forms import PaletaForm, PackingListForm
from django.core.paginator import Paginator
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required
from django.db import models
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth import forms
from django.contrib.auth.mixins import LoginRequiredMixin
import locale
import os
from django.conf import settings
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Table, TableStyle, Frame
from .models import ConfiguracionImpresionEtiqueta
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseBadRequest

def login_view(request):
    # Comprobamos si el usuario ya está autenticado
    if request.user.is_authenticated:
        return redirect('home')  # Redirige a la página principal si el usuario ya está logueado

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Si el formulario es válido, autentica al usuario
            user = form.get_user()
            login(request, user)
            return redirect('home')  # Redirigir a la página principal después del login exitoso
        else:
            # Si el formulario no es válido, vuelve a mostrar el login con errores
            return render(request, 'login.html', {'form': form})
    else:
        # Si el formulario no fue enviado, simplemente muestra el formulario de login vacío
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

class PaletaUpdateView(UpdateView):
    model = Paleta
    form_class = PaletaForm
    template_name = 'editar_paleta.html'
    success_url = reverse_lazy('home')  # <-- Agrega esto

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.POST.get("accion") == "recibir":
            nueva_localidad = self.request.POST.get("localidad_recibir")
            if nueva_localidad:
                self.object.localidad = nueva_localidad
                self.object.save()

        return response


class EditarPaletaView(LoginRequiredMixin, UpdateView):
    model = Paleta
    fields = ['tipo_bateria', 'peso_bruto_lb', 'peso_bruto_kg', 'cantidad_baterias','localidad']
    template_name = 'paletas/editar_paleta.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        # Asignamos el usuario como el creador de la paleta
        form.instance.usuario_creador = self.request.user.username
        
        # Llamamos al método del padre para procesar el formulario
        return super().form_valid(form)


def home_view(request):
    return render(request, 'home.html')  # Este es un ejemplo, usa tu vista de inicio real

def home(request):
    cantidad = request.GET.get('cantidad', 15)
    try:
        cantidad = int(cantidad)
    except ValueError:
        cantidad = 15

    paletas_list = Paleta.objects.all().order_by('-fecha_creacion')
    paginator = Paginator(paletas_list, cantidad)
    page_number = request.GET.get('page')
    paletas = paginator.get_page(page_number)

    return render(request, 'paletas/home.html', {
        'paletas': paletas,
        'cantidad': cantidad
    })

##Vista para Agregar Paleta
@login_required
def agregar_paleta(request):
    if request.method == "POST":
        form = PaletaForm(request.POST)
        if form.is_valid():
            paleta = form.save(commit=False)
            paleta.usuario_creador = request.user
            paleta.save()
            return redirect('home')
    else:
        form = PaletaForm()
    return render(request, 'paletas/agregar_paleta.html', {'form': form})


##Vista para Imprimir Etiqueta
from reportlab.lib.units import inch
import locale
from .models import ConfiguracionImpresionEtiqueta

# Configurar el locale
locale.setlocale(locale.LC_ALL, 'es_DO.UTF-8')


def imprimir_etiqueta(request, paleta_id):
    paleta = get_object_or_404(Paleta, id=paleta_id)

    # Obtener tamaño de etiqueta desde la configuración
    config = ConfiguracionImpresionEtiqueta.objects.first()
    if config:
        ancho = config.ancho_pulgadas * inch
        alto = config.alto_pulgadas * inch
    else:
        from reportlab.lib.pagesizes import letter
        ancho, alto = letter  # fallback

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Etiqueta_{paleta.codigo_barra}.pdf"'

    pdf = canvas.Canvas(response, pagesize=(ancho, alto))
    pdf.setFont("Helvetica", 12)

    offset_y = alto - 20
    pdf.drawCentredString(ancho / 2, offset_y, "Información de la Paleta")
    offset_y -= 30

    pdf.drawString(50, alto - 40, f"Código de Paleta: {paleta.codigo_barra}, Fecha Creacion: {paleta.fecha_creacion.strftime('%d-%m-%Y')}")
    pdf.drawString(50, alto - 60, f"Usuario Creador: {paleta.usuario_creador}")
    pdf.drawString(50, alto - 80, f"Cantidad de Baterías: {paleta.cantidad_baterias}")
    pdf.drawString(50, alto - 100, f"Peso Bruto (KG): {locale.format_string('%.2f', paleta.peso_bruto_kg, grouping=True)}")
    pdf.drawString(50, alto - 120, f"Peso Bruto (LB): {locale.format_string('%.2f', paleta.peso_bruto_lb, grouping=True)}")
    pdf.drawString(50, alto - 140, f"Peso Neto (KG): {locale.format_string('%.2f', paleta.peso_neto_kg, grouping=True)}")
    pdf.drawString(50, alto - 160, f"Peso Neto (LB): {locale.format_string('%.2f', paleta.peso_neto_lb, grouping=True)}")

    # Imagen pictograma adicional
    ruta_pictograma = os.path.join(settings.MEDIA_ROOT, 'pictogramas', 'corrosive.png')
    if os.path.exists(ruta_pictograma):
        try:
            pdf.drawImage(ruta_pictograma, 400, alto - 180, width=100, height=100)
        except Exception as e:
            pdf.drawString(50, alto - 180, f"Error al cargar pictograma: {str(e)}")

    # Código de barras
    ruta_codigo_barra = f"media/codigos/{paleta.codigo_barra}.png"
    try:
        pdf.drawImage(ruta_codigo_barra, 50, alto - 300, width=300, height=150)
    except Exception:
        pdf.drawString(50, alto - 200, "Código de barras no disponible")
        

    pdf.showPage()
    pdf.save()
    return response

##Vista para Crear PackingList Manual
@login_required
def packing_list_manual(request):
    MAX_PESO_LB = 56000
    MIN_PESO_LB = 54500

    if request.method == "POST":
        codigos_str = request.POST.get('codigos', '')
        codigos_list = codigos_str.split(',') if codigos_str else []
        codigos = [c.strip() for c in codigos_str.split(',') if c.strip()]
        paletas = Paleta.objects.filter(codigo_barra__in=codigos).exclude(packinglist__isnull=False)

        if not paletas.exists():
            messages.error(request, "⚠️ No se seleccionaron paletas válidas o ya están en otro Packing List.")
            return render(request, 'paletas/packing_list_manual.html', {'codigos_str': codigos_str})

        total_bruto_lb = sum(p.peso_bruto_lb or 0 for p in paletas)
        total_bruto_kg = sum(p.peso_bruto_kg or 0 for p in paletas)
        total_neto_lb = sum(p.peso_neto_lb or 0 for p in paletas)
        total_neto_kg = sum(p.peso_neto_kg or 0 for p in paletas)
        total_baterias = sum(p.cantidad_baterias or 0 for p in paletas)

        faltante_minimo = max(0, MIN_PESO_LB - total_bruto_lb)
        margen_restante = max(0, MAX_PESO_LB - total_bruto_lb)

        if 'eliminar_codigo' in request.POST:
                    eliminar_codigo = request.POST.get('eliminar_codigo')
                    codigos = [c for c in codigos if c and c != eliminar_codigo]
                    codigos_str = ','.join(codigos)
                    codigos_list = codigos
                    paletas = Paleta.objects.filter(codigo_barra__in=codigos).exclude(packinglist__isnull=False)
                    
                    # Calcular nuevamente
                    total_bruto_lb = sum(p.peso_bruto_lb or 0 for p in paletas)
                    total_bruto_kg = sum(p.peso_bruto_kg or 0 for p in paletas)
                    total_neto_lb = sum(p.peso_neto_lb or 0 for p in paletas)
                    total_neto_kg = sum(p.peso_neto_kg or 0 for p in paletas)
                    total_baterias = sum(p.cantidad_baterias or 0 for p in paletas)
                    faltante_minimo = max(0, MIN_PESO_LB - total_bruto_lb)
                    margen_restante = max(0, MAX_PESO_LB - total_bruto_lb)


        if total_bruto_lb > MAX_PESO_LB:
            messages.error(request, "❌ El peso bruto total supera el máximo permitido de 56,000 lb.")
            return render(request, 'paletas/packing_list_manual.html', {
                'codigos_str': codigos_str,
                'paletas': paletas,
                'total_bruto_kg': round(total_bruto_kg, 2),
                'total_bruto_lb': round(total_bruto_lb, 2),
                'total_neto_kg': round(total_neto_kg, 2),
                'total_neto_lb': round(total_neto_lb, 2),
                'total_baterias': total_baterias,
                'faltante_minimo': round(faltante_minimo, 2),
                'margen_restante': round(margen_restante, 2),
                'preview': True,
            })
                       

        if 'confirmar' in request.POST:
            # Confirmación: crear packing list
            packing_list = PackingList()
            packing_list.save()
            packing_list.paletas.set(paletas)
            packing_list.save()

            messages.success(request, f"✅ Packing List '{packing_list.nombre}' creado correctamente.")
            
            # Generar PDF PACKING LIST
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Packing_List_{packing_list.nombre}.pdf"'
            pdf = canvas.Canvas(response, pagesize=letter)
            pdf.setFont("Helvetica", 12)

            pdf.drawString(100, 750, f"Packing List: {packing_list.nombre}")
            pdf.drawString(100, 730, f"Fecha: {packing_list.fecha_creacion.strftime('%Y-%m-%d')}")
            pdf.drawString(100, 710, f"Total Peso Neto KG: {total_neto_kg:.2f}")
            pdf.drawString(100, 690, f"Total Peso Neto LB: {total_neto_lb:.2f}")
            pdf.drawString(100, 670, f"Total Peso Bruto KG: {total_bruto_kg:.2f}")
            pdf.drawString(100, 650, f"Total Peso Bruto LB: {total_bruto_lb:.2f}")
            pdf.drawString(100, 630, f"Total Cantidad de Baterías: {total_baterias}")

            y = 610
            for paleta in paletas:
                pdf.drawString(100, y, f"Paleta {paleta.codigo_barra} - Cantidad: {paleta.cantidad_baterias}, Neto KG: {paleta.peso_neto_kg}, Bruto LB: {paleta.peso_bruto_lb}")
                y -= 20

            pdf.showPage()
            pdf.save()
            return response

        # Mostrar vista previa
        return render(request, 'paletas/packing_list_manual.html', {
            'paletas': paletas,
            'total_bruto_kg': round(total_bruto_kg, 2),
            'total_bruto_lb': round(total_bruto_lb, 2),
            'total_neto_kg': round(total_neto_kg, 2),
            'total_neto_lb': round(total_neto_lb, 2),
            'total_baterias': total_baterias,
            'faltante_minimo': round(faltante_minimo, 2),
            'margen_restante': round(margen_restante, 2),
            'preview': True,
            'codigos_str': codigos_str,
        })

    # GET: formulario vacío
    return render(request, 'paletas/packing_list_manual.html')



##VISTA IMPRIMIR PACKIGLIST
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def imprimir_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Packing_List_{packing_list.nombre}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_title = styles['Heading1']

    # Encabezado del documento
    elements.append(Paragraph(f"<b>Packing List: {packing_list.nombre}</b>", style_title))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Fecha de creación: {packing_list.fecha_creacion.strftime('%Y-%m-%d')}", style_normal))
    elements.append(Paragraph(f"Peso Neto Total: {packing_list.peso_neto_kg:.2f} KG / {packing_list.peso_neto_lb:.2f} LB", style_normal))
    elements.append(Paragraph(f"Peso Bruto Total: {packing_list.peso_bruto_kg:.2f} KG / {packing_list.peso_bruto_lb:.2f} LB", style_normal))

    total_baterias = sum(p.cantidad_baterias for p in packing_list.paletas.all())
    elements.append(Paragraph(f"Cantidad total de baterías: {total_baterias}", style_normal))

    elements.append(Spacer(1, 20))

    # Tabla de paletas
    data = [
        ['Código', 'Tipo', 'Cantidad', 'Neto KG', 'Neto LB', 'Bruto KG', 'Bruto LB']
    ]
    for paleta in packing_list.paletas.all():
        data.append([
            paleta.codigo_barra,
            paleta.tipo_bateria,
            paleta.cantidad_baterias,
            f"{paleta.peso_neto_kg:.2f}",
            f"{paleta.peso_neto_lb:.2f}",
            f"{paleta.peso_bruto_kg:.2f}",
            f"{paleta.peso_bruto_lb:.2f}"
        ])

    table = Table(data, colWidths=[65, 70, 60, 65, 65, 65, 65])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),

        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),

        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),

        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)

    doc.build(elements)
    return response


##Vistas CRUD para PackingList (Lista, Editar, Eliminar)

#Listar PackingList
def lista_packing_list(request):
    packing_lists = PackingList.objects.all().order_by('-fecha_creacion')
    return render(request, 'paletas/lista_packing_list.html', {'packing_lists': packing_lists})


#Editar PackingList
from django.contrib import messages

def editar_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    form = PackingListForm(instance=packing_list)

    # Paletas ya asignadas a este packing list (sin importar localidad)
    paletas_asignadas = packing_list.paletas.all()

    # Paletas disponibles: sin packing list Y de localidad 'HAI'
    paletas_disponibles = Paleta.objects.filter(
        packinglist__isnull=True,
        localidad='EXH'
    )

    # Unimos ambas queryset sin duplicados
    todas_las_paletas = (paletas_disponibles | paletas_asignadas).distinct()

    if request.method == "POST":
        form = PackingListForm(request.POST, instance=packing_list)
        if form.is_valid():
            selected_ids = request.POST.getlist('paletas')
            paletas_seleccionadas = Paleta.objects.filter(id__in=selected_ids)

            # Calcular peso bruto total
            peso_total_bruto_lb = sum(p.peso_bruto_lb for p in paletas_seleccionadas)

            # Validación del peso
            if peso_total_bruto_lb > 56000:
                messages.error(request, f"❌ El peso bruto total ({peso_total_bruto_lb:.2f} lb) excede el máximo permitido de 56,000 lb.")
            else:
                packing_list = form.save(commit=False)
                packing_list.paletas.clear()
                packing_list.save()
                packing_list.paletas.set(paletas_seleccionadas)
                packing_list.save()
                messages.success(request, f"✅ Packing List '{packing_list.nombre}' actualizado correctamente.")
                return redirect('lista_packing_list')

    return render(request, 'paletas/editar_packing_list.html', {
        'form': form,
        'packing_list': packing_list,
        'todas_las_paletas': todas_las_paletas,
    })


    
#Eliminar PackingList
def eliminar_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    if request.method == "POST":
        packing_list.delete()
        return redirect('lista_packing_list')
    return render(request, 'paletas/eliminar_packing_list.html', {'packing_list': packing_list})

## HISTORIAL DE LIMPIEZA DE PALETAS Y PICKING
from .models import HistorialLimpieza

def historial_limpieza(request):
    historial = HistorialLimpieza.objects.all().order_by('-fecha')
    return render(request, 'paletas/historial_limpieza.html', {'historial': historial})

## VISTA ASEGURADA
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(lambda u: u.is_superuser)
def historial_limpieza(request):
    historial = HistorialLimpieza.objects.all().order_by('-fecha')
    return render(request, 'paletas/historial_limpieza.html', {'historial': historial})
