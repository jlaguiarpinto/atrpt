#atrpt/presentation/secretaria/controller.py

import tkinter as tk
from tkinter import messagebox
import logging

from presentation.shared.base_gui import BaseGui as BG
from presentation.secretaria.tesouraria_validacao_gui import TesourariaValidacaoGUI
from domain.secretaria.pim_context import PimContext
from application.secretaria.enviar_faturas_usecase import EnviarFaturasPimUseCase
from core.paths import resolver_path_template


logger = logging.getLogger(__name__)

_MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


class SecretariaController:
    def __init__(self, root, user_context, cfg, emailer, pim_repo, residentes_repo, contacorrente_repo, inflow_repo, template_builder):
        self.root = root
        self.user = user_context
        self.cfg = cfg
        self.emailer = emailer        
        self.pim_repo = pim_repo
        self.gui = None
        self.tesouraria = None
        self.residentes_repo = residentes_repo
        self.cc_repo = contacorrente_repo
        self.inflow_repo = inflow_repo
        self.template_builder = template_builder
        self.tesouraria = self._build_tesouraria()
   

    # -----------------------------
    # MÉTODOS DO MENU
    # -----------------------------

    def start(self):
        from .secretaria_gui import SecretariaGUI
        self.gui = SecretariaGUI(self.root, self)
        
    def abrir_tesouraria(self):
        from .tesouraria_view import TesourariaView
        view = TesourariaView(self.gui)
        view.render(self)

    def abrir_pim(self):
        from .farmacia_view import FarmaciaView 
        from datetime import date
        mes = BG.perguntaMes(self.gui)       
        if not mes:
            self.gui.log("Operação cancelada.")
            return
        
        _MESES = [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]  
        mes_idx = int(mes)
        self.mes_faturacao = _MESES[mes_idx]
        self.mes_pagamento = _MESES[1] if mes_idx == 12 else _MESES[mes_idx + 1]
        
        self.mes_str = f"{mes_idx:02d}"
        ano_atual = date.today().year
        ano = ano_atual - 1 if mes_idx == 12 else ano_atual
        self.ano_str = str(ano)

        self._init_pim_contexto()
        view = FarmaciaView(self.gui)
        view.render(self)
    
    def _build_pim(self, ctx):

        from domain.secretaria.pim_service import Pim

        return Pim(
            ctx=ctx,
            residentes_repo=self.residentes_repo,
            conta_corrente_repo=self.cc_repo,
            pim_repo=self.pim_repo,
        )

    def abrir_ponto(self):
        from presentation.secretaria.ponto_controller import PontoController
        from domain.secretaria.ponto_processor import PontoProcessor
        from application.secretaria.processar_ponto_usecase import ProcessarPontoUseCase
        
        usecase = ProcessarPontoUseCase()   #(processor=PontoProcessor())
        controller = PontoController(self.root, self.cfg, usecase)
        self._limpar_area_trabalho()
        controller.start(self.gui)

    def abrir_saldos(self):
        """Abrir módulo de saldos"""
        logging.info("Módulo de saldos - a implementar")
    
    def sair_app(self):
        """Sair da aplicação"""
        self.root.quit()
    
    def _limpar_area_trabalho(self):
        """Limpar a área de trabalho atual"""
        if self.gui and hasattr(self.gui, 'frame_work'):
            for w in self.gui.frame_work.winfo_children():
                w.destroy()

    # -----------------------------
    # TESOURARIA
    # -----------------------------

    def _build_tesouraria(self):

        from application.secretaria.tesouraria_service import TesourariaService

        return TesourariaService(
            paths=self.cfg.paths,
            emailer=self.emailer,
            residentes_repo=self.residentes_repo,
            conta_corrente_repo=self.cc_repo,
            comprovativo_repo=None,  # se não estiveres a usar ainda
            inflow_repo=self.inflow_repo,
            pim_repo=self.pim_repo,
            template_builder=self.template_builder,
            cfg=self.cfg,
            email_secretaria=self.cfg.email_secretaria,
            modo_teste=self.cfg.modo_teste,
        )
    
    def processar_extrato(self):

        resultado = self.tesouraria.processar_extrato(
            pedir_input=self._pedir_input,
            confirmar_adicao=self._confirmar_adicao,
            validar_callback=self._abrir_validacao_tesouraria
        )
        # -------------------------
        # tratamento de estados
        # -------------------------
        if resultado["status"] == "sem_novos":
            logging.info("Informação\nSem novos movimentos.")
            return

        if resultado["status"] == "cancelado":
            logging.info("Operação cancelada pelo utilizador.")
            return

        # -------------------------
        # sucesso
        # -------------------------
        logging.info(
            f"Foram encontrados {resultado['novos']} novos movimentos."
        )

        logging.info(
            "Concluído\nMovimentos aplicados. Recibos preparados para envio posterior."
        )
 
    def _abrir_validacao_tesouraria(self, df_classificado):
        residentes_lookup = self.tesouraria.get_residentes_lookup()
        if "numero_residente" in df_classificado.columns:
            df_classificado["nome"] = (
                df_classificado["numero_residente"]
                .map(residentes_lookup)
                .fillna("")
            )
        gui = TesourariaValidacaoGUI(
                        parent=self.root,
                        df=df_classificado,
                        residentes_lookup=residentes_lookup
            )

        self.root.wait_window(gui)
        return gui.resultado
    
    def _pedir_input(self, titulo, pergunta, tipo, dados_mov=None):

        import tkinter as tk
        from tkinter import ttk

        dialog = tk.Toplevel(self.root)
        dialog.title(titulo)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill="both", expand=True)

        # 🔹 Mostrar dados do movimento se existirem
        if dados_mov:
            ttk.Label(frame, text=f"data: {dados_mov.get('data','')}").pack(anchor="w")
            ttk.Label(frame, text=f"Descricao: {dados_mov.get('descricao','')}").pack(anchor="w")
            ttk.Label(frame, text=f"valor: {dados_mov.get('valor',''):.2f} €").pack(anchor="w")

            if "numero_residente" in dados_mov and dados_mov['numero_residente']:
                ttk.Label(frame, text=f"Num: {dados_mov.get('numero_residente')}").pack(anchor="w")
            if "nome" in dados_mov and dados_mov['nome']:
                ttk.Label(frame, text=f"Nome: {dados_mov.get('nome')}").pack(anchor="w")

            ttk.Separator(frame).pack(fill="x", pady=8)

        ttk.Label(frame, text=pergunta).pack(anchor="w")

        entry = ttk.Entry(frame)
        entry.pack(fill="x")
        entry.focus_set()
        entry.select_range(0, tk.END)

        resultado = {"valor": None}

        def confirmar():
            try:
                if tipo == "int":
                    resultado["valor"] = int(entry.get())
                else:
                    resultado["valor"] = entry.get()
            except ValueError:
                resultado["valor"] = None
            dialog.destroy()

        ttk.Button(frame, text="OK", command=confirmar).pack(pady=10)

        dialog.bind("<Return>", lambda e: confirmar())

        self.root.wait_window(dialog)

        return resultado["valor"] 
    
    def _confirmar_adicao(self,numero, nome, descricao):
        resposta = messagebox.askyesno(
            "Nova Designação Bancária",
            f"Residente: {numero} - {nome}\n\n"
            f"Adicionar nova designação?\n\n"
            f"{descricao}"
        )
        return resposta        
   
    def registar_movimentos(self):                  #Registar um pagamento manual
        import pandas as pd
      
        identificador = self.gui.pedirInput(
            "Registar Pagamento",
            "Nº de Residente ou Nome:"
        )
        
        if not identificador:
            return
        
        # Tentar encontrar residente
        residente = None
        
        # Se for número
        if identificador.isdigit():
            residente = self.tesouraria.residentes_repo.get_by_numero(int(identificador))
        else:
            # Procurar por nome (case insensitive)
            residentes = self.tesouraria.residentes_repo.get_all()
            for res in residentes:
                if identificador.lower() in (res.get("nome") or"").lower:
                    residente = res
                    break
        
        if not residente:
            self.gui.informuser("Erro", f"Residente '{identificador}' não encontrado.")
            return
        
        # Pedir valor
        valor_str = self.gui.pedirInput(
            "Registar Pagamento",
            f"Residente: {residente['numero_residente']} - {residente['nome']}\nvalor do pagamento (€):",
            "float"
        )
        
        if not valor_str:
            return
        
        try:
            valor = float(valor_str)
        except ValueError:
            self.gui.informuser("Erro", "valor inválido.")
            return
        
        # Pedir descrição (opcional)
        descricao = self.gui.pedirInput(
            "Registar Pagamento",
            "Descrição (opcional, Enter para ignorar):"
        ) or "Pagamento manual"
        
        # Criar movimento
        from datetime import datetime
        novo_movimento = pd.DataFrame([{
            "data": datetime.now().strftime("%Y-%m-%d"),
            "descricao": descricao,
            "valor": valor,
            "numero_residente": residente['numero_residente'],
            "nome": residente['nome'],
            "tipo": None,  # será classificado automaticamente
            "copag": residente.get("copag", "")
        }])
        
        # Classificar movimento
        df_classificado = self.tesouraria.classificar_movimentos(
            novo_movimento,
            self._pedir_input,
            self._confirmar_adicao
        )
        
        # Calcular distribuição
        df_calculado = self.tesouraria.calcular_distribuicao(df_classificado)
        
        # atualizar inflow e aplicar efeitos
        self.tesouraria._atualizar_inflow(df_classificado)
        self.tesouraria.aplicar_efeitos_financeiros(df_calculado)
        
        logging.info(f"Pagamento de {valor:.2f}€ registado para {residente['nome']}")
        self.gui.informuser("Sucesso", f"Pagamento de {valor:.2f}€ registado com sucesso.")

    def enviar_recibos(self):
        enviados = self.tesouraria._enviar_recibos()
        logging.info(f"Envio concluído: {enviados} recibos enviados com sucesso." if enviados else "Não existem recibos pendentes de envio.")

    def processar_dd(self):
        if not self.tesouraria.existe_comprovativodd():
            self.gui.informuser(
                "Débitos Diretos",
                "Não foi encontrado o ficheiro de comprovativo DD."
            )
            return

        atualizar = self.gui.ask_yes_no(
            "atualizar PIM",
            "Pretende atualizar o ficheiro PIM?"
        )

        enviar = self.gui.ask_yes_no(
            "Enviar emails",
            "Pretende enviar os comprovativos por email?"
        )
        n = self.tesouraria.processar_dd(
            atualizar_pim=atualizar,
            enviar_emails=enviar
        )
        self.gui.informuser(
            "Débitos Diretos",
            f"{n} pagamentos processados."
        )
    
    def abrir_dd(self):
        from presentation.secretaria.debitodireto_gui import DebitoDiretoGUI
        DebitoDiretoGUI(self.root, self)

    def produzir_dd(self):

        path = self.tesouraria.produzir_dd()

        logging.info(f"Débitos Diretos\nFicheiro produzido:\n\n{path}")

    # -----------------------------
    # PIM
    # -----------------------------

    def _init_pim_contexto(self):

        from datetime import date
        from infrastructure.persistence.faturacao_residentes_repository import FaturacaoResidentesRepository



        self.ctx = self._criar_pim_context(self.ano_str, self.mes_str)

        self.pim = self._build_pim(self.ctx)
        self.faturacao_repo = FaturacaoResidentesRepository(
                            self.ctx.faturacao_residentes_file)
        self.envio_faturas_repo = FaturacaoResidentesRepository(self.ctx.envio_faturas_file)

        self.pim.construir_tabela_residentes()
        self.pim.nif_to_residente = self.pim.tabela_nif_residente.set_index("NIF")
        self.enviar_faturas_usecase = EnviarFaturasPimUseCase(
                                                                emailer=self.emailer,
                                                                ctx=self.ctx,
                                                                faturacao_repo=self.faturacao_repo,
                                                                envio_faturas_repo=self.envio_faturas_repo,
                                                                logger=logging.getLogger("EnviarFaturasPimUseCase")
                                                            )

    def processar_faturacao(self):
        logging.info("A ler faturas...")
        pdf_faturas=self.pim.ler_faturas_pdf()
        n_faturas = len(pdf_faturas)
        logging.info(f"Lidas {n_faturas} faturas.")        
        logging.info("A agregar por residente...")
        faturacao_residentes=self.pim.agregar_por_residente()
        n_residentes = len(faturacao_residentes)
        logging.info(f"Lida faturação de {n_residentes} residentes.")
        logging.info("A ler resumo CSAG...")
        self.pim.ler_resumo_csag(self.ctx)
        logging.info("A comparar totais...")
        diferencas = self.pim.comparar_csag()
        if diferencas is not None and not diferencas.empty:
            self.gui.mostrar_dataframe(
                "Diferenças entre PDFs e resumo CSAG",
                diferencas
            )
        self.residentes_faturacao = self.pim.juntar_dados_residente(faturacao_residentes)
        return diferencas
 
    def produzir_pim(self):
        logging.info("A produzir o novo PIM...")
        self.pim.construir_novo_pim()
        return

    def preparar_faturas(self):
        logging.info("A preparar emails para envio...")
        preparados = self.enviar_faturas_usecase.preparar(self.mes_faturacao, self.mes_pagamento)
        total = preparados.get("total", 0)
        self.gui.informuser(
            "Preparação de faturas",
            f"{total} emails preparados para envio."
        )

    def enviar_faturas(self):
        resultado = self.enviar_faturas_usecase.enviar(
            on_progress=lambda msg: self.gui.log(msg)
        )
        self.gui.informuser(
            "Envio de faturas",
            f"Enviados: {resultado.get('enviados', 0)} | Erros: {resultado.get('erros', 0)}"
        )

    def _criar_pim_context(self,ano,mes):
        params = {
        'ano': ano,
        'mes': mes
        }
        pim_mensal_dir = resolver_path_template(self.cfg,"pim_mensal_dir", ano=ano, mes=mes)
        pim_mensal_dir.mkdir(parents=True, exist_ok=True)
        params['pim_mensal_dir'] = str(pim_mensal_dir)
        
        return PimContext(
                        ano=ano,
                        mes=mes,
                        modo_teste=self.cfg.modo_teste,
                        email_teste=self.cfg.email_teste,
                        pim_file=self.pim_repo,
                        pim_mensal_dir=pim_mensal_dir,
                        csag_file=resolver_path_template(self.cfg,"csag_file", **params),
                        # Todos os templates agora têm pim_mensal_dir disponível
                        pim_mensal_file=resolver_path_template(self.cfg, "pim_mensal_file", **params),
                        pdf_faturas=resolver_path_template(self.cfg, "pdf_faturas", **params),
                        faturacao_residentes_file=resolver_path_template(self.cfg, "faturacao_residentes", **params),
                        # outputs
                        diferencas_file=resolver_path_template(self.cfg, "diferencas_file", **params),
                        envio_faturas_file = pim_mensal_dir / "envio_faturas.xlsx",
                        template_email=str(self.cfg.paths_app["template_enviofat"]) 
                        )

    def _build_main_menu(self):
        self.gui.build_menu_buttons([
            ("Tesouraria", self.abrir_tesouraria),
            ("PIM", self.abrir_pim),
            ("Ponto", self.abrir_ponto),
            ("Fechar", self.gui.hide_menu),
        ])

    def _build_home(self):

        parent = self.gui.abrir_work_area()
        frame = tk.Frame(parent, bg=self.gui.BG)
        frame.pack(fill="x", anchor="n")
        frame.config(bg="blue")

        tk.Label(
            frame,
            text="Selecione uma opção no menu",
            font=self.gui.FONT_SUB,
            bg=self.gui.BG,
            fg=self.gui.FG
        ).pack(anchor="w", padx=10, pady=10)

    def voltar_menu(self):
        self.gui.frame_menu.pack(fill="x", pady=5)
        self.start()

