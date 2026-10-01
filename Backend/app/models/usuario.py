from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func
from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())
