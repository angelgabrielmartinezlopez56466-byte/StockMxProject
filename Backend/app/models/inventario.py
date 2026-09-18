"""
models/inventario.py
----------------------
Refleja la tabla "inventario" (existencia actual de cada producto).
Se usa para RF-03 (Controlar inventario).
"""

from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, func
from app.database import Base


class Inventario(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), unique=True, nullable=False)
    existencia_actual = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
