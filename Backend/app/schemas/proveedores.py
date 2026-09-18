from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ProveedorCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    telefono: str | None = None
    correo: EmailStr | None = None

    @field_validator("nombre", "telefono", mode="before")
    @classmethod
    def limpiar_texto(cls, valor):
        return None if valor is None else str(valor).strip()


class ProveedorActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    telefono: str | None = None
    correo: EmailStr | None = None


class ProveedorRespuesta(ProveedorCrear):
    model_config = ConfigDict(from_attributes=True)

    id: int
