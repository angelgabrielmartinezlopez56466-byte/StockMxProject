import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Lee el archivo .env (ahí vive DATABASE_URL, con la contraseña real)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "No se encontró DATABASE_URL. Revisa que exista el archivo .env "
        "en la raíz de Backend/ con esa variable definida."
    )

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal genera una "sesión" de trabajo con la base de datos
# cada vez que una petición a la API necesita leer o escribir algo.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base es la clase de la que van a heredar todos nuestros modelos
# (Usuario, Producto, Venta...) en la carpeta models/.
Base = declarative_base()


def get_db():
    """
    Abre una sesión de base de datos para una petición, y la cierra
    automáticamente al terminar (haya error o no). Cada endpoint de
    la API la usa así:

        @router.get("/productos")
        def listar_productos(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
