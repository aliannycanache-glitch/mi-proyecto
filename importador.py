import json
from datetime import datetime
import pandas as pd
from modelo import Calle, Familia, Miembro, RegistroGas, SessionLocal


def parsear_fecha(val):
    """Convierte cadenas o datetime de Excel a objeto datetime.date."""
    if pd.isna(val) or not val:
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    return None


# ==========================================
# 1. IMPORTACIÓN DESDE EXCEL
# ==========================================
def importar_censo_desde_excel(ruta_excel: str) -> bool:
    """Lee las hojas del Excel e inserta/actualiza las entidades respetando relaciones."""
    session = SessionLocal()
    try:
        xls = pd.ExcelFile(ruta_excel)

        # A. Procesar Calles
        if "Calles" in xls.sheet_names:
            df_calles = pd.read_excel(xls, "Calles", dtype=str)
            for _, fila in df_calles.iterrows():
                nombre = str(fila.get("Nombre Calle", "")).strip()
                sector = str(fila.get("Sector", "")).strip()
                if nombre:
                    calle = (
                        session.query(Calle)
                        .filter(Calle.nombre == nombre, Calle.sector == sector)
                        .first()
                    )
                    if not calle:
                        calle = Calle(
                            sector=sector,
                            nombre=nombre,
                            numero=str(fila.get("Número", "")),
                        )
                        session.add(calle)
            session.commit()

        # B. Procesar Familias (Jefes)
        if "Familias" in xls.sheet_names:
            df_familias = pd.read_excel(xls, "Familias", dtype=str)
            for _, fila in df_familias.iterrows():
                cedula = str(fila.get("Cédula Jefe", "")).strip()
                if not cedula:
                    continue

                # Buscar o Vincular Calle
                nombre_calle = str(fila.get("Nombre Calle", "")).strip()
                calle = (
                    session.query(Calle)
                    .filter(Calle.nombre == nombre_calle)
                    .first()
                    if nombre_calle
                    else None
                )
                calle_id = (
                    calle.id
                    if calle
                    else (
                        session.query(Calle).first().id
                        if session.query(Calle).first()
                        else None
                    )
                )

                if not calle_id:
                    # Crear calle por defecto si no existe ninguna
                    nueva_calle = Calle(sector="General", nombre="Principal")
                    session.add(nueva_calle)
                    session.commit()
                    calle_id = nueva_calle.id

                familia = (
                    session.query(Familia)
                    .filter(Familia.cedula_jefe == cedula)
                    .first()
                )

                datos_fam = {
                    "nombres_jefe": str(fila.get("Nombres Jefe", "")).strip(),
                    "apellidos_jefe": str(
                        fila.get("Apellidos Jefe", "")
                    ).strip(),
                    "tipo_id": str(fila.get("Tipo ID Jefe", "V")).strip(),
                    "telefono_jefe": str(
                        fila.get("Teléfono Jefe", "")
                    ).strip(),
                    "fecha_nacimiento_jefe": parsear_fecha(
                        fila.get("Fecha Nacimiento Jefe")
                    ),
                    "calle_id": calle_id,
                    "casa_num": str(fila.get("N° Casa", "")).strip(),
                }

                if familia:
                    # Actualizar si ya existe
                    for key, val in datos_fam.items():
                        setattr(familia, key, val)
                else:
                    # Crear nuevo registro
                    familia = Familia(cedula_jefe=cedula, **datos_fam)
                    session.add(familia)
            session.commit()

        # C. Procesar Miembros
        if "Miembros" in xls.sheet_names:
            df_miembros = pd.read_excel(xls, "Miembros", dtype=str)
            for _, fila in df_miembros.iterrows():
                cedula_jefe = str(fila.get("Cédula Jefe", "")).strip()
                cedula_m = str(fila.get("Cédula Miembro", "No posee")).strip()

                familia = (
                    session.query(Familia)
                    .filter(Familia.cedula_jefe == cedula_jefe)
                    .first()
                )
                if not familia:
                    continue  # Requiere que la familia exista

                miembro = None
                if cedula_m and cedula_m.lower() != "no posee":
                    miembro = (
                        session.query(Miembro)
                        .filter(
                            Miembro.cedula == cedula_m,
                            Miembro.familia_id == familia.id,
                        )
                        .first()
                    )

                datos_m = {
                    "nombres": str(fila.get("Nombres", "")).strip(),
                    "apellidos": str(fila.get("Apellidos", "")).strip(),
                    "tipo_id": str(fila.get("Tipo ID", "V")).strip(),
                    "cedula": cedula_m,
                    "fecha_nacimiento": parsear_fecha(
                        fila.get("Fecha Nacimiento")
                    ),
                    "parentesco": str(fila.get("Parentesco", "—")).strip(),
                    "familia_id": familia.id,
                }

                if miembro:
                    for key, val in datos_m.items():
                        setattr(miembro, key, val)
                else:
                    session.add(Miembro(**datos_m))
            session.commit()

        # D. Procesar Censo de Gas
        if "Gas Doméstico" in xls.sheet_names:
            df_gas = pd.read_excel(xls, "Gas Doméstico", dtype=str)
            for _, fila in df_gas.iterrows():
                cedula_jefe = str(fila.get("Cédula Jefe", "")).strip()
                familia = (
                    session.query(Familia)
                    .filter(Familia.cedula_jefe == cedula_jefe)
                    .first()
                )
                if not familia:
                    continue

                gas = (
                    session.query(RegistroGas)
                    .filter(RegistroGas.familia_id == familia.id)
                    .first()
                )
                kg10 = int(float(fila.get("10kg", 0) or 0))
                kg18 = int(float(fila.get("18kg", 0) or 0))
                kg27 = int(float(fila.get("27kg", 0) or 0))
                kg43 = int(float(fila.get("43kg", 0) or 0))

                if gas:
                    gas.kg10, gas.kg18, gas.kg27, gas.kg43 = (
                        kg10,
                        kg18,
                        kg27,
                        kg43,
                    )
                else:
                    session.add(
                        RegistroGas(
                            familia_id=familia.id,
                            kg10=kg10,
                            kg18=kg18,
                            kg27=kg27,
                            kg43=kg43,
                        )
                    )
            session.commit()

        return True

    except Exception as e:
        session.rollback()
        print(f"Error al importar desde Excel: {e}")
        return False
    finally:
        session.close()


