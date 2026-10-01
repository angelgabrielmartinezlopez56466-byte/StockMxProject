DROP TABLE IF EXISTS reportes;
DROP TABLE IF EXISTS detalle_ventas;
DROP TABLE IF EXISTS ventas;
DROP TABLE IF EXISTS movimientos_inventario;
DROP TABLE IF EXISTS inventario;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS usuarios;
CREATE TABLE usuarios (
  id              SERIAL PRIMARY KEY,
  nombre          TEXT NOT NULL,
  correo          TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,
  rol             TEXT NOT NULL CHECK (rol IN ('administrador', 'empleado')),
  activo          BOOLEAN NOT NULL DEFAULT TRUE,
  fecha_creacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE proveedores (
  id        SERIAL PRIMARY KEY,
  nombre    TEXT NOT NULL,
  telefono  TEXT,
  correo    TEXT
);
CREATE TABLE productos (
  id             SERIAL PRIMARY KEY,
  nombre         TEXT NOT NULL,
  codigo         TEXT NOT NULL UNIQUE,
  precio         NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
  costo          NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (costo >= 0),
  categoria      TEXT,
  stock_minimo   INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
  proveedor_id   INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
  activo         BOOLEAN NOT NULL DEFAULT TRUE,
  fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE inventario (
  id                  SERIAL PRIMARY KEY,
  producto_id         INTEGER NOT NULL UNIQUE REFERENCES productos(id) ON DELETE CASCADE,
  existencia_actual   INTEGER NOT NULL DEFAULT 0 CHECK (existencia_actual >= 0),
  fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE movimientos_inventario (
  id           SERIAL PRIMARY KEY,
  producto_id  INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
  usuario_id   INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  tipo         TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
  cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
  motivo       TEXT,
  fecha        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE ventas (
  id          SERIAL PRIMARY KEY,
  usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
  fecha       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total       NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total >= 0)
);
CREATE TABLE detalle_ventas (
  id              SERIAL PRIMARY KEY,
  venta_id        INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
  producto_id     INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
  cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
  precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),
  subtotal        NUMERIC(10,2) NOT NULL CHECK (subtotal >= 0)
);
CREATE TABLE reportes (
  id                 SERIAL PRIMARY KEY,
  usuario_id         INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  tipo               TEXT NOT NULL CHECK (tipo IN ('ventas', 'inventario', 'productos_top')),
  rango_fechas       TEXT,
  total_ventas       NUMERIC(10,2),
  ganancia_estimada  NUMERIC(10,2),
  fecha_generacion   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_productos_codigo     ON productos(codigo);
CREATE INDEX idx_productos_categoria  ON productos(categoria);
CREATE INDEX idx_inventario_producto  ON inventario(producto_id);
CREATE INDEX idx_movimientos_producto ON movimientos_inventario(producto_id);
CREATE INDEX idx_movimientos_fecha    ON movimientos_inventario(fecha);
CREATE INDEX idx_ventas_fecha         ON ventas(fecha);
CREATE INDEX idx_detalle_venta        ON detalle_ventas(venta_id);
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
INSERT INTO inventario (producto_id, existencia_actual) VALUES
  (1, 40),
  (2, 15),
  (3, 6);
