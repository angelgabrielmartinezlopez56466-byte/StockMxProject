from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.security import administrador_actual, usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.detalle_venta import DetalleVenta
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.venta import Venta
from app.models.usuario import Usuario
from app.models.reporte import Reporte

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _rango(desde: date | None, hasta: date | None) -> tuple[datetime, datetime]:
    fecha_hasta = hasta or date.today()
    fecha_desde = desde or (fecha_hasta - timedelta(days=30))
    if fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=400,
            detail="La fecha inicial no puede ser posterior a la fecha final",
        )
    return datetime.combine(fecha_desde, time.min), datetime.combine(fecha_hasta + timedelta(days=1), time.min)


def _historial(desde: date | None, hasta: date | None, total: Decimal, usuario: Usuario, db: Session):
    fecha_hasta = hasta or date.today()
    fecha_desde = desde or (fecha_hasta - timedelta(days=30))
    registro = Reporte(
        usuario_id=usuario.id,
        tipo="ventas",
        rango_fechas=f"{fecha_desde.isoformat()} a {fecha_hasta.isoformat()}",
        total_ventas=total,
    )
    try:
        db.add(registro)
        db.commit()
        db.refresh(registro)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar el historial del reporte")
    return registro


@router.post("/ventas/generar", status_code=status.HTTP_201_CREATED)
def guardar_reporte_ventas(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(administrador_actual),
):
    inicio, fin = _rango(desde, hasta)
    total = sum(
        (venta.total for venta in db.query(Venta).filter(Venta.fecha >= inicio, Venta.fecha < fin).all()),
        Decimal("0.00"),
    )
    registro = _historial(desde, hasta, total, usuario, db)
    registrar_auditoria("reporte.ventas.generar", usuario.id, reporte_id=registro.id)
    return {
        "id": registro.id,
        "tipo": registro.tipo,
        "rango_fechas": registro.rango_fechas,
        "total_ventas": registro.total_ventas,
        "fecha_generacion": registro.fecha_generacion,
    }


@router.get("/historial")
def historial_reportes(
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(administrador_actual),
):
    registros = db.query(Reporte).order_by(Reporte.fecha_generacion.desc()).limit(limite).all()
    return [
        {
            "id": registro.id,
            "tipo": registro.tipo,
            "rango_fechas": registro.rango_fechas,
            "total_ventas": registro.total_ventas,
            "ganancia_estimada": registro.ganancia_estimada,
            "fecha_generacion": registro.fecha_generacion,
        }
        for registro in registros
    ]


@router.get("/ventas")
def reporte_ventas(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    inicio, fin = _rango(desde, hasta)
    ventas = db.query(Venta).filter(Venta.fecha >= inicio, Venta.fecha < fin).all()
    total = sum((venta.total for venta in ventas), Decimal("0.00"))
    return {
        "desde": inicio.date(),
        "hasta": (fin - timedelta(days=1)).date(),
        "cantidad_ventas": len(ventas),
        "total_ventas": total,
    }


@router.get("/productos-mas-vendidos")
def productos_mas_vendidos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    inicio, fin = _rango(desde, hasta)
    filas = db.query(
        Producto.id,
        Producto.nombre,
        Producto.codigo,
        func.sum(DetalleVenta.cantidad).label("unidades_vendidas"),
        func.sum(DetalleVenta.subtotal).label("ingresos"),
    ).join(DetalleVenta, DetalleVenta.producto_id == Producto.id).join(
        Venta, Venta.id == DetalleVenta.venta_id
    ).filter(Venta.fecha >= inicio, Venta.fecha < fin).group_by(
        Producto.id, Producto.nombre, Producto.codigo
    ).order_by(func.sum(DetalleVenta.cantidad).desc()).limit(limite).all()
    return [
        {
            "producto_id": fila.id,
            "nombre": fila.nombre,
            "codigo": fila.codigo,
            "unidades_vendidas": fila.unidades_vendidas,
            "ingresos": fila.ingresos,
        }
        for fila in filas
    ]


@router.get("/productos-menos-vendidos")
def productos_menos_vendidos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    inicio, fin = _rango(desde, hasta)
    ventas_periodo = db.query(
        DetalleVenta.producto_id,
        func.coalesce(func.sum(DetalleVenta.cantidad), 0).label("unidades_vendidas"),
    ).join(Venta, Venta.id == DetalleVenta.venta_id).filter(
        Venta.fecha >= inicio, Venta.fecha < fin
    ).group_by(DetalleVenta.producto_id).subquery()
    filas = db.query(
        Producto.id,
        Producto.nombre,
        Producto.codigo,
        func.coalesce(ventas_periodo.c.unidades_vendidas, 0).label("unidades_vendidas"),
    ).outerjoin(ventas_periodo, ventas_periodo.c.producto_id == Producto.id).filter(
        Producto.activo.is_(True)
    ).order_by(
        func.coalesce(ventas_periodo.c.unidades_vendidas, 0).asc(),
        Producto.nombre.asc(),
    ).limit(limite).all()
    return [
        {
            "producto_id": fila.id,
            "nombre": fila.nombre,
            "codigo": fila.codigo,
            "unidades_vendidas": fila.unidades_vendidas,
        }
        for fila in filas
    ]


@router.get("/ventas-detalle")
def ventas_detalle(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    inicio, fin = _rango(desde, hasta)
    filas = db.query(Venta, DetalleVenta, Producto).join(
        DetalleVenta, DetalleVenta.venta_id == Venta.id
    ).join(Producto, Producto.id == DetalleVenta.producto_id).filter(
        Venta.fecha >= inicio, Venta.fecha < fin
    ).order_by(Venta.fecha.desc(), Venta.id.desc(), Producto.nombre).all()
    return [
        {
            "venta_id": venta.id,
            "fecha": venta.fecha,
            "producto": producto.nombre,
            "codigo": producto.codigo,
            "cantidad": detalle.cantidad,
            "precio_unitario": detalle.precio_unitario,
            "subtotal": detalle.subtotal,
            "total_venta": venta.total,
        }
        for venta, detalle, producto in filas
    ]


@router.get("/existencias")
def reporte_existencias(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    filas = db.query(Producto, Inventario).join(
        Inventario, Inventario.producto_id == Producto.id
    ).filter(Producto.activo.is_(True)).order_by(Producto.nombre).all()
    return [
        {
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "codigo": producto.codigo,
            "existencia_actual": inventario.existencia_actual,
            "stock_minimo": producto.stock_minimo,
            "stock_bajo": inventario.existencia_actual <= producto.stock_minimo,
        }
        for producto, inventario in filas
    ]


@router.get("/movimientos")
def reporte_movimientos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    producto_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    inicio, fin = _rango(desde, hasta)
    consulta = db.query(MovimientoInventario).filter(
        MovimientoInventario.fecha >= inicio,
        MovimientoInventario.fecha < fin,
    )
    if producto_id:
        consulta = consulta.filter(MovimientoInventario.producto_id == producto_id)
    movimientos = consulta.order_by(MovimientoInventario.fecha.desc()).all()
    return [
        {
            "id": movimiento.id,
            "producto_id": movimiento.producto_id,
            "usuario_id": movimiento.usuario_id,
            "tipo": movimiento.tipo,
            "cantidad": movimiento.cantidad,
            "motivo": movimiento.motivo,
            "fecha": movimiento.fecha,
        }
        for movimiento in movimientos
    ]
