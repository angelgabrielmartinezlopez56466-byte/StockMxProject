from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import administrador_actual, hashear_password, usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuarios import UsuarioActualizar, UsuarioCrear, UsuarioRespuesta

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _validar_rol(rol: str | None) -> None:
    if rol is not None and rol not in {"administrador", "empleado"}:
        raise HTTPException(status_code=422, detail="El rol debe ser administrador o empleado")


@router.get("/me", response_model=UsuarioRespuesta)
def perfil_actual(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.get("", response_model=list[UsuarioRespuesta])
def listar_usuarios(
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(administrador_actual),
):
    return db.query(Usuario).order_by(Usuario.nombre).all()


@router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    _: Usuario = Depends(administrador_actual),
):
    _validar_rol(datos.rol)
    if db.query(Usuario).filter(Usuario.correo == datos.correo).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
        activo=True,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    db.refresh(usuario)
    registrar_auditoria("usuario.crear", administrador.id, usuario_objetivo_id=usuario.id)
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioRespuesta)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizar,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(administrador_actual),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    cambios = datos.model_dump(exclude_unset=True)
    _validar_rol(cambios.get("rol"))
    if "correo" in cambios and db.query(Usuario).filter(
        Usuario.correo == cambios["correo"], Usuario.id != usuario_id
    ).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    password = cambios.pop("password", None)
    if password is not None:
        usuario.password_hash = hashear_password(password)
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    registrar_auditoria("usuario.actualizar", administrador.id, usuario_objetivo_id=usuario.id)
    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(administrador_actual),
):
    if usuario_id == administrador.id:
        raise HTTPException(status_code=409, detail="No puedes eliminar tu propia cuenta")
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.rol == "administrador":
        admin_restantes = db.query(Usuario).filter(
            Usuario.rol == "administrador",
            Usuario.id != usuario_id,
        ).count()
        if admin_restantes == 0:
            raise HTTPException(
                status_code=409,
                detail="Debe quedar al menos un administrador activo en el sistema",
            )

    db.delete(usuario)
    db.commit()
    registrar_auditoria("usuario.eliminar", administrador.id, usuario_objetivo_id=usuario_id)
