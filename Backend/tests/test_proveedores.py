import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database
from app.auth.security import crear_token
from app.main import app
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario


class ProveedorDeleteTests(unittest.TestCase):
    def setUp(self):
        database.engine = create_engine(
            "sqlite:////tmp/stockmx_test.db",
            connect_args={"check_same_thread": False},
        )
        database.Base.metadata.drop_all(bind=database.engine)
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
        database.Base.metadata.create_all(bind=database.engine)

        self.db = database.SessionLocal()
        admin = Usuario(
            nombre="Admin prueba",
            correo="admin@test.com",
            password_hash="hash",
            rol="administrador",
            activo=True,
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        self.admin_id = admin.id
        self.token = crear_token({"sub": str(self.admin_id)})

        proveedor = Proveedor(nombre="Proveedor prueba", telefono="123", correo="proveedor@test.com")
        self.db.add(proveedor)
        self.db.commit()
        self.db.refresh(proveedor)
        self.proveedor_id = proveedor.id

        app.dependency_overrides[database.get_db] = self._override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _override_get_db(self):
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def test_delete_proveedor_endpoint_removes_supplier(self):
        response = self.client.delete(
            f"/proveedores/{self.proveedor_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.db.get(Proveedor, self.proveedor_id))


if __name__ == "__main__":
    unittest.main()
