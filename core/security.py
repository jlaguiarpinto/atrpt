#atrpt /core/security.py

from dataclasses import dataclass

PERFIS = {
    "Dir":    "Direcção",
    "DirFin": "Direcção — Financeiro",
    "DL":     "Direcção Lar",
    "DCD":    "Direcção Centro de Dia",
    "SG":     "Serviços Gerais",
    "RH":     "Recursos Humanos",
    "CS":     "Chefe de Secretaria",
    "Sec":    "Secretaria",
}

# Permissões funcionais (tabela permissions) — ortogonais ao perfil
PERMISSOES = {
    "dev": "Acesso de desenvolvimento/administração",
}

PERFIS_DIRECAO = {"Dir", "DirFin"}

@dataclass
class userContext:
    username: str
    nome: str
    email: str
    nif: str | None
    ativo: bool
    permissions: set[str]
    perfil: str | None = None  # código do perfil: Dir, DL, DCD, SG, RH, CS, Sec

class AuthorizationService:

    def __init__(self, user_context: userContext):
        self.user = user_context

    def has_permission(self, permission_code: str) -> bool:
        #return permission_code in self.user.permissions       por agora todos têm todas as permissões
        return True

    def require(self, permission_code: str):
        if not self.has_permission(permission_code):
            raise PermissionError(
                f"Utilizador sem permissão: {permission_code}"
            )