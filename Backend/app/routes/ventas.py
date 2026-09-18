from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.security import usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.detalle_venta import DetalleVenta
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.schemas.ventas import (
    DetalleVentaRespuesta,
    VentaCrear,
    VentaRespuesta,
)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def _respuesta(venta: Venta, detalles: list[DetalleVenta]) -> VentaRespuesta:
    return VentaRespuesta(
        id=venta.id,
        usuario_id=venta.usuario_id,
        fecha=venta.fecha,
        total=venta.total,
        detalles=[
            DetalleVentaRespuesta(
                producto_id=detalle.producto_id,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal,
            )
            for detalle in detalles
        ],
    )


@router.post("", response_model=VentaRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_venta(
    datos: VentaCrear,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    cantidades: dict[int, int] = defaultdict(int)
    for detalle in datos.detalles:
        cantidades[detalle.producto_id] += detalle.cantidad

    productos = {}
    inventarios = {}
    for producto_id, cantidad in cantidades.items():
        producto = db.get(Producto, producto_id)
        if not producto or not producto.activo:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado o inactivo")
        inventario = db.query(Inventario).filter(
            Inventario.producto_id == producto_id
        ).with_for_update().first()
        if not inventario or inventario.existencia_actual < cantidad:
            raise HTTPException(
                status_code=409,
                detail=f"Stock insuficiente para el producto {producto.nombre}",
            )
        productos[producto_id] = producto
        inventarios[producto_id] = inventario

    total = Decimal("0.00")
    venta = Venta(usuario_id=usuario.id, total=0)
    detalles_creados = []
    try:
        db.add(venta)
        db.flush()
        for producto_id, cantidad in cantidades.items():
            producto = productos[producto_id]
            subtotal = producto.precio * cantidad
            total += subtotal
            inventarios[producto_id].existencia_actual -= cantidad
            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto_id,
                cantidad=cantidad,
                precio_unitario=producto.precio,
                subtotal=subtotal,
            )
            db.add(detalle)
            detalles_creados.append(detalle)
            db.add(MovimientoInventario(
                producto_id=producto_id,
                usuario_id=usuario.id,
                tipo="salida",
                cantidad=cantidad,
                motivo=f"Venta #{venta.id}",
            ))
        venta.total = total
        db.commit()
        registrar_auditoria("venta.crear", usuario.id, venta_id=venta.id, total=total)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la venta",
        )
    db.refresh(venta)
    for detalle in detalles_creados:
        db.refresh(detalle)
    return _respuesta(venta, detalles_creados)


@router.get("", response_model=list[VentaRespuesta])
def listar_ventas(
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    ventas = db.query(Venta).order_by(Venta.fecha.desc()).limit(limite).all()
    if not ventas:
        return []
    venta_ids = [venta.id for venta in ventas]
    detalles_por_venta = {venta_id: [] for venta_id in venta_ids}
    detalles = db.query(DetalleVenta).filter(
        DetalleVenta.venta_id.in_(venta_ids)
    ).all()
    for detalle in detalles:
        detalles_por_venta[detalle.venta_id].append(detalle)
    return [
        _respuesta(venta, detalles_por_venta[venta.id])
        for venta in ventas
    ]


@router.get("/{venta_id}", response_model=VentaRespuesta)
def obtener_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    venta = db.get(Venta, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    detalles = db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta_id).all()
    return _respuesta(venta, detalles)
