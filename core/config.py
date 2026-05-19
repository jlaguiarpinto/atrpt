#atrpt/core/config.py
from configparser import ConfigParser
from dataclasses import dataclass, field
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
    imap_server: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_ssl: bool = True
    imap_folders: tuple[str, ...] = ("INBOX",)

# -------------------------
# CONFIG
# -------------------------
@dataclass
class Config:
    modo_teste: bool
    email_teste: str | None
    email_secretaria: str | None
    email_associados: str | None

    nif_proprio: str | None             = None
    paths_app: dict[str, Path]          = field(default_factory=dict)
    paths: dict[str, Path]              = field(default_factory=dict)
    paths_templates: dict[str, str]     = field(default_factory=dict)
    users: dict[str, list[str]]         = field(default_factory=dict)
    emails: dict[str, EmailProfile]     = field(default_factory=dict)
    centros_custo: list[str]            = field(default_factory=list)
    email_listas: dict[str, list[str]]  = field(default_factory=dict)

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
    # EMAIL LISTAS
    # -------------------------
    def get_lista_emails(self, secao: str) -> list[str]:
        return self.email_listas.get(secao, [])

    # -------------------------
    # VALIDAÇÃO OPCIONAL
    # -------------------------
    def check_paths_exist(self) -> None:
        for key, value in self.paths.items():
            if not value.exists():
                raise FileNotFoundError(f"[CONFIG] Path não existe: {key} -> {value}")

# -------------------------
# HELPERS INTERNOS
# -------------------------
_PATTERN = re.compile(r"\{([^{}]+)\}")
_DATE_TOKENS = {"ano", "mes", "dia"}

def _resolve_raw(raw_paths: dict[str, str]) -> dict[str, str]:
    """Resolve placeholders entre chaves dentro do mesmo dict de raw strings."""
    resolved: dict[str, str] = {}
    for key, value in raw_paths.items():
        while True:
            new_value = value
            for match in _PATTERN.findall(value):
                if match in _DATE_TOKENS:
                    continue
                if match not in raw_paths:
                    raise KeyError(f"[CONFIG] Placeholder '{{{match}}}' não definido em nenhuma secção carregada.")
                new_value = new_value.replace(f"{{{match}}}", raw_paths[match])
            if new_value == value:
                break
            value = new_value
        resolved[key] = value
    return resolved

def _to_paths(resolved_raw: dict[str, str], base_dir: Path) -> dict[str, Path]:
    """Converte strings resolvidas em Path absolutos."""
    result: dict[str, Path] = {}
    for key, value in resolved_raw.items():
        p = Path(value)
        if not p.is_absolute():
            p = base_dir / p
        result[key] = p.resolve()
    return result

