from sqlalchemy import Column, Integer, Numeric, ForeignKey, TIMESTAMP, func
from app.database import Base


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(TIMESTAMP, server_default=func.now())
    total = Column(Numeric(10, 2), nullable=False, default=0)
