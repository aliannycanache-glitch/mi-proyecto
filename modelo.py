from datetime import date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

# ==========================
# Modelo de Calles / Sectores
# ==========================
class Calle(Base):
    __tablename__ = "calles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector = Column(String(100), nullable=False)
    nombre = Column(String(100), nullable=False)
    numero = Column(String(20), nullable=True)

    # Relación 1:N con Familias
    familias = relationship("Familia", back_populates="calle")


# ==========================
# Modelo de Usuarios
# ==========================
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)
    apellido = Column(String(50), nullable=False)
    tipo_id = Column(String(2), nullable=False, default="V")  # V, E, J, P
    cedula = Column(String(15), unique=True, nullable=False)
    correo = Column(String(100), unique=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    rol = Column(String(50), nullable=False)  # Ej: "Líder Político", "Encargado de Gas"
    sexo = Column(String(20), nullable=False, default="No especificado")
    fecha_nacimiento = Column(Date, nullable=True)
    
    # Credenciales de Seguridad y Recuperación
    clave_hash = Column(String(255), nullable=False)  # Hashing recomendado (bcrypt)
    pregunta1 = Column(String(150), nullable=True)
    respuesta1 = Column(String(255), nullable=True)
    pregunta2 = Column(String(150), nullable=True)
    respuesta2 = Column(String(255), nullable=True)
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    bloqueado = Column(Integer, nullable=False, default=0)

    # Propiedad calculada dinámicamente (no se guarda en la BD)
    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None


# ==========================
# Modelo de Familias
# ==========================
class Familia(Base):
    __tablename__ = "familias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombres_jefe = Column(String(60), nullable=False)
    apellidos_jefe = Column(String(60), nullable=False)
    tipo_id = Column(String(2), nullable=False, default="V")
    cedula_jefe = Column(String(15), unique=True, nullable=False)
    telefono_jefe = Column(String(20), nullable=True)
    fecha_nacimiento_jefe = Column(Date, nullable=False)
    es_beneficiario = Column(String(10), nullable=False, default="No")
    bono = Column(String(500), nullable=False, default="Ninguno")
    
    # Clave Foránea referenciando a la Calle (3FN)
    calle_id = Column(Integer, ForeignKey("calles.id", ondelete="RESTRICT"), nullable=False)
    casa_num = Column(String(20), nullable=True)  # Número o identificador de casa

    # Relaciones
    calle = relationship("Calle", back_populates="familias")
    miembros = relationship("Miembro", back_populates="familia", cascade="all, delete-orphan")
    registros_gas = relationship("RegistroGas", back_populates="familia", cascade="all, delete-orphan")

    @property
    def edad_jefe(self):
        if self.fecha_nacimiento_jefe:
            today = date.today()
            return today.year - self.fecha_nacimiento_jefe.year - (
                (today.month, today.day) < (self.fecha_nacimiento_jefe.month, self.fecha_nacimiento_jefe.day)
            )
        return None


# ==========================
# Modelo de Miembros de Familia
# ==========================
class Miembro(Base):
    __tablename__ = "miembros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(60), nullable=False)
    apellidos = Column(String(60), nullable=False)
    tipo_id = Column(String(2), nullable=False, default="V")
    cedula = Column(String(15), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    parentesco = Column(String(30), nullable=False)  # Ej: Hijo, Esposa, Abuelo
    es_beneficiario = Column(String(10), nullable=False, default="No")
    bonos = Column(String(500), nullable=False, default="Ninguno")

    # Relación 1:N con Familias
    familia_id = Column(Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False)
    familia = relationship("Familia", back_populates="miembros")

    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None


# ==========================
# Modelo de Registros de Gas
# ==========================
class RegistroGas(Base):
    __tablename__ = "registros_gas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Clave Foránea en lugar de repetir datos del jefe de familia (3FN)
    familia_id = Column(Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False)
    
    # Conteo de cilindros por peso
    kg10 = Column(Integer, default=0, nullable=False)
    kg18 = Column(Integer, default=0, nullable=False)
    kg27 = Column(Integer, default=0, nullable=False)
    kg43 = Column(Integer, default=0, nullable=False)

    # Relación con la Familia
    familia = relationship("Familia", back_populates="registros_gas")


# ==========================
# Modelo de Atención al Adulto Mayor
# ==========================
class AdultoMayor(Base):
    __tablename__ = "adultos_mayores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(60), nullable=False)
    apellidos = Column(String(60), nullable=False)
    tipo_id = Column(String(2), nullable=False, default="V")
    cedula = Column(String(15), unique=True, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    telefono = Column(String(20), nullable=True)
    direccion = Column(String(250), nullable=False)
    condicion_salud = Column(String(150), nullable=True)
    servicio = Column(String(150), nullable=False, default="Atención gerontológica")
    observaciones = Column(String(500), nullable=True)
    es_adulto_mayor = Column(String(20), nullable=False, default="No")
    aplica_bolsa = Column(String(20), nullable=False, default="No")
    categoria = Column(String(50), nullable=False, default="No aplica")

    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None

    def actualizar_evaluacion(self):
        edad_actual = self.edad
        if edad_actual is None:
            self.es_adulto_mayor = "No"
            self.aplica_bolsa = "No"
            self.categoria = "Sin edad"
            return

        if edad_actual >= 60:
            self.es_adulto_mayor = "Si"
            self.aplica_bolsa = "Si"
            self.categoria = "Bolsa Adulto Mayor"
        elif edad_actual >= 50:
            self.es_adulto_mayor = "Si"
            self.aplica_bolsa = "No"
            self.categoria = "Adulto Mayor sin bolsa"
        else:
            self.es_adulto_mayor = "No"
            self.aplica_bolsa = "No"
            self.categoria = "No aplica"


# ==========================
# Modelo de Protección Integral
# ==========================
class ProteccionIntegral(Base):
    __tablename__ = "proteccion_integral"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(60), nullable=False)
    apellidos = Column(String(60), nullable=False)
    tipo_id = Column(String(2), nullable=False, default="V")
    cedula = Column(String(15), unique=True, nullable=False)
    telefono = Column(String(20), nullable=True)
    direccion = Column(String(250), nullable=False)
    tipo_caso = Column(String(100), nullable=False)
    descripcion = Column(String(500), nullable=False)
    estado = Column(String(60), nullable=False, default="Abierto")
    fecha_registro = Column(Date, nullable=False, default=date.today)
    atendido_por = Column(String(100), nullable=True)


# ==========================
# Inicializar Base de Datos
# ==========================
engine = create_engine("sqlite:///datos.db", echo=False)
Base.metadata.create_all(engine)

try:
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(adultos_mayores)").fetchall()
        existing = {col[1] for col in cols}
        if "es_adulto_mayor" not in existing:
            conn.exec_driver_sql("ALTER TABLE adultos_mayores ADD COLUMN es_adulto_mayor VARCHAR(20) DEFAULT 'No'")
        if "aplica_bolsa" not in existing:
            conn.exec_driver_sql("ALTER TABLE adultos_mayores ADD COLUMN aplica_bolsa VARCHAR(20) DEFAULT 'No'")
        if "categoria" not in existing:
            conn.exec_driver_sql("ALTER TABLE adultos_mayores ADD COLUMN categoria VARCHAR(50) DEFAULT 'No aplica'")
        usuario_cols = {col[1] for col in conn.exec_driver_sql("PRAGMA table_info(usuarios)").fetchall()}
        if "sexo" not in usuario_cols:
            conn.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN sexo VARCHAR(20) DEFAULT 'No especificado'")
        if "intentos_fallidos" not in usuario_cols:
            conn.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN intentos_fallidos INTEGER DEFAULT 0")
        if "bloqueado" not in usuario_cols:
            conn.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN bloqueado INTEGER DEFAULT 0")
        miembro_cols = {col[1] for col in conn.exec_driver_sql("PRAGMA table_info(miembros)").fetchall()}
        if "es_beneficiario" not in miembro_cols:
            conn.exec_driver_sql("ALTER TABLE miembros ADD COLUMN es_beneficiario VARCHAR(10) DEFAULT 'No'")
        if "bonos" not in miembro_cols:
            conn.exec_driver_sql("ALTER TABLE miembros ADD COLUMN bonos VARCHAR(500) DEFAULT 'Ninguno'")
        familia_cols = {
            col[1]
            for col in conn.exec_driver_sql("PRAGMA table_info(familias)").fetchall()
        }
        if "es_beneficiario" not in familia_cols:
            conn.exec_driver_sql("ALTER TABLE familias ADD COLUMN es_beneficiario VARCHAR(10) DEFAULT 'No'")
        if "bono" not in familia_cols:
            conn.exec_driver_sql("ALTER TABLE familias ADD COLUMN bono VARCHAR(100) DEFAULT 'Ninguno'")
except Exception:
    pass

SessionLocal = sessionmaker(bind=engine)