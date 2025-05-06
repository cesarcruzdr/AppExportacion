from django.urls import path
from . import views
from .views import EditarPaletaView

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('agregar/', views.agregar_paleta, name='agregar_paleta'),
    path('imprimir_etiqueta/<int:paleta_id>/', views.imprimir_etiqueta, name='imprimir_etiqueta'),
    # Para crear un PackingList desde el flujo Manual (único lugar para crear)
    path('packing_list/manual/', views.packing_list_manual, name='packing_list_manual'),
    # Listado CRUD de PackingList
    path('packing_list/lista/', views.lista_packing_list, name='lista_packing_list'),
    path('packing_list/editar/<int:pk>/', views.editar_packing_list, name='editar_packing_list'),
    path('packing_list/eliminar/<int:pk>/', views.eliminar_packing_list, name='eliminar_packing_list'),
    # Nueva ruta para imprimir Packing List:
    path('packing_list/imprimir/<int:pk>/', views.imprimir_packing_list, name='imprimir_packing_list'),
    ## URL para el historial de limpieza
    path('limpieza/historial/', views.historial_limpieza, name='historial_limpieza'),
    path('packing_list/lista/', views.lista_packing_list, name='lista_packing_list'),
    path('paleta/editar/<int:pk>/', EditarPaletaView.as_view(), name='editar_paleta'),    
    path('packing_list/manual/<str:codigos_str>/', views.packing_list_manual, name='packing_list_manual'),   
    ]