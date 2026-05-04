#atrpt/core/config.py
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import re
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import re

# -------------------------
# EMAIL PROFILE
# -------------------------
@dataclass(frozen=True)
class EmailProfile:
    email_address: str
    smtp_server: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_ssl: bool

# -------------------------
# PATHS (TIPADO)
# -------------------------
@dataclass(frozen=True)
class PathsDados:
    comprovativo_file: Path
    inflow_file: Path
    comprovativodd_file: Path
    residentes_file: Path
    residentes_cc_file: Path
    pim_file: Path
    associados_file: Path
    saldos_file: Path

# -------------------------
# CONFIG
# -------------------------
@dataclass(frozen=True)
class Config:
    modo_teste: bool
    email_teste: str | None
    email_secretaria: str | None
    email_associados: str | None

    paths: dict[str, Path]
    paths_app: dict[str, Path]
    paths_templates: dict[str, str]

    users: dict[str, list[str]]
    emails: dict[str, EmailProfile]
    centros_custo: list[str]

    # -------------------------
    # EMAILS
    # -------------------------
    def get_email_profile(self, name: str) -> EmailProfile:
        if name not in self.emails:
            raise ValueError(f"[CONFIG] Perfil de email não existe: {name}")
        return self.emails[name]

    # -------------------------
    # USERS
    # -------------------------
    def get_users(self, key: str) -> list[str]:
        return self.users.get(key, [])

    # -------------------------
    # VALIDAÇÃO OPCIONAL
    # -------------------------
    def check_paths_exist(self) -> None:
        for field, value in self.paths.__dict__.items():
            if not value.exists():
                raise FileNotFoundError(f"[CONFIG] Path não existe: {field} -> {value}")
            
# -------------------------
# LOAD CONFIG
# -------------------------
def load_config(path: Path) -> Config:

    parser = ConfigParser(interpolation=None,strict=False)
    parser.read(path, encoding="utf-8")
    base_dir = path.parent

    # -------------------------
    # MODO
    # -------------------------
    modo_teste = parser.getboolean("modo", "teste", fallback=False)
    email_teste = parser.get("modo", "email_teste", fallback=None)
    email_secretaria = parser.get("modo", "email_secretaria", fallback=None)
    email_associados = parser.get("modo", "email_associados", fallback=None)
    
    # -------------------------
    # PATHS_APP
    # -------------------------
    paths_app: dict[str, Path] = {}

    if parser.has_section("paths_app"):
        for key, value in parser["paths_app"].items():
            p = Path(value)
            if not p.is_absolute():
                p = base_dir / p
            paths_app[key] = p.resolve()

    # -------------------------
    # PATHS_DADOS (raw)
    # -------------------------
    raw_paths: dict[str, str] = {}

    if parser.has_section("paths_dados"):
        for key, value in parser["paths_dados"].items():
            raw_paths[key] = value.strip()


    pattern = re.compile(r"\{([^{}]+)\}")
    def resolve_value(value: str) -> str:
        while True:
            new_value = value
            for match in pattern.findall(value):
                if match in ("ano", "mes", "dia"):
                    continue
                if match not in raw_paths:
                    raise KeyError(f"[CONFIG] Placeholder '{{{match}}}' não definido.")
                new_value = new_value.replace(f"{{{match}}}", raw_paths[match])
            if new_value == value:
                break
            value = new_value
        return value

    # -------------------------
    # RESOLVER PATHS_DADOS
    # -------------------------
    resolved_paths: dict[str, Path] = {}
    for key, value in raw_paths.items():
        resolved = resolve_value(value)
        p = Path(resolved)
        if not p.is_absolute():
            p = base_dir / p
        resolved_paths[key] = p.resolve()

    # -------------------------
    # BUILDER TIPADO
    # -------------------------

    # -------------------------
    # PATHS_TEMPLATES
    # -------------------------
    paths_templates: dict[str, str] = {}

    if parser.has_section("paths_templates"):
        for key, value in parser["paths_templates"].items():

            template = value.strip()

            for name, resolved in resolved_paths.items():
                template = template.replace(f"{{{name}}}", str(resolved))

            paths_templates[key] = template

    # -------------------------
    # EMAIL PROFILES
    # -------------------------
    emails: dict[str, EmailProfile] = {}

    for section in parser.sections():
        if section.startswith("email."):

            perfil = section.split(".", 1)[1]

            emails[perfil] = EmailProfile(
                email_address=parser[section]["email_address"],
                smtp_server=parser[section]["smtp_server"],
                smtp_port=int(parser[section]["smtp_port"]),
                smtp_user=parser[section]["smtp_user"],
                smtp_password=parser[section]["smtp_password"],
                smtp_ssl=parser.getboolean(section, "smtp_ssl", fallback=False),
            )

    # -------------------------
    # USERS
    # -------------------------
    users: dict[str, list[str]] = {}

    if parser.has_section("users"):
        for key, value in parser["users"].items():
            users[key] = [u.strip() for u in value.split(";") if u.strip()]

    # -------------------------
    # CENTROS DE CUSTO
    # -------------------------
    centros_custo: list[str] = []

    if parser.has_section("aprovisionamento"):
        raw = parser.get("aprovisionamento", "centros_custo", fallback="")
        centros_custo = [c.strip() for c in raw.split(",") if c.strip()]

    # -------------------------
    # FINAL
    # -------------------------
    
    return Config(
        modo_teste=modo_teste,
        email_teste=email_teste,
        email_secretaria=email_secretaria,
        email_associados=email_associados,
        paths=resolved_paths,
        paths_app=paths_app,
        paths_templates=paths_templates,
        users=users,
        emails=emails,
        centros_custo=centros_custo,
    )

def build_paths(paths_dict: dict[str, Path]) -> dict[str, Path]:
    return {
        "inflow_file": paths_dict["inflow_file"],
        "comprovativo_file": paths_dict["comprovativo_file"],
        "comprovativodd_file": paths_dict["comprovativodd_file"],
        "residentes_file": paths_dict["residentes_file"],
        "residentes_cc_file": paths_dict["residentes_cc_file"],
        "pim_file": paths_dict["pim_file"],
        "associados_file": paths_dict["associados_file"],
        "saldos_file": paths_dict["saldos_file"],
    }

