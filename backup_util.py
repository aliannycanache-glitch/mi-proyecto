import os
import shutil
from datetime import datetime

def hacer_respaldo_automatico():
    # 1. Crear la carpeta "respaldos" inmediatamente si no existe
    carpeta_respaldos = "respaldos"
    if not os.path.exists(carpeta_respaldos):
        os.makedirs(carpeta_respaldos)
        print("📁 Carpeta 'respaldos' creada con éxito.")

    db_origen = "datos.db"
    
    # 2. Verificar si existe la base de datos
    if not os.path.exists(db_origen):
        print(f"⚠️ No se encontró el archivo '{db_origen}'. El respaldo se creará cuando exista la base de datos.")
        return

    # 3. Crear el nombre del respaldo con fecha y hora
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    db_destino = os.path.join(carpeta_respaldos, f"datos_backup_{timestamp}.db")

    try:
        shutil.copy2(db_origen, db_destino)
        print(f"✅ Respaldo automático generado con éxito: {db_destino}")
        limpiar_respaldos_antiguos(carpeta_respaldos, max_respaldos=10)
    except Exception as e:
        print(f"❌ Error al copiar el archivo de respaldo: {e}")

def limpiar_respaldos_antiguos(carpeta, max_respaldos=10):
    archivos = [
        os.path.join(carpeta, f) for f in os.listdir(carpeta)
        if f.startswith("datos_backup_") and f.endswith(".db")
    ]
    archivos.sort(key=os.path.getmtime)
    
    while len(archivos) > max_respaldos:
        archivo_a_borrar = archivos.pop(0)
        os.remove(archivo_a_borrar)
        print(f"🗑️ Respaldo antiguo eliminado: {archivo_a_borrar}")