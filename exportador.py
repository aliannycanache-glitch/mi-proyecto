import json
import pandas as pd
from modelo import SessionLocal, Familia, Miembro, Calle, RegistroGas
from sqlalchemy.orm import joinedload

# ==========================================
# 1. EXPORTACIÓN COMPLETA A EXCEL (Multi-hoja)
# ==========================================
def exportar_censo_a_excel(ruta_destino: str) -> bool:
    """
    Exporta TODAS las tablas de la BD a un único archivo Excel con pestañas.
    Soporta migración y adición de nuevos datos masivos.
    """
    session = SessionLocal()
    try:
        # A. Calles
        calles = session.query(Calle).all()
        filas_calles = [{
            "ID Calle": c.id,
            "Sector": c.sector,
            "Nombre Calle": c.nombre,
            "Número": c.numero or ""
        } for c in calles]

        # B. Familias
        familias = session.query(Familia).options(
            joinedload(Familia.miembros),
            joinedload(Familia.calle)
        ).all()

        filas_familias = []
        filas_miembros = []

        for f in familias:
            filas_familias.append({
                "ID Familia": f.id,
                "Tipo ID Jefe": f.tipo_id,
                "Cédula Jefe": f.cedula_jefe,
                "Nombres Jefe": f.nombres_jefe,
                "Apellidos Jefe": f.apellidos_jefe,
                "Teléfono Jefe": f.telefono_jefe or "",
                "Fecha Nacimiento Jefe": f.fecha_nacimiento_jefe.strftime("%Y-%m-%d") if f.fecha_nacimiento_jefe else "",
                "ID Calle": f.calle_id,
                "Nombre Calle": f.calle.nombre if f.calle else "",
                "N° Casa": f.casa_num or ""
            })

            for m in f.miembros:
                filas_miembros.append({
                    "ID Miembro": m.id,
                    "Cédula Jefe": f.cedula_jefe,  # Clave de Vinculación
                    "Tipo ID": m.tipo_id,
                    "Cédula Miembro": m.cedula,
                    "Nombres": m.nombres,
                    "Apellidos": m.apellidos,
                    "Parentesco": m.parentesco,
                    "Fecha Nacimiento": m.fecha_nacimiento.strftime("%Y-%m-%d") if m.fecha_nacimiento else ""
                })

        # C. Registros de Gas
        registros_gas = session.query(RegistroGas).options(joinedload(RegistroGas.familia)).all()
        filas_gas = [{
            "ID Registro Gas": r.id,
            "Cédula Jefe": r.familia.cedula_jefe if r.familia else "",
            "10kg": r.kg10,
            "18kg": r.kg18,
            "27kg": r.kg27,
            "43kg": r.kg43
        } for r in registros_gas]

        # Convertir a DataFrames
        df_calles = pd.DataFrame(filas_calles)
        df_familias = pd.DataFrame(filas_familias)
        df_miembros = pd.DataFrame(filas_miembros)
        df_gas = pd.DataFrame(filas_gas)

        # Escribir en Excel con openpyxl
        with pd.ExcelWriter(ruta_destino, engine="openpyxl") as writer:
            df_calles.to_excel(writer, sheet_name="Calles", index=False)
            df_familias.to_excel(writer, sheet_name="Familias", index=False)
            df_miembros.to_excel(writer, sheet_name="Miembros", index=False)
            df_gas.to_excel(writer, sheet_name="Gas Doméstico", index=False)

        return True

    except Exception as e:
        print(f"Error al exportar a Excel: {e}")
        return False
    finally:
        session.close()


# ==========================================
# 2. EXPORTACIÓN RESPALDO JSON (Full Backup)
# ==========================================
def exportar_backup_json(ruta_destino: str) -> bool:
    """Exporta toda la BD a un archivo JSON estructural perfecto para migrar de PC."""
    session = SessionLocal()
    try:
        data = {"calles": [], "familias": [], "registros_gas": []}

        # 1. Calles
        for c in session.query(Calle).all():
            data["calles"].append({
                "id": c.id, "sector": c.sector, "nombre": c.nombre, "numero": c.numero
            })

        # 2. Familias y Miembros
        for f in session.query(Familia).options(joinedload(Familia.miembros)).all():
            fam_dict = {
                "id": f.id,
                "nombres_jefe": f.nombres_jefe,
                "apellidos_jefe": f.apellidos_jefe,
                "tipo_id": f.tipo_id,
                "cedula_jefe": f.cedula_jefe,
                "telefono_jefe": f.telefono_jefe,
                "fecha_nacimiento_jefe": f.fecha_nacimiento_jefe.isoformat() if f.fecha_nacimiento_jefe else None,
                "calle_id": f.calle_id,
                "casa_num": f.casa_num,
                "miembros": [
                    {
                        "id": m.id,
                        "nombres": m.nombres,
                        "apellidos": m.apellidos,
                        "tipo_id": m.tipo_id,
                        "cedula": m.cedula,
                        "fecha_nacimiento": m.fecha_nacimiento.isoformat() if m.fecha_nacimiento else None,
                        "parentesco": m.parentesco
                    } for m in f.miembros
                ]
            }
            data["familias"].append(fam_dict)

        # 3. Gas
        for g in session.query(RegistroGas).all():
            data["registros_gas"].append({
                "id": g.id,
                "familia_id": g.familia_id,
                "kg10": g.kg10, "kg18": g.kg18, "kg27": g.kg27, "kg43": g.kg43
            })

        with open(ruta_destino, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True
    except Exception as e:
        print(f"Error al exportar JSON: {e}")
        return False
    finally:
        session.close()