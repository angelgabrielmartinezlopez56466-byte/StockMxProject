from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import administrador_actual, usuario_actual
from app.audit import registrar_auditoria
from app.database import get_db
from app.models.inventario import Inventario
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.schemas.productos import ProductoActualizar, ProductoCrear, ProductoRespuesta

router = APIRouter(prefix="/productos", tags=["Productos"])


def _respuesta(producto: Producto, existencia: int = 0) -> ProductoRespuesta:
    return ProductoRespuesta(
        id=producto.id,
        nombre=producto.nombre,
        codigo=producto.codigo,
        precio=producto.precio,
        costo=producto.costo,
        categoria=producto.categoria,
        stock_minimo=producto.stock_minimo,
        proveedor_id=producto.proveedor_id,
        activo=producto.activo,
        existencia_actual=existencia,
    )


@router.get("", response_model=list[ProductoRespuesta])
def listar_productos(
    incluir_inactivos: bool = Query(False),
    busqueda: str | None = Query(None, min_length=1),
    db: Session = Depends(get_db),
    _: object = Depends(usuario_actual),
):
    consulta = db.query(Producto)
    if not incluir_inactivos:
        consulta = consulta.filter(Producto.activo.is_(True))
    if busqueda:
        termino = f"%{busqueda}%"
        consulta = consulta.filter(
            (Producto.nombre.ilike(termino)) | (Producto.codigo.ilike(termino))
        )
    productos = consulta.order_by(Producto.nombre).all()
    existencias = {
        existencia.producto_id: existencia.existencia_actual
        for existencia in db.query(Inventario).filter(
            Inventario.producto_id.in_([producto.id for producto in productos])
        ).all()
    } if productos else {}
    return [_respuesta(producto, existencias.get(producto.id, 0)) for producto in productos]


@router.get("/{producto_id}", response_model=ProductoRespuesta)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(usuario_actual),
):
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    existencia = db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
    return _respuesta(producto, existencia.existencia_actual if existencia else 0)


@router.post("", response_model=ProductoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    administrador = Depends(administrador_actual),
):
    if db.query(Producto).filter(Producto.codigo == datos.codigo).first():
        raise HTTPException(status_code=409, detail="El código del producto ya existe")
    if datos.proveedor_id and not db.get(Proveedor, datos.proveedor_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    producto = Producto(
        nombre=datos.nombre,
        codigo=datos.codigo,
        precio=datos.precio,
        costo=datos.costo,
        categoria=datos.categoria,
        stock_minimo=datos.stock_minimo,
        proveedor_id=datos.proveedor_id,
    )
    try:
        db.add(producto)
        db.flush()
        db.add(Inventario(producto_id=producto.id, existencia_actual=datos.existencia_inicial))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear el producto")
    db.refresh(producto)
    registrar_auditoria("producto.crear", administrador.id, producto_id=producto.id)
    return _respuesta(producto, datos.existencia_inicial)


@router.patch("/{producto_id}", response_model=ProductoRespuesta)
def actualizar_producto(
    producto_id: int,
    datos: ProductoActualizar,
    db: Session = Depends(get_db),
    administrador = Depends(administrador_actual),
):
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    cambios = datos.model_dump(exclude_unset=True)
    if "codigo" in cambios and db.query(Producto).filter(
        Producto.codigo == cambios["codigo"], Producto.id != producto_id
    ).first():
        raise HTTPException(status_code=409, detail="El código del producto ya existe")
    if cambios.get("proveedor_id") and not db.get(Proveedor, cambios["proveedor_id"]):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar el producto")
    db.refresh(producto)
    registrar_auditoria("producto.actualizar", administrador.id, producto_id=producto.id)
    existencia = db.query(Inventario).filter(Inventario.producto_id == producto_id).first()
    return _respuesta(producto, existencia.existencia_actual if existencia else 0)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    administrador = Depends(administrador_actual),
):
    producto = db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.activo = False
    db.commit()
    registrar_auditoria("producto.desactivar", administrador.id, producto_id=producto.id)
