"""
models/detalle_venta.py
-------------------------
Refleja la tabla "detalle_ventas" (qué productos y cuántos se
vendieron en cada venta).
"""

from sqlalchemy import Column, Integer, Numeric, ForeignKey
from app.database import Base


class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
