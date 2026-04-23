# atrpt /core/paths.py

from pathlib import Path
import sys
import os


# ------------------------------------------------------------
# BASE DA APLICAÇÃO (repo ou executável)
# ------------------------------------------------------------
def app_base_dir() -> Path:
    """
    Diretório base da aplicação.
    Funciona em dev e com PyInstaller.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


# ------------------------------------------------------------
# PATHS DA APLICAÇÃO (templates, imagens, etc.)
# ------------------------------------------------------------
def resolve_app_path(relative_path: str | Path) -> Path:
    return (app_base_dir() / Path(relative_path)).resolve()


def resolve_app_cfg_path(cfg, key: str) -> Path:
    if key not in cfg.paths_app:
        raise KeyError(f"Path '{key}' não definido em cfg.paths_app")

    return resolve_app_path(cfg.paths_app[key])


# ------------------------------------------------------------
# CONFIG (persistente por utilizador)
# ------------------------------------------------------------
def config_dir(app_name: str = "ATRPT") -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / app_name
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_path(app_name: str = "ATRPT") -> Path:
    return config_dir(app_name) / "app.ini"


# ------------------------------------------------------------
# DADOS OPERACIONAIS (fora do repo)
# ------------------------------------------------------------
def data_dir() -> Path:
    return Path.home()


def resolve_data_path(rel: str | Path) -> Path:
    return (data_dir() / Path(rel)).expanduser().resolve()

# ------------------------------------------------------------
# PATHS COM TEMPLATE ({ano}, {mes}, etc.)
# ------------------------------------------------------------
def resolver_path_template(cfg, key: str, **kwargs) -> Path:
    if key not in cfg.paths_templates:
        raise KeyError(f"Template '{key}' não definido em cfg.paths_templates")

    template = cfg.paths_templates[key]
    kwargs = {k: str(v) for k, v in kwargs.items()}

    return Path(template.format(**kwargs))


# ------------------------------------------------------------
# NORMALIZAÇÃO
# ------------------------------------------------------------
def normalize_path(path: Path | str) -> str:
    if path is None:
        raise ValueError("Path é None")

    return str(Path(path).expanduser().resolve(strict=False))