from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    correo: EmailStr
    password: str = Field(min_length=6, max_length=72)
    rol: str = "empleado"

    @field_validator("nombre", "rol", mode="before")
    @classmethod
    def limpiar_campos(cls, valor):
        return str(valor).strip()

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, valor):
        if valor not in {"administrador", "empleado"}:
            raise ValueError("El rol debe ser administrador o empleado")
        return valor


class UsuarioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    correo: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=72)
    rol: str | None = None
    activo: bool | None = None

    @field_validator("nombre", "rol", mode="before")
    @classmethod
    def limpiar_campos(cls, valor):
        return None if valor is None else str(valor).strip()


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    correo: EmailStr
    rol: str
    activo: bool
    fecha_creacion: datetime | None
