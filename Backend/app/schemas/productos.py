from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductoBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    codigo: str = Field(min_length=1, max_length=80)
    precio: Decimal = Field(ge=0, decimal_places=2)
    costo: Decimal = Field(default=0, ge=0, decimal_places=2)
    categoria: str | None = None
    stock_minimo: int = Field(default=0, ge=0)
    proveedor_id: int | None = Field(default=None, gt=0)

    @field_validator("nombre", "codigo", "categoria", mode="before")
    @classmethod
    def limpiar_texto(cls, valor):
        if valor is None:
            return valor
        valor = str(valor).strip()
        if not valor:
            raise ValueError("El texto no puede estar vacío")
        return valor


class ProductoCrear(ProductoBase):
    existencia_inicial: int = Field(default=0, ge=0)


class ProductoActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    codigo: str | None = Field(default=None, min_length=1, max_length=80)
    precio: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    costo: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    categoria: str | None = None
    stock_minimo: int | None = Field(default=None, ge=0)
    proveedor_id: int | None = Field(default=None, gt=0)
    activo: bool | None = None


class ProductoRespuesta(ProductoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    existencia_actual: int = 0