# ==========================================
# 2. RESTAURAR RESPALDO JSON
# ==========================================
def importar_backup_json(ruta_json: str) -> bool:
    """Restaura todos los datos almacenados en un archivo JSON."""
    session = SessionLocal()
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        # A. Restaurar Calles
        mapa_calles = {}  # Mapea ID antiguo en JSON -> Objeto Calle en BD
        for c in data.get("calles", []):
            calle = (
                session.query(Calle)
                .filter(
                    Calle.nombre == c.get("nombre"),
                    Calle.sector == c.get("sector"),
                )
                .first()
            )
            if not calle:
                calle = Calle(
                    sector=c.get("sector", "General"),
                    nombre=c.get("nombre", ""),
                    numero=c.get("numero", ""),
                )
                session.add(calle)
                session.flush()
            mapa_calles[c.get("id")] = calle.id
        session.commit()

        # B. Restaurar Familias y Miembros
        mapa_familias = {}  # Mapea ID antiguo en JSON -> Objeto Familia en BD
        for f_data in data.get("familias", []):
            cedula_jefe = str(f_data.get("cedula_jefe", "")).strip()
            if not cedula_jefe:
                continue

            fam = (
                session.query(Familia)
                .filter(Familia.cedula_jefe == cedula_jefe)
                .first()
            )
            fn_jefe = parsear_fecha(f_data.get("fecha_nacimiento_jefe"))

            # Resolver calle_id
            json_calle_id = f_data.get("calle_id")
            calle_id = mapa_calles.get(
                json_calle_id,
                (
                    session.query(Calle).first().id
                    if session.query(Calle).first()
                    else None
                ),
            )

            datos_fam = {
                "nombres_jefe": f_data.get("nombres_jefe", ""),
                "apellidos_jefe": f_data.get("apellidos_jefe", ""),
                "tipo_id": f_data.get("tipo_id", "V"),
                "telefono_jefe": f_data.get("telefono_jefe", ""),
                "fecha_nacimiento_jefe": fn_jefe,
                "calle_id": calle_id,
                "casa_num": f_data.get("casa_num", ""),
            }

            if not fam:
                fam = Familia(cedula_jefe=cedula_jefe, **datos_fam)
                session.add(fam)
            else:
                for key, val in datos_fam.items():
                    setattr(fam, key, val)

            session.flush()
            mapa_familias[f_data.get("id")] = fam.id

            # Restaurar Miembros de esta Familia
            for m_data in f_data.get("miembros", []):
                fn_m = parsear_fecha(m_data.get("fecha_nacimiento"))
                cedula_m = str(m_data.get("cedula", "No posee")).strip()

                m_existente = None
                if cedula_m and cedula_m.lower() != "no posee":
                    m_existente = (
                        session.query(Miembro)
                        .filter(
                            Miembro.cedula == cedula_m,
                            Miembro.familia_id == fam.id,
                        )
                        .first()
                    )

                datos_m = {
                    "nombres": m_data.get("nombres", ""),
                    "apellidos": m_data.get("apellidos", ""),
                    "tipo_id": m_data.get("tipo_id", "V"),
                    "cedula": cedula_m,
                    "fecha_nacimiento": fn_m,
                    "parentesco": m_data.get("parentesco", "—"),
                    "familia_id": fam.id,
                }

                if m_existente:
                    for key, val in datos_m.items():
                        setattr(m_existente, key, val)
                else:
                    session.add(Miembro(**datos_m))

        session.commit()

        # C. Restaurar Censo de Gas
        for g in data.get("registros_gas", []):
            json_fam_id = g.get("familia_id")
            bd_fam_id = mapa_familias.get(json_fam_id)

            if not bd_fam_id:
                continue

            reg = (
                session.query(RegistroGas)
                .filter(RegistroGas.familia_id == bd_fam_id)
                .first()
            )
            if reg:
                reg.kg10 = g.get("kg10", 0)
                reg.kg18 = g.get("kg18", 0)
                reg.kg27 = g.get("kg27", 0)
                reg.kg43 = g.get("kg43", 0)
            else:
                session.add(
                    RegistroGas(
                        familia_id=bd_fam_id,
                        kg10=g.get("kg10", 0),
                        kg18=g.get("kg18", 0),
                        kg27=g.get("kg27", 0),
                        kg43=g.get("kg43", 0),
                    )
                )

        session.commit()
        return True

    except Exception as e:
        session.rollback()
        print(f"Error al importar JSON: {e}")
        return False
    finally:
        session.close()