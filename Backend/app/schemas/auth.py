from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def validar_longitud_bcrypt(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes")
        return password


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nombre: str
    rol: str
