from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, LoginResponse
from app.auth.security import crear_token, usuario_actual, verificar_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.correo == datos.correo).first()

    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta está desactivada",
        )

    token = crear_token({"sub": str(usuario.id), "rol": usuario.rol})

    return LoginResponse(
        access_token=token,
        nombre=usuario.nombre,
        rol=usuario.rol,
    )


@router.get("/me")
def perfil_actual(usuario: Usuario = Depends(usuario_actual)):
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "activo": usuario.activo,
    }
