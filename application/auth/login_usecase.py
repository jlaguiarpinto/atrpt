#atrpt /application/auth/login_usecase.py
import getpass
from core.security import userContext
from presentation.shared.user_register_gui import userRegisterGUI

class LoginUseCase:

    def __init__(self, user_repository):
        self.user_repository = user_repository

    def execute(self, parent) -> userContext:                           # Construir userContext

        username = getpass.getuser().lower()                    # 1. Obter username do sistema
        user = self.user_repository.get_by_username(username)   # 2. Procurar utilizador na base de dados e cria se não existir
        if not user:                              
            dados = userRegisterGUI.ask(parent, username)
            if not dados:
                raise RuntimeError("Registo cancelado.")
            user = self.user_repository.create(
                username=username,
                nome=dados["nome"],
                email=dados["email"],
                nif=dados["nif"],
                perfil=dados.get("perfil"),
            )
        
        if not user.ativo:
            raise PermissionError("Utilizador desativado.")
        return userContext(
            username=user.username,
            nome=user.nome,
            email=user.email,
            nif=user.nif,
            ativo=user.ativo,
            permissions=set(user.permissions),
            perfil=getattr(user, "perfil", None),
        )