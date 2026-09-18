from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class DetalleVentaCrear(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class VentaCrear(BaseModel):
    detalles: list[DetalleVentaCrear] = Field(min_length=1)

    @field_validator("detalles")
    @classmethod
    def validar_detalles(cls, detalles):
        if len({detalle.producto_id for detalle in detalles}) != len(detalles):
            raise ValueError("No se puede repetir un producto en la venta")
        return detalles


class DetalleVentaRespuesta(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaRespuesta(BaseModel):
    id: int
    usuario_id: int
    fecha: datetime | None
    total: Decimal
    detalles: list[DetalleVentaRespuesta]
