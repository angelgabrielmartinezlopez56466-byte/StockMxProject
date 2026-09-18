-- ==================================================================
-- STOCK MX · Schema de base de datos (PostgreSQL)
-- ==================================================================
-- Este archivo crea las 8 tablas del sistema, basadas en el
-- documento de análisis (Capítulo 1: requisitos funcionales RF-01
-- a RF-07, y Capítulo 2: diagrama de clases y diagrama E-R).
--
-- Cómo correrlo:
--   psql -U <usuario> -d stockmx -f schema.sql
--
-- Convención de nombres usada en todo el proyecto:
--   - snake_case en minúsculas para tablas y columnas (nombre_asi)
--   - cada tabla tiene una columna "id" como llave primaria
--   - las llaves foráneas se llaman "<tabla_relacionada>_id"
-- ==================================================================

-- Se borran en orden inverso a como se crean (una tabla no se
-- puede borrar si otra depende de ella), para poder re-ejecutar
-- este archivo las veces que haga falta sin dar error.
DROP TABLE IF EXISTS reportes;
DROP TABLE IF EXISTS detalle_ventas;
DROP TABLE IF EXISTS ventas;
DROP TABLE IF EXISTS movimientos_inventario;
DROP TABLE IF EXISTS inventario;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS usuarios;


-- ==================================================================
-- 1) USUARIOS
-- Documento: RF-01 (Iniciar sesión), RF-07 (Gestionar usuarios)
-- Quiénes usan el sistema y con qué permisos (rol).
-- ==================================================================
CREATE TABLE usuarios (
  id              SERIAL PRIMARY KEY,
  nombre          TEXT NOT NULL,
  correo          TEXT NOT NULL UNIQUE,          -- se usa para iniciar sesión, no se puede repetir
  password_hash   TEXT NOT NULL,                 -- la contraseña NUNCA se guarda en texto plano,
                                                  -- aquí se guarda su hash (lo genera el backend)
  rol             TEXT NOT NULL CHECK (rol IN ('administrador', 'empleado')),
  activo          BOOLEAN NOT NULL DEFAULT TRUE, -- para desactivar una cuenta sin borrarla
  fecha_creacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ==================================================================
-- 2) PROVEEDORES
-- Documento: diagrama de clases, relación Proveedor → Producto
-- Quién surte cada producto a la tienda.
-- ==================================================================
CREATE TABLE proveedores (
  id        SERIAL PRIMARY KEY,
  nombre    TEXT NOT NULL,
  telefono  TEXT,                                 -- opcional, según el diccionario del documento
  correo    TEXT                                  -- opcional, según el diccionario del documento
);


-- ==================================================================
-- 3) PRODUCTOS
-- Documento: RF-02 (Gestionar productos)
-- El catálogo de artículos que se venden en la tienda.
-- Nota: aquí NO se guarda la cantidad disponible (eso vive en la
-- tabla "inventario", tabla 4) — así separamos "qué es el
-- producto" de "cuánto hay", tal como lo plantea el diagrama E-R
-- original del documento.
-- ==================================================================
CREATE TABLE productos (
  id             SERIAL PRIMARY KEY,
  nombre         TEXT NOT NULL,
  codigo         TEXT NOT NULL UNIQUE,            -- SKU o código de barras, único por producto
  precio         NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
  costo          NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (costo >= 0),
  categoria      TEXT,
  stock_minimo   INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),  -- usado por RF-05 (alertas)
  proveedor_id   INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
  activo         BOOLEAN NOT NULL DEFAULT TRUE,   -- CU-01: si tiene ventas asociadas, se desactiva
                                                   -- en vez de eliminarse de la base de datos
  fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ==================================================================
-- 4) INVENTARIO
-- Documento: RF-03 (Controlar inventario)
-- La existencia actual de cada producto. Relación 1 a 1 con
-- productos (cada producto tiene exactamente un registro aquí).
-- ==================================================================
CREATE TABLE inventario (
  id                  SERIAL PRIMARY KEY,
  producto_id         INTEGER NOT NULL UNIQUE REFERENCES productos(id) ON DELETE CASCADE,
  existencia_actual   INTEGER NOT NULL DEFAULT 0 CHECK (existencia_actual >= 0),
  fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ==================================================================
-- 5) MOVIMIENTOS DE INVENTARIO
-- Documento: RF-03 (Controlar inventario) — historial de entradas
-- y salidas de mercancía, para saber qué pasó y cuándo.
-- ==================================================================
CREATE TABLE movimientos_inventario (
  id           SERIAL PRIMARY KEY,
  producto_id  INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
  usuario_id   INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,  -- quién hizo el movimiento
  tipo         TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
  cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
  motivo       TEXT,                              -- ej. "compra", "merma", "ajuste", "venta"
  fecha        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ==================================================================
-- 6) VENTAS
-- Documento: RF-04 (Registrar ventas)
-- Cada venta que hace un empleado. El detalle (qué productos y
-- cuántos) vive en la siguiente tabla, "detalle_ventas".
-- ==================================================================
CREATE TABLE ventas (
  id          SERIAL PRIMARY KEY,
  usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,  -- empleado que vendió
  fecha       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total       NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total >= 0)
);


