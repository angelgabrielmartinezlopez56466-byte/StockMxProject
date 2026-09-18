from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import administrador_actual, usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.proveedor import Proveedor
from app.schemas.proveedores import (
    ProveedorActualizar,
    ProveedorCrear,
    ProveedorRespuesta,
)

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("", response_model=list[ProveedorRespuesta])
def listar_proveedores(
    db: Session = Depends(get_db),
    _: object = Depends(usuario_actual),
):
    return db.query(Proveedor).order_by(Proveedor.nombre).all()


@router.post("", response_model=ProveedorRespuesta, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    datos: ProveedorCrear,
    db: Session = Depends(get_db),
    administrador = Depends(administrador_actual),
):
    proveedor = Proveedor(**datos.model_dump())
    db.add(proveedor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear el proveedor")
    db.refresh(proveedor)
    registrar_auditoria("proveedor.crear", administrador.id, proveedor_id=proveedor.id)
    return proveedor


@router.patch("/{proveedor_id}", response_model=ProveedorRespuesta)
def actualizar_proveedor(
    proveedor_id: int,
    datos: ProveedorActualizar,
    db: Session = Depends(get_db),
    administrador = Depends(administrador_actual),
):
    proveedor = db.get(Proveedor, proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(proveedor, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar el proveedor")
    db.refresh(proveedor)
    registrar_auditoria("proveedor.actualizar", administrador.id, proveedor_id=proveedor.id)
    return proveedor
