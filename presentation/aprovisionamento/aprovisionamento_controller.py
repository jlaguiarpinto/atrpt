# atrpt/presentation/aprovisionamento/aprovisionamento_controller.py

import logging
from core.logging_utils import audit

logger = logging.getLogger(__name__)

class AprovisionamentoController:

    def __init__(
        self,
        gui,
        user_context,
        cfg,
        audit_log,
        create_uc,
        add_proposta_uc,
        select_proposta_uc,
        autorizar_uc,
        encomendar_uc,
        enviar_uc,
        list_pedidos_uc,
        list_fornecedores_uc,
        fornecedor_repo,
        encomenda_repo,
        pedido_repo=None,
        user_repo=None,
        submeter_uc=None,
    ):
        self.gui = gui
        self.user = user_context
        self.cfg = cfg
        self.audit_log = audit_log

        self.encomendar_uc = encomendar_uc
        self.create_uc = create_uc
        self.add_proposta_uc = add_proposta_uc
        self.select_proposta_uc = select_proposta_uc
        self.autorizar_uc = autorizar_uc
        self.enviar_uc = enviar_uc
        self.list_pedidos_uc = list_pedidos_uc
        self.list_fornecedores_uc = list_fornecedores_uc

        self.pedido_repo = pedido_repo
        self.fornecedor_repo = fornecedor_repo
        self.encomenda_repo = encomenda_repo
        self.user_repo = user_repo
        self.submeter_uc = submeter_uc

    # -------------------------------------------------
    # Fornecedores
    # -------------------------------------------------

    def importar_fornecedores(self, file_path: str):

        try:
            total = self.import_fornecedores_uc.execute(file_path)

            self.gui.informuser(
                "Importação concluída",
                f"{total} fornecedores importados."
            )

        except Exception as e:
            self.gui.informuser("Erro", str(e), tipo="error")

    def importar_fornecedores_dialog(self):

        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx")]
        )

        if not file_path:
            return

        self.importar_fornecedores(file_path)

    def importar_fornecedores_dialog(self):

        file_path = self.gui.ask_file(
            title="Selecionar ficheiro Excel",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )

        if not file_path:
            return

        try:
            total = self.import_fornecedores_uc.execute(file_path)

            self.gui.informuser(
                "Importação concluída",
                f"{total} fornecedores processados."
            )

        except Exception as e:
            self.gui.informuser("Erro", str(e), tipo="error")

    def novo_fornecedor(self, dados: dict):
        """Cria fornecedor a partir de dict {nome, nif, ...}. Devolve o fornecedor criado."""
        try:
            self.fornecedor_repo.save_from_dict(dados)
            # devolver o fornecedor recém-criado para actualizar o combobox
            return self.fornecedor_repo.get_by_nome(dados["nome"])
        except Exception as e:
            logger.exception("Erro ao criar fornecedor")
            raise

    def novo_fornecedor_dialog(self):

        data = self.gui.form_fornecedor_dialog()

        if not data:
            return

        self.fornecedor_repo.save_from_dict(data)

        self.gui.informuser(
            "Fornecedor",
            "Fornecedor criado com sucesso.",
            tipo="info"
        )

    def listar_fornecedores_dialog(self):
        from presentation.aprovisionamento.fornecedores_gui import FornecedoresListGUI
        fornecedores = self.list_fornecedores_uc.execute()
        self.gui.show_view (FornecedoresListGUI,self,fornecedores)

    # -------------------------------------------------
    # Pedidos
    # -------------------------------------------------

    def adicionar_proposta(self, numero, fornecedor_id, valor, documento):
        logger.info(f"Chamando controller com: numero={numero}, fornecedor_id=fornecedor_id, valor={valor}, documento={documento}")
        try:
            # Chamar o usecase para adicionar proposta
            self.add_proposta_uc.execute(
                numero=numero,
                fornecedor_id=fornecedor_id,
                valor=valor,
                documento=documento)

            self.gui.informuser("OK", "Proposta adicionada com sucesso.")

        except Exception as e:
            import traceback
            logger.error(f">>> EXCEPÇÃO em adicionar_proposta: {e}")
            logger.error(traceback.format_exc())
            raise  # re-lança para a GUI apanhar e mostrar

    def adicionar_proposta_dialog(self):
        """Abre diálogo para adicionar proposta a um pedido existente"""
        from presentation.aprovisionamento.pedido_proposta_gui import JuntarPropostaGUI

        # Criar janela modal
        win = tk.Toplevel()
        win.title("Adicionar Proposta")
        win.grab_set()

        JuntarPropostaGUI(win, self)
        self.gui.root.wait_window(win)

    def selecionar_proposta(self, numero, fornecedor_id):
        try:
            self.select_proposta_uc.execute(numero, fornecedor_id)
            self.gui.informuser("OK", "Proposta selecionada.")

        except Exception as e:
            self.gui.informuser("Erro", str(e), tipo="error")

    def criar_pedido_dialog(self):

        # 1. dados
        centros_custo = self.container.cfg.centros_custo
        fornecedores = self.list_fornecedores_uc.execute()

        # 2. form
        data = self.gui.form_pedido_dialog(
            centros_custo=centros_custo,
            fornecedores=[f.nome for f in fornecedores]
        )

        if not data:
            return

        # 3. mapping nome → id
        map_forn = {f.nome: f.id for f in fornecedores}

        # 4. normalizar proposta
        proposta = []
        for p in data["proposta"]:
            if not p:
                continue

            proposta.append({
                "fornecedor_id": map_forn[p["fornecedor"]],
                "valor": p["valor"],
                "pdf_path": p["pdf_path"]
            })

        # 5. criar pedido
        self.criar_pedido(
            centro_custo=data["centro_custo"],
            descricao=data["descricao"],
            criado_por=self.user.username,
            proposta=proposta
        )

    def criar_pedido(self, centro_custo, descricao, proposta):
        from domain.aprovisionamento.entities import Proposta
        """
        propostas = [
            Proposta(
                fornecedor_id=p["fornecedor_id"],
                valor=p["valor"],
                pdf_path=p["documento"],
            )
            for p in proposta
        ]   """

        pedido = self.create_uc.execute(
            centro_custo=centro_custo,
            descricao=descricao,
            criado_por=self.user.username,
            propostas=proposta
        )

        self.gui.informuser(
            "Pedido criado",
            f"Pedido {pedido.numero} criado com sucesso."
        )

    # -------------------------------------------------

    def autorizar_pedido(self, numero, proposta=None):
        pedido = self.autorizar_uc.execute(numero, self.user.username, proposta)
        audit(
            self.audit_log,
            utilizador=self.user.username,
            accao="autorizar_pedido",
            detalhe=f"pedido={numero} proposta_forn={getattr(proposta, 'fornecedor_id', '')}",
        )
        return pedido

    def autorizar_pedido_dialog(self):

        numero = self.gui.pedirInput("Autorizar Pedido", "Número do pedido:", "int")
        if not numero:
            return

        self.autorizar_pedido(numero, self.user.username)

    def recusar_pedido(self, numero: str) -> None:
        from domain.aprovisionamento.enums import PedidoEstado
        if not self.pedido_repo:
            raise ValueError("Repositório de pedidos não configurado.")
        pedido = self.pedido_repo.get_by_numero(numero)
        if not pedido:
            raise ValueError(f"Pedido {numero} não encontrado.")
        if pedido.estado != PedidoEstado.pendente:
            raise ValueError(f"Só é possível recusar pedidos em estado 'pendente' (estado actual: '{pedido.estado.value}').")
        pedido.estado = PedidoEstado.cancelado
        self.pedido_repo.save(pedido)
        audit(
            self.audit_log,
            utilizador=self.user.username,
            accao="recusar_pedido",
            detalhe=f"pedido={numero}",
        )

    def nao_autorizar_pedido(self, numero: str) -> None:
        """Devolve o pedido ao estado 'criado' para revisão pelo requerente."""
        from domain.aprovisionamento.enums import PedidoEstado
        if not self.pedido_repo:
            raise ValueError("Repositório de pedidos não configurado.")
        pedido = self.pedido_repo.get_by_numero(numero)
        if not pedido:
            raise ValueError(f"Pedido {numero} não encontrado.")
        if pedido.estado != PedidoEstado.pendente:
            raise ValueError(f"Só é possível devolver pedidos em estado 'pendente' (estado actual: '{pedido.estado.value}').")
        pedido.estado = PedidoEstado.criado
        self.pedido_repo.save(pedido)
        audit(
            self.audit_log,
            utilizador=self.user.username,
            accao="nao_autorizar_pedido",
            detalhe=f"pedido={numero}",
        )

    # -------------------------------------------------

    def enviar_pedido(self, numero):

        try:
            pedido = self.enviar_uc.execute(numero)

            self.gui.informuser(
                "Enviado",
                f"Pedido {pedido.numero} enviado com sucesso."
            )

        except Exception as e:
            self.gui.informuser("Erro", str(e), tipo="error")

    def enviar_pedido_dialog(self):

        numero = self.gui.pedirInput("Enviar Pedido", "Número do pedido:", "int")
        if not numero:
            return

        self.enviar_pedido(numero)

    def autorizar_encomenda(self, numero):
        return self.service.autorizar_encomenda(numero, self.user.username)

    # -------------------------------------------------


    def listar_pedidos_para_proposta(self):
        """Pedidos elegíveis para receber proposta — exclui aprovado, cancelado, concluido."""
        estados = ["criado", "pendente",]
        try:
            return self.list_pedidos_uc.execute(*estados)
        except Exception as e:
            logger.exception("Erro ao listar pedidos para proposta")
            return []

    def listar_pedidos(self, *estados):
        """Devolve pedidos filtrados pelos estados indicados. Sem estados devolve todos."""
        try:
            return self.list_pedidos_uc.execute(*estados)
        except Exception as e:
            logger.exception("Erro ao listar pedidos")
            raise

    def listar_pendentes_dialog(self):
        self.listar_pendentes()

    def encomendar(self, numero):
        return self.encomendar_uc.execute(numero, encomendado_por=self.user.username)

    def get_centros_custo(self):
        return self.cfg.centros_custo

    def pedir_aprovacao(self, numero: str, proposta, diretor_financeiro, diretor2,
                        observacoes: str = "") -> None:
        """Muda pedido de 'criado' para 'pendente' e envia email aos dois diretores."""
        pedido = self.submeter_uc.execute(
            numero             = numero,
            proposta           = proposta,
            diretor_financeiro = diretor_financeiro,
            diretor2           = diretor2,
            observacoes        = observacoes,
        )
        audit(
            self.audit_log,
            utilizador = self.user.username,
            accao      = "pedir_aprovacao",
            detalhe    = (
                f"pedido={numero} "
                f"fornecedor={proposta.fornecedor_id} valor={proposta.valor} "
                f"dir_fin={diretor_financeiro.username} dir2={diretor2.username}"
            ),
        )

    # ── helpers de diretores ──────────────────────────────────────────

    def get_diretor_financeiro(self):
        """Devolve o utilizador com perfil=DirFin.
        Fallback: utilizador actual (self.user), para não bloquear o fluxo."""
        if self.user_repo:
            try:
                resultado = self.user_repo.get_by_perfil("DirFin")
                if resultado:
                    return resultado[0]
            except Exception:
                logger.exception("Erro ao obter diretor financeiro")
        # fallback: utilizador actual
        return self.user

    def get_diretores_para_segundo(self) -> list:
        """Devolve diretores (Dir/DirFin) activos, excluindo o DirFin (reservado para o 1.º slot)."""
        if not self.user_repo:
            return []
        try:
            from core.security import PERFIS_DIRECAO
            todos = []
            for perfil in PERFIS_DIRECAO:
                todos.extend(self.user_repo.get_by_perfil(perfil))
            # excluir quem já está no slot financeiro
            dir_fin = self.get_diretor_financeiro()
            excluir = {dir_fin.username} if dir_fin else set()
            return [u for u in todos if u.username not in excluir]
        except Exception:
            logger.exception("Erro ao obter lista de diretores")
            return []

    def get_user_info(self, username: str):
        """Devolve o objeto user para o username dado, ou None."""
        if not self.user_repo or not username:
            return None
        try:
            return self.user_repo.get_by_username(username)
        except Exception:
            logger.exception(f"Erro ao obter info de utilizador: {username}")
            return None

    def adicionar_anexo(self, pedido_numero: str, path: str) -> None:
        self.pedido_repo.adicionar_anexo(pedido_numero, path)
        audit(self.audit_log, self.user.username,
              "adicionar_anexo", f"pedido={pedido_numero} path={path}")

    def remover_anexo(self, anexo_id: int) -> None:
        self.pedido_repo.remover_anexo(anexo_id)
        audit(self.audit_log, self.user.username,
              "remover_anexo", f"id={anexo_id}")

    def listar_anexos(self, pedido_numero: str) -> list:
        if not self.pedido_repo:
            return []
        return self.pedido_repo.listar_anexos(pedido_numero)

    def get_fornecedores(self):
        try:
            return self.list_fornecedores_uc.execute()
        except Exception as e:
            logger.exception("Erro ao listar fornecedores")
            return []

    def get_mapa_fornecedores(self) -> dict:
        """Devolve dicionário {str(id): nome} para resolução de nomes na GUI."""
        try:
            return {str(f.id): f.nome for f in self.list_fornecedores_uc.execute()}
        except Exception as e:
            logger.exception("Erro ao construir mapa de fornecedores")
            return {}

    def editar_fornecedor(self, dados: dict):
        try:
            self.fornecedor_repo.update(dados)
            audit(
                self.audit_log,
                utilizador=self.user.username,
                accao="editar_fornecedor",
                detalhe=f"id={dados['id']} nome={dados.get('nome','')} nif={dados.get('nif','')}",
            )
            self.gui.informuser("OK", "Fornecedor actualizado com sucesso.")
        except Exception as e:
            logger.exception("Erro ao editar fornecedor")
            raise

    # -------------------------------------------------
    # Encomendas
    # -------------------------------------------------

    def listar_encomendas(self, *estados):
        """Sem estados → todas. estados: 'colocada','recebida','pagar','paga'"""
        try:
            todas = self.encomenda_repo.list_all()
            if not estados:
                return todas
            return [e for e in todas if self._estado_encomenda(e) in estados]
        except Exception:
            logger.exception("Erro ao listar encomendas")
            return []

    def _estado_encomenda(self, e) -> str:
        if e.recebido == "pago":
            return "paga"
        if e.pode_pagar:
            return "pagar"
        if e.recebido == "ok":
            return "recebida"
        return "colocada"

    def receber_encomenda(self, numero: str, resultado: str):
        e = self.encomenda_repo.get_by_numero(numero)
        if not e:
            raise ValueError(f"Encomenda {numero} não encontrada.")
        e.marcar_recebido(resultado == "ok", self.user.username)
        self.encomenda_repo.update(e)
        audit(self.audit_log, self.user.username, "receber_encomenda",
              f"numero={numero} resultado={resultado}")

    def pagar_encomenda(self, numero: str):
        e = self.encomenda_repo.get_by_numero(numero)
        if not e:
            raise ValueError(f"Encomenda {numero} não encontrada.")
        if not e.pode_pagar:
            raise ValueError(f"Encomenda {numero} não está pronta a pagar.")
        e.recebido = "pago"
        from datetime import datetime
        e.log_user = self.user.username
        e.log_data = datetime.now()
        self.encomenda_repo.update(e)
        audit(self.audit_log, self.user.username, "pagar_encomenda", f"numero={numero}")

    def get_faturacao_fornecedor(self, fornecedor_id: int) -> list:
        """
        Agrega faturação anual do fornecedor a partir dos pedidos encomendados/concluídos.
        Devolve lista de {ano, n_pedidos, total}.
        As duas bases de dados são separadas — o join é feito em Python.
        """
        from collections import defaultdict
        try:
            pedidos = self.encomenda_repo.list_by_estado("encomendado", "concluido", "concluído")
            por_ano = defaultdict(lambda: {"n_pedidos": 0, "total": 0.0})
            forn_str = str(fornecedor_id)
            for pedido in pedidos:
                for proposta in (pedido.propostas or []):
                    if str(proposta.fornecedor_id) == forn_str:
                        ano = pedido.data_criacao.year if pedido.data_criacao else 0
                        por_ano[ano]["n_pedidos"] += 1
                        por_ano[ano]["total"]     += float(proposta.valor or 0)
                        break  # cada pedido conta uma vez por fornecedor
            return [
                {"ano": ano, "n_pedidos": d["n_pedidos"], "total": round(d["total"], 2)}
                for ano, d in sorted(por_ano.items(), reverse=True)
            ]
        except Exception:
            logger.exception("Erro ao obter faturação")
            return []
