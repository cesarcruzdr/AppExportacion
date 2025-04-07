from django.shortcuts import render

# Create your views here.
##Vista Home (Listado de Paletas)
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth.decorators import login_required
from .models import Paleta, PackingList
from .forms import PaletaForm, PackingListForm

def home(request):
    paletas = Paleta.objects.all()
    return render(request, 'paletas/home.html', {'paletas': paletas})


##Vista para Agregar Paleta
@login_required
def agregar_paleta(request):
    if request.method == "POST":
        form = PaletaForm(request.POST)
        if form.is_valid():
            paleta = form.save(commit=False)
            paleta.usuario_creador = request.user.username
            paleta.save()
            return redirect('home')
    else:
        form = PaletaForm()
    return render(request, 'paletas/agregar_paleta.html', {'form': form})


##Vista para Imprimir Etiqueta
def imprimir_etiqueta(request, paleta_id):
    paleta = get_object_or_404(Paleta, id=paleta_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Etiqueta_{paleta.codigo_barra}.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, f"Código de Paleta: {paleta.codigo_barra}")
    pdf.drawString(100, 730, f"Fecha de Creación: {paleta.fecha_creacion.strftime('%Y-%m-%d')}")
    pdf.drawString(100, 710, f"Peso Neto LB: {paleta.peso_lb}")
    pdf.drawString(100, 690, f"Peso Neto KG: {paleta.peso_kg}")
    pdf.drawString(100, 670, f"Peso Bruto LB: {paleta.peso_bruto_lb}")
    pdf.drawString(100, 650, f"Peso Bruto KG: {paleta.peso_bruto_kg}")
    pdf.drawString(100, 630, f"Usuario Creador: {paleta.usuario_creador}")

    ruta_codigo_barra = f"media/codigos/{paleta.codigo_barra}.png"
    try:
        pdf.drawImage(ruta_codigo_barra, 100, 500, width=200, height=100)
    except Exception:
        pdf.drawString(100, 480, "Código de barras no disponible")

    pdf.showPage()
    pdf.save()
    return response


##Vista para Crear PackingList Manual
def packing_list_manual(request):
    if request.method == "POST":
        codigos_str = request.POST.get('codigos', '')
        codigos = [codigo.strip() for codigo in codigos_str.split(',') if codigo.strip()]
        # Filtrar paletas que NO estén ya asignadas a otro PackingList
        paletas = Paleta.objects.filter(codigo_barra__in=codigos).exclude(packinglist__isnull=False)
        if not paletas.exists():
            return HttpResponse("No se seleccionaron paletas disponibles o ya están en otro Packing List.")
        
        # Crear el PackingList
        packing_list = PackingList()
        packing_list.save()  # Se genera el nombre automáticamente
        packing_list.paletas.set(paletas)  # Asigna las paletas
        try:
            packing_list.full_clean()  # Validar que no existan conflictos
        except Exception as e:
            return HttpResponse(f"Error: {e}")
        packing_list.save()
        # Actualizar pesos: el método save() de PackingList llama a calcular_pesos()
        # Ahora, generar PDF
        total_kg = packing_list.total_peso_kg()
        total_lb = packing_list.total_peso_lb()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Packing_List_{packing_list.nombre}.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, 750, f"Packing List: {packing_list.nombre}")
        pdf.drawString(100, 730, f"Fecha de Creación: {packing_list.fecha_creacion.strftime('%Y-%m-%d')}")
        pdf.drawString(100, 710, f"Total Peso Neto KG: {packing_list.peso_neto_kg}")
        pdf.drawString(100, 690, f"Total Peso Neto LB: {packing_list.peso_neto_lb}")
        pdf.drawString(100, 670, f"Total Peso Bruto KG: {packing_list.peso_bruto_kg}")
        pdf.drawString(100, 650, f"Total Peso Bruto LB: {packing_list.peso_bruto_lb}")
        y = 630
        for paleta in packing_list.paletas.all():
            pdf.drawString(100, y, f"Paleta {paleta.codigo_barra} - Neto KG: {paleta.peso_kg}, Neto LB: {paleta.peso_lb}, Bruto LB: {paleta.peso_bruto_lb}, Bruto KG: {paleta.peso_bruto_kg}")
            y -= 20
        pdf.showPage()
        pdf.save()
        return response

    # En GET, se muestra un formulario para ingresar los códigos de paletas
    return render(request, 'paletas/packing_list_manual.html')

##VISTA IMPRIMIR PACKIGLIST
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def imprimir_packing_list(request, pk):
    # Recuperar el PackingList usando su primary key
    packing_list = get_object_or_404(PackingList, pk=pk)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Packing_List_{packing_list.nombre}.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, f"Packing List: {packing_list.nombre}")
    pdf.drawString(100, 730, f"Fecha de Creación: {packing_list.fecha_creacion.strftime('%Y-%m-%d')}")
    pdf.drawString(100, 710, f"Total Peso Neto KG: {packing_list.peso_neto_kg}")
    pdf.drawString(100, 690, f"Total Peso Neto LB: {packing_list.peso_neto_lb}")
    pdf.drawString(100, 670, f"Total Peso Bruto KG: {packing_list.peso_bruto_kg}")
    pdf.drawString(100, 650, f"Total Peso Bruto LB: {packing_list.peso_bruto_lb}")
    y = 630
    for paleta in packing_list.paletas.all():
        pdf.drawString(100, y, f"Paleta {paleta.codigo_barra} - Neto KG: {paleta.peso_kg}, Neto LB: {paleta.peso_lb}")
        y -= 20
    pdf.showPage()
    pdf.save()
    return response


##Vistas CRUD para PackingList (Lista, Editar, Eliminar)

#Listar PackingList
def lista_packing_list(request):
    packing_lists = PackingList.objects.all().order_by('-fecha_creacion')
    return render(request, 'paletas/lista_packing_list.html', {'packing_lists': packing_lists})

#Editar PackingList
def editar_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    if request.method == "POST":
        form = PackingListForm(request.POST, instance=packing_list)
        if form.is_valid():
            form.save()
            return redirect('lista_packing_list')
    else:
        form = PackingListForm(instance=packing_list)
    return render(request, 'paletas/editar_packing_list.html', {'form': form, 'packing_list': packing_list})

#Eliminar PackingList
def eliminar_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    if request.method == "POST":
        packing_list.delete()
        return redirect('lista_packing_list')
    return render(request, 'paletas/eliminar_packing_list.html', {'packing_list': packing_list})
