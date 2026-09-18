"""
models/reporte.py
-------------------
Refleja la tabla "reportes". Se usa para RF-06 (Consultar reportes).
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP, func
from app.database import Base


class Reporte(Base):
    __tablename__ = "reportes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    tipo = Column(String, nullable=False)  # 'ventas', 'inventario', 'productos_top'
    rango_fechas = Column(String)
    total_ventas = Column(Numeric(10, 2))
    ganancia_estimada = Column(Numeric(10, 2))
    fecha_generacion = Column(TIMESTAMP, server_default=func.now())
