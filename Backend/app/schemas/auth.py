"""
schemas/auth.py
-----------------
Define qué forma deben tener los datos que entran y salen en el
login. FastAPI usa esto para validar automáticamente (si falta un
campo o está mal escrito, rechaza la petición antes de que llegue
a nuestro código).
"""

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Lo que el frontend manda al intentar iniciar sesión."""
    correo: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def validar_longitud_bcrypt(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes")
        return password


class LoginResponse(BaseModel):
    """Lo que la API regresa si el login es correcto."""
    access_token: str
    token_type: str = "bearer"
    nombre: str
    rol: str