# -------------------------
# LOAD CONFIG
# Carrega: modo, emails, users, centros_custo, paths_app.
# NÃO carrega paths de dados — cada main chama load_paths().
# -------------------------
def load_config(path: Path) -> Config:

    parser = ConfigParser(interpolation=None, strict=False)
    parser.read(path, encoding="utf-8")
    base_dir = path.parent

    # -------------------------
    # MODO
    # -------------------------
    modo_teste  = parser.getboolean("modo", "teste",        fallback=False)
    email_teste = parser.get("modo", "email_teste",         fallback=None)
    # email_secretaria e email_associados derivados dos perfis [email.*];
    # apenas substituídos se estiverem explicitamente em [modo] (retrocompatibilidade)
    _email_secretaria_override = parser.get("modo", "email_secretaria", fallback=None)
    _email_associados_override = parser.get("modo", "email_associados", fallback=None)

    nif_proprio = parser.get("organizacao", "nif", fallback=None)

    # -------------------------
    # PATHS_APP (relativos à raiz da app — secção legada)
    # -------------------------
    paths_app: dict[str, Path] = {}
    if parser.has_section("paths_app"):
        for key, value in parser["paths_app"].items():
            p = Path(value)
            if not p.is_absolute():
                p = base_dir / p
            paths_app[key] = p.resolve()

    # -------------------------
    # EMAIL PROFILES
    # -------------------------
    emails: dict[str, EmailProfile] = {}
    for section in parser.sections():
        if section.startswith("email."):
            perfil = section.split(".", 1)[1]
            raw_folders = parser.get(section, "imap_folders", fallback="INBOX")
            imap_folders = tuple(f.strip() for f in raw_folders.split(",") if f.strip())
            imap_user = parser.get(section, "imap_user", fallback="") or parser.get(section, "smtp_user", fallback="")
            emails[perfil] = EmailProfile(
                email_address=parser[section]["email_address"],
                smtp_server=parser[section]["smtp_server"],
                smtp_port=int(parser[section]["smtp_port"]),
                smtp_user=parser[section]["smtp_user"],
                smtp_password=parser[section]["smtp_password"],
                smtp_ssl=parser.getboolean(section, "smtp_ssl", fallback=False),
                imap_server=parser.get(section, "imap_server", fallback=""),
                imap_port=int(parser.get(section, "imap_port", fallback="993")),
                imap_user=imap_user,
                imap_password=parser.get(section, "imap_password", fallback=""),
                imap_ssl=parser.getboolean(section, "imap_ssl", fallback=True),
                imap_folders=imap_folders,
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
    # EMAIL LISTAS  ([emails_*] com chave "lista")
    # -------------------------
    email_listas: dict[str, list[str]] = {}
    for section in parser.sections():
        if section.startswith("emails_"):
            raw_lista = parser.get(section, "lista", fallback="")
            email_listas[section] = [e.strip() for e in raw_lista.split(",") if e.strip()]

    # derivar endereços dos perfis de email (fonte única de verdade)
    def _addr(perfil: str, override: str | None) -> str | None:
        if override:
            return override
        p = emails.get(perfil)
        return p.email_address if p else None

    email_secretaria = _addr("secretaria", _email_secretaria_override)
    email_associados = _addr("associados", _email_associados_override)

    return Config(
        modo_teste=modo_teste,
        email_teste=email_teste,
        email_secretaria=email_secretaria,
        email_associados=email_associados,
        nif_proprio=nif_proprio,
        paths_app=paths_app,
        users=users,
        emails=emails,
        centros_custo=centros_custo,
        email_listas=email_listas,
    )

# -------------------------
# LOAD PATHS
# Carrega e resolve paths das secções indicadas.
# Chamar com "paths_comum" + a(s) secção(ões) do módulo.
# Exemplo: load_paths(ini, "paths_comum", "paths_secretaria")
# -------------------------
def load_paths(ini_path: Path, *sections: str) -> dict[str, Path]:
    parser = ConfigParser(interpolation=None, strict=False)
    parser.read(ini_path, encoding="utf-8")
    base_dir = ini_path.parent

    raw: dict[str, str] = {}
    for section in sections:
        if parser.has_section(section):
            for key, value in parser[section].items():
                raw[key] = value.strip()

    resolved_raw = _resolve_raw(raw)
    return _to_paths(resolved_raw, base_dir)

# -------------------------
# LOAD PATHS TEMPLATES
# Carrega [paths_templates] e substitui {chave} com os paths já resolvidos.
# Tokens de data ({ano}, {mes}, {dia}) ficam como estão para uso em runtime.
# -------------------------
def load_paths_templates(ini_path: Path, paths: dict[str, Path]) -> dict[str, str]:
    parser = ConfigParser(interpolation=None, strict=False)
    parser.read(ini_path, encoding="utf-8")

    templates: dict[str, str] = {}
    if parser.has_section("paths_templates"):
        for key, value in parser["paths_templates"].items():
            template = value.strip()
            for name, resolved in paths.items():
                template = template.replace(f"{{{name}}}", str(resolved))
            templates[key] = template
    return templates
