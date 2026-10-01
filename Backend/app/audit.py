import logging
from typing import Any

logger = logging.getLogger("stockmx.audit")


def registrar_auditoria(accion: str, usuario_id: int | None, **datos: Any) -> None:
    campos = " ".join(f"{clave}={valor!r}" for clave, valor in sorted(datos.items()))
    logger.info("audit accion=%s usuario_id=%s %s", accion, usuario_id, campos)