-- ==================================================================
-- 7) DETALLE DE VENTAS
-- Documento: diagrama de clases (DetalleVenta)
-- Cada renglón de una venta: un producto, su cantidad, y su
-- subtotal. Una venta puede tener muchos renglones.
-- ==================================================================
CREATE TABLE detalle_ventas (
  id              SERIAL PRIMARY KEY,
  venta_id        INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
  producto_id     INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
  cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
  precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),  -- precio al momento
                                                                          -- de la venta (aunque
                                                                          -- el producto cambie de
                                                                          -- precio después, este
                                                                          -- registro no cambia)
  subtotal        NUMERIC(10,2) NOT NULL CHECK (subtotal >= 0)          -- cantidad × precio_unitario
);


-- ==================================================================
-- 8) REPORTES
-- Documento: RF-06 (Consultar reportes)
-- Guarda un registro de qué reportes se generaron, cuándo y por
-- quién — no los datos completos del reporte (esos se calculan
-- al momento, consultando ventas/inventario).
-- ==================================================================
CREATE TABLE reportes (
  id                 SERIAL PRIMARY KEY,
  usuario_id         INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,  -- quién lo generó
  tipo               TEXT NOT NULL CHECK (tipo IN ('ventas', 'inventario', 'productos_top')),
  rango_fechas       TEXT,                        -- ej. "2026-09-01 a 2026-09-30"
  total_ventas       NUMERIC(10,2),
  ganancia_estimada  NUMERIC(10,2),                -- del diagrama de clases: total_ventas - costos
  fecha_generacion   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ==================================================================
-- ÍNDICES
-- Aceleran las consultas más frecuentes del sistema. No son
-- obligatorios para que la base funcione, pero sin ellos las
-- consultas se vuelven lentas conforme crecen las tablas.
-- ==================================================================
CREATE INDEX idx_productos_codigo     ON productos(codigo);
CREATE INDEX idx_productos_categoria  ON productos(categoria);
CREATE INDEX idx_inventario_producto  ON inventario(producto_id);
CREATE INDEX idx_movimientos_producto ON movimientos_inventario(producto_id);
CREATE INDEX idx_movimientos_fecha    ON movimientos_inventario(fecha);
CREATE INDEX idx_ventas_fecha         ON ventas(fecha);
CREATE INDEX idx_detalle_venta        ON detalle_ventas(venta_id);


-- ==================================================================
-- DATOS DE PRUEBA
-- Solo para poder probar el sistema de inmediato, sin tener que
-- capturar todo a mano. En producción, este bloque se elimina o
-- se reemplaza con los datos reales de la tienda.
-- ==================================================================

-- Usuarios de ejemplo. La contraseña real (hash bcrypt) se genera
-- desde el backend con un script — 'PENDIENTE_HASH' es solo un
-- marcador temporal, todavía no es una contraseña funcional.
INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES
  ('Administrador General', 'admin@stockmx.com',    'PENDIENTE_HASH', 'administrador'),
  ('Empleado Mostrador',    'empleado@stockmx.com',  'PENDIENTE_HASH', 'empleado');

INSERT INTO proveedores (nombre, telefono, correo) VALUES
  ('Distribuidora La Central', '2711234567', 'contacto@lacentral.com'),
  ('Abarrotera del Valle',     '2717654321', 'ventas@abarroteradelvalle.com');

INSERT INTO productos (nombre, codigo, precio, costo, categoria, stock_minimo, proveedor_id) VALUES
  ('Refresco de cola 600ml', 'REF-600-COLA', 18.00, 12.00, 'Bebidas',   10, 1),
  ('Arroz 1kg',              'ARZ-1KG',      25.50, 18.00, 'Abarrotes', 5,  2),
  ('Aceite vegetal 1L',      'ACE-1L',       45.00, 34.00, 'Abarrotes', 8,  2);

-- El producto 3 (Aceite) queda con menos existencia que su
-- stock_minimo (6 < 8) a propósito, para poder probar la alerta
-- de stock bajo (RF-05) en cuanto exista el backend.
INSERT INTO inventario (producto_id, existencia_actual) VALUES
  (1, 40),
  (2, 15),
  (3, 6);
