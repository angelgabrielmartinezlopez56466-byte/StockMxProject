import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.database import get_db
from app.models.usuario import Usuario

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No se encontró SECRET_KEY en el archivo .env")
ALGORITHM = "HS256"
MINUTOS_EXPIRACION_TOKEN = 60 * 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hashear_password(password_plano: str) -> str:
    return pwd_context.hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


def crear_token(datos: dict) -> str:
    datos_a_codificar = datos.copy()
    expiracion = datetime.utcnow() + timedelta(minutes=MINUTOS_EXPIRACION_TOKEN)
    datos_a_codificar.update({"exp": expiracion})
    return jwt.encode(datos_a_codificar, SECRET_KEY, algorithm=ALGORITHM)


def leer_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    datos = leer_token(token)
    if not datos or not datos.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        usuario_id = int(datos["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.get(Usuario, usuario_id)
    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autorizado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def administrador_actual(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if usuario.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere el rol de administrador",
        )
    return usuario
