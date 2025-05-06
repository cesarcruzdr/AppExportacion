import os
import threading
import getpass
import socket

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from paletas.models import Paleta, PackingList, HistorialLimpieza

class TimeoutInput:
    def __init__(self, timeout):
        self.timeout = timeout
        self.result = None

    def input_with_timeout(self, prompt):
        def target():
            try:
                self.result = input(prompt)
            except EOFError:
                self.result = None

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(self.timeout)
        if thread.is_alive():
            return None  # Timeout alcanzado
        return self.result

class Command(BaseCommand):
    help = "Limpia las paletas, packing list y elimina los archivos de código de barras"

    def handle(self, *args, **kwargs):
        total_packing = PackingList.objects.count()
        total_paletas = Paleta.objects.count()

        self.stdout.write("🧹 LIMPIEZA DE BASE DE DATOS")
        self.stdout.write(f"🔎 Paletas registradas: {total_paletas}")
        self.stdout.write(f"🔎 Packing List registrados: {total_packing}")
        self.stdout.write("❗ ¿Estás seguro que deseas eliminar estos registros y archivos? (sí/no)")
        self.stdout.write("⌛ Tienes 30 segundos para responder...")

        input_manager = TimeoutInput(timeout=30)
        confirm = input_manager.input_with_timeout("👉 Confirmar: ")

        if not confirm or confirm.lower() not in ['si', 'sí', 's']:
            self.stdout.write(self.style.WARNING("❌ Operación cancelada (respuesta inválida o timeout)."))
            return

        # Eliminar relaciones M2M
        self.stdout.write("🔗 Eliminando relaciones entre paletas y packing list...")
        for pl in PackingList.objects.all():
            pl.paletas.clear()

        # Eliminar registros
        PackingList.objects.all().delete()
        Paleta.objects.all().delete()
        self.stdout.write("🗑️ Registros eliminados.")

        # Eliminar archivos de códigos de barra
        codigos_path = os.path.join(settings.MEDIA_ROOT, 'codigos')
        archivos_eliminados = 0
        if os.path.exists(codigos_path):
            for archivo in os.listdir(codigos_path):
                ruta = os.path.join(codigos_path, archivo)
                if os.path.isfile(ruta):
                    os.remove(ruta)
                    archivos_eliminados += 1
            self.stdout.write(f"🧹 Se eliminaron {archivos_eliminados} archivos de código de barras.")
        else:
            self.stdout.write("⚠️ La carpeta de códigos no existe.")

        # Reiniciar ID (sólo para SQLite o PostgreSQL)
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='paletas_paleta'")
            elif connection.vendor == 'postgresql':
                cursor.execute("ALTER SEQUENCE paletas_paleta_id_seq RESTART WITH 1")

        # Registrar en Historial
        usuario = getpass.getuser()
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except:
            ip = None

        HistorialLimpieza.objects.create(
            usuario=usuario,
            ip_usuario=ip,
            descripcion="Limpieza ejecutada desde comando limpiar_paletas."
        )

        # Resumen final
        self.stdout.write(self.style.SUCCESS("\n✅ LIMPIEZA COMPLETADA"))
        self.stdout.write("🧾 Resumen:")
        self.stdout.write(f"  🔸 Paletas eliminadas: {total_paletas}")
        self.stdout.write(f"  🔸 Packing List eliminados: {total_packing}")
        self.stdout.write(f"  🔸 Archivos eliminados: {archivos_eliminados}")