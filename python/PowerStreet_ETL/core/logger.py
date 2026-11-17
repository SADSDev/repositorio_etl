#=================================================
# LIBRERIAS
#===============================================
import logging
from pathlib import Path
from datetime import date

#================================================
# PROCESOS
#================================================
def obtener_error_resumido(exc: Exception) -> str:

    # Buscar la excepción más profunda de la cadena
    error_final = exc

    while error_final.__cause__ is not None:
        error_final = error_final.__cause__

    return (
        f"{type(error_final).__name__}: {error_final}"
    )


def configurar_logger():

    carpeta = Path("logs")
    carpeta.mkdir(exist_ok=True)

    fecha = date.today().isoformat()

    logger = logging.getLogger("PowerStreet_ETL")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:

        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Log general
        general = logging.FileHandler(
            carpeta / f"{fecha}_proceso.log",
            encoding="utf-8"
        )
        general.setFormatter(formato)

        consola = logging.StreamHandler()
        consola.setFormatter(formato)

        logger.addHandler(general)
        logger.addHandler(consola)

    return logger