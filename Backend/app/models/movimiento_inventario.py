"""
models/movimiento_inventario.py
---------------------------------
Refleja la tabla "movimientos_inventario" (historial de entradas
y salidas de mercancía). Se usa para RF-03.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from app.database import Base


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    tipo = Column(String, nullable=False)  # 'entrada' o 'salida'
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String)
    fecha = Column(TIMESTAMP, server_default=func.now())
