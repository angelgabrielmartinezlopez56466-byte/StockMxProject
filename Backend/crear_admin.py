"""
crear_admin.py
----------------
Script de un solo uso: reemplaza los 'PENDIENTE_HASH' de los
usuarios semilla (admin@stockmx.com, empleado@stockmx.com) con
hashes reales de contraseña, para poder hacer login de verdad.

Se corre así, desde la carpeta Backend:
    python3 crear_admin.py
"""

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.auth.security import hashear_password

db = SessionLocal()

# Contraseñas reales que vas a usar para entrar al sistema.
# Cámbialas aquí si quieres algo distinto antes de correr el script.
credenciales = {
    "admin@stockmx.com": "admin123",
    "empleado@stockmx.com": "empleado123",
}

for correo, password_plano in credenciales.items():
    usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
    if usuario:
        usuario.password_hash = hashear_password(password_plano)
        print(f"Contraseña actualizada para: {correo}")
    else:
        print(f"No se encontró un usuario con correo: {correo}")

db.commit()
db.close()
print("Listo. Ya puedes iniciar sesión con esas credenciales.")
