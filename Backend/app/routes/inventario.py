from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.security import administrador_actual, usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.inventario import (
    ExistenciaRespuesta,
    MovimientoCrear,
    MovimientoRespuesta,
)

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("", response_model=list[ExistenciaRespuesta])
def listar_existencias(
    solo_stock_bajo: bool = Query(False),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    filas = db.query(Producto, Inventario).join(
        Inventario, Inventario.producto_id == Producto.id
    ).filter(Producto.activo.is_(True)).order_by(Producto.nombre).all()
    resultado = []
    for producto, inventario in filas:
        stock_bajo = inventario.existencia_actual <= producto.stock_minimo
        if not solo_stock_bajo or stock_bajo:
            resultado.append(ExistenciaRespuesta(
                producto_id=producto.id,
                codigo=producto.codigo,
                nombre=producto.nombre,
                existencia_actual=inventario.existencia_actual,
                stock_minimo=producto.stock_minimo,
                stock_bajo=stock_bajo,
            ))
    return resultado


def _registrar_movimiento(
    datos: MovimientoCrear,
    tipo: str,
    usuario: Usuario,
    db: Session,
) -> MovimientoInventario:
    inventario = db.query(Inventario).filter(
        Inventario.producto_id == datos.producto_id
    ).with_for_update().first()
    producto = db.get(Producto, datos.producto_id)
    if not producto or not producto.activo:
        raise HTTPException(status_code=404, detail="Producto no encontrado o inactivo")
    if not inventario:
        raise HTTPException(status_code=409, detail="El producto no tiene inventario")
    nueva_existencia = (
        inventario.existencia_actual + datos.cantidad
        if tipo == "entrada"
        else inventario.existencia_actual - datos.cantidad
    )
    if nueva_existencia < 0:
        raise HTTPException(status_code=409, detail="No hay stock suficiente")
    inventario.existencia_actual = nueva_existencia
    movimiento = MovimientoInventario(
        producto_id=datos.producto_id,
        usuario_id=usuario.id,
        tipo=tipo,
        cantidad=datos.cantidad,
        motivo=datos.motivo,
    )
    try:
        db.add(movimiento)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo registrar el movimiento")
    db.refresh(movimiento)
    registrar_auditoria(
        f"inventario.{tipo}", usuario.id,
        producto_id=datos.producto_id, cantidad=datos.cantidad,
    )
    return movimiento


@router.post("/entradas", response_model=MovimientoRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_entrada(
    datos: MovimientoCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(administrador_actual),
):
    return _registrar_movimiento(datos, "entrada", usuario, db)


@router.post("/salidas", response_model=MovimientoRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_salida(
    datos: MovimientoCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(administrador_actual),
):
    return _registrar_movimiento(datos, "salida", usuario, db)


@router.get("/movimientos", response_model=list[MovimientoRespuesta])
def listar_movimientos(
    producto_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    consulta = db.query(MovimientoInventario)
    if producto_id:
        consulta = consulta.filter(MovimientoInventario.producto_id == producto_id)
    return consulta.order_by(MovimientoInventario.fecha.desc()).all()
