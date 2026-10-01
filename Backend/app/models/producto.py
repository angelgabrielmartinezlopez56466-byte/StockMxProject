from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, TIMESTAMP, func
from app.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    codigo = Column(String, unique=True, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    costo = Column(Numeric(10, 2), nullable=False, default=0)
    categoria = Column(String)
    stock_minimo = Column(Integer, nullable=False, default=0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"))
    activo = Column(Boolean, default=True, nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())
