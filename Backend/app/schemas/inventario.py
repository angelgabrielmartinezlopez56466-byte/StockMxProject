from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovimientoCrear(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    motivo: str | None = Field(default=None, max_length=250)


class MovimientoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    usuario_id: int | None
    tipo: str
    cantidad: int
    motivo: str | None
    fecha: datetime | None


class ExistenciaRespuesta(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    existencia_actual: int
    stock_minimo: int
    stock_bajo: bool
