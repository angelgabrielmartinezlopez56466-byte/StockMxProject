import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database
from app.auth.security import crear_token
from app.main import app
from app.models.usuario import Usuario


class UsuarioManagementTests(unittest.TestCase):
    def setUp(self):
        database.engine = create_engine(
            "sqlite:////tmp/stockmx_usuarios_test.db",
            connect_args={"check_same_thread": False},
        )
        database.Base.metadata.drop_all(bind=database.engine)
        database.Base.metadata.create_all(bind=database.engine)
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

        self.db = database.SessionLocal()
        administrador_1 = Usuario(
            nombre="Admin principal",
            correo="admin1@test.com",
            password_hash="hash",
            rol="administrador",
            activo=True,
        )
        administrador_2 = Usuario(
            nombre="Admin secundario",
            correo="admin2@test.com",
            password_hash="hash",
            rol="administrador",
            activo=True,
        )
        empleado = Usuario(
            nombre="Empleado prueba",
            correo="empleado@test.com",
            password_hash="hash",
            rol="empleado",
            activo=True,
        )
        self.db.add_all([administrador_1, administrador_2, empleado])
        self.db.commit()
        self.db.refresh(administrador_1)
        self.db.refresh(administrador_2)
        self.db.refresh(empleado)

        self.admin_1_id = administrador_1.id
        self.admin_2_id = administrador_2.id
        self.employee_id = empleado.id
        self.token = crear_token({"sub": str(self.admin_1_id)})

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

    def test_delete_admin_allowed_when_other_admin_exists(self):
        response = self.client.delete(
            f"/usuarios/{self.admin_2_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.db.get(Usuario, self.admin_2_id))

    def test_delete_last_admin_is_blocked(self):
        self.db.query(Usuario).filter(Usuario.id != self.admin_1_id).delete()
        self.db.commit()

        response = self.client.delete(
            f"/usuarios/{self.admin_1_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIsNotNone(self.db.get(Usuario, self.admin_1_id))

    def test_delete_employee_is_allowed(self):
        response = self.client.delete(
            f"/usuarios/{self.employee_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.db.get(Usuario, self.employee_id))


if __name__ == "__main__":
    unittest.main()
