from fastapi import APIRouter, Depends
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.security import usuario_actual
from app.database import get_db
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.usuario import Usuario

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    total_productos = db.query(func.count(Producto.id)).filter(Producto.activo.is_(True)).scalar() or 0
    stock_bajo = db.query(func.count(Producto.id)).join(
        Inventario, Inventario.producto_id == Producto.id
    ).filter(
        Producto.activo.is_(True),
        Inventario.existencia_actual <= Producto.stock_minimo,
    ).scalar() or 0
    ventas = db.query(Venta).order_by(Venta.fecha.desc()).all()
    ventas_total = sum((venta.total for venta in ventas), Decimal("0.00"))
    unidades_vendidas = db.query(func.coalesce(func.sum(DetalleVenta.cantidad), 0)).scalar() or 0
    mas_vendidos = db.query(
        Producto.nombre,
        func.sum(DetalleVenta.cantidad).label("unidades"),
    ).join(DetalleVenta, DetalleVenta.producto_id == Producto.id).group_by(
        Producto.id, Producto.nombre
    ).order_by(func.sum(DetalleVenta.cantidad).desc()).limit(3).all()
    return {
        "total_productos": total_productos,
        "productos_stock_bajo": stock_bajo,
        "ventas_acumuladas": len(ventas),
        "ventas_brutas": ventas_total,
        "unidades_vendidas": unidades_vendidas,
        "productos_mas_vendidos": [
            {"nombre": nombre, "unidades": unidades}
            for nombre, unidades in mas_vendidos
        ],
        "ventas_recientes": [
            {
                "id": venta.id,
                "fecha": venta.fecha,
                "total": venta.total,
                "usuario_id": venta.usuario_id,
            }
            for venta in ventas[:5]
        ],
    }
