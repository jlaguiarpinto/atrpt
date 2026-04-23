# atrpt/core/logging_utils.py

from pathlib import Path
import logging
import sys


# --------------------------------------------------
# SETUP PRINCIPAL
# --------------------------------------------------

def setup_logging(cfg, app_name: str):
    """
    Configura logging global:
    - consola
    - ficheiro geral (app.log)
    - ficheiro de erros (error.log)
    """

    # usar paths_dados se disponível (path absoluto), senão paths_app
    base_log_dir = Path(cfg.paths.get("log_dir"))
    log_dir = base_log_dir / app_name
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{app_name}.log"
    error_file = log_dir / "error.log"

    root = logging.getLogger()
    root.handlers.clear()  # 🔴 crítico: evitar duplicações
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    # -------------------------
    # LOG GERAL (INFO+)
    # -------------------------
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    # -------------------------
    # LOG DE ERROS (ERROR+)
    # -------------------------
    eh = logging.FileHandler(error_file, encoding="utf-8")
    eh.setLevel(logging.ERROR)
    eh.setFormatter(formatter)

    # -------------------------
    # CONSOLA
    # -------------------------
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    # -------------------------
    # REGISTAR HANDLERS
    # -------------------------
    root.addHandler(fh)
    root.addHandler(eh)
    root.addHandler(ch)

    return root

# --------------------------------------------------
# LOG DE ERROS (UNIFICADO)
# --------------------------------------------------

def log_error(context: str, extra: dict | None = None):
    """
    Regista erro com contexto + traceback
    Vai automaticamente para:
    - consola
    - GUI
    - app.log
    - error.log
    """

    msg = f"Contexto: {context}"

    if extra:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
        msg += f" | {extra_str}"

    logging.error(msg, exc_info=True)

# --------------------------------------------------
# AUDIT LOGGER
# --------------------------------------------------

def setup_audit_logger(cfg, app_name: str) -> logging.Logger:
    """Devolve logger dedicado para auditoria. Escreve em logs/<app_name>/audit.log"""
    base_log_dir = Path(
        cfg.paths.get("log_dir") or
        cfg.paths_app.get("log_dir", "logs")
    )
    log_dir = base_log_dir / app_name
    log_dir.mkdir(parents=True, exist_ok=True)

    audit_file = log_dir / "audit.log"
    logger = logging.getLogger(f"audit.{app_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        fh = logging.FileHandler(audit_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)

    return logger


def audit(logger: logging.Logger, utilizador: str, accao: str, detalhe: str = ""):
    """Regista entrada de auditoria."""
    msg = f"{utilizador} | {accao}"
    if detalhe:
        msg += f" | {detalhe}"
    logger.info(msg)


# --------------------------------------------------
# (OPCIONAL FUTURO)
# --------------------------------------------------

class ErrorOnlyFilter(logging.Filter):
    """Permite filtrar apenas erros."""
    def filter(self, record):
        return record.levelno >= logging.ERROR