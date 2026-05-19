# atrpt/presentation/associados_controller.py
import threading
from pathlib import Path
import logging
import tkinter as tk
from tkinter import filedialog, messagebox as mb
from presentation.associados.associados_menu_gui import AssociadosMenuGUI
from application.shared.aplicar_filtros import aplicar_filtros
from application.associados.enviar_emails_usecase import EnviarEmailsAssociadosUseCase  # NOVO use case

logger = logging.getLogger(__name__)

class AssociadosController:

    def __init__(self, root, container, user_context):
        self.root = root
        self.container = container
        self.user_context = user_context
        self.template = None
        self.anexos = []
        self.email_gui = None
        self.df_envio = None
        self.ficheiro_envio = None
        self.envio_file = None
        self.repo_associados = container.associados
        self.emailer = container.email_sender
        self.email_sender = container.email_sender
        self.usecase = container.usecase       
        self.ficheiro_envio = None
        self.gui = None
        self._mensagens_preparadas = None

    def start(self):
        self.gui = AssociadosMenuGUI(self.root, self)
    
    # ==========================================
    # MÉTODO PRINCIPAL - ABRIR ENVIO DE EMAILS
    # ==========================================
    
    def preparar_envio(self):

        template = filedialog.askopenfilename(                                             # TEMPLATE     
            title="Template do email",
            filetypes=[("Word", "*.docx")])

        if not template:
            logger.info("Envio cancelado: template não selecionado")
            return

        self.template = Path(template)
        logger.info(f"✅ Template selecionado: {self.template.name}")

        # ------------------------------------------

        # ------------------------------------------
        self.anexos = []
        while True:
            anexo = filedialog.askopenfilename(title="Selecione um anexo (cancelar para terminar)")
            if not anexo:
                break
            self.anexos.append(anexo)
            logger.info(f"✅ Anexo: {Path(anexo).name}")
            if not mb.askyesno("Anexos", "Anexar mais um ficheiro?"):
                break
        if self.anexos:
            logger.info(f"✅ Anexos: {', '.join(Path(a).name for a in self.anexos)}")
        else:
            logger.info("ℹ️ Sem anexos")

        ficheiro_associados = filedialog.askopenfilename(                                   # FICHEIRO DE ASSOCIADOS
            title="Ficheiro de Associados",
            filetypes=[("Excel", "*.xlsx *.xls")]
        )

        if not ficheiro_associados:
            logger.info("Envio cancelado: ficheiro não selecionado")
            return

        if hasattr(self.repo_associados, "associados_file"):
            self.repo_associados.associados_file = Path(ficheiro_associados)

        logger.info(f"📄 Ficheiro: {Path(ficheiro_associados).name}")

        # ------------------------------------------
        # PREPARAR DADOS
        # ------------------------------------------

        resultado = self.usecase.preparar(
            template_path=str(self.template),
            anexos = self.anexos)
        self.ficheiro_envio = Path(resultado["ficheiro_envio"])
        logger.info(f"✅ Ficheiro criado: {self.ficheiro_envio.name}")
        total = resultado.get("total")
        logger.info(f"✅ {total} mensagens preparadas")

        total = self._excluir_duplicados(total)

        if mb.askyesno("Destinatários", f"{total} destinatários preparados.\nDeseja excluir algum manualmente?"):
            total = self._dialogo_excluir_destinatarios(total)

        # logs passam pelo txt_output do BaseGui (gui raiz)
        self.email_gui = self.gui

        resumo = (
            f"Ficheiro: {self.ficheiro_envio.name}\n"
            f"Destinatários prontos para envio: {total}"
        )
        self.gui.mostrar_resumo_envio(resumo)
        self.root.after(300, self.analisar_mensagens)

    # ==========================================
    # EXCLUSÃO DE DESTINATÁRIOS
    # ==========================================

    def _excluir_duplicados(self, total_atual: int) -> int:
        import pandas as pd

        df = pd.read_excel(self.ficheiro_envio)
        duplicados = df[df.duplicated(subset=["email"], keep=False)]

        if duplicados.empty:
            return total_atual

        n_dup = df.duplicated(subset=["email"], keep="first").sum()
        resposta = mb.askyesno(
            "Emails repetidos",
            f"Existem {n_dup} registo(s) com email duplicado.\nExcluir duplicados?"
        )
        if resposta:
            df = df.drop_duplicates(subset=["email"], keep="first")
            df.to_excel(self.ficheiro_envio, index=False)
            logger.info(f"✅ {n_dup} duplicado(s) removido(s). Restam {len(df)} destinatários.")
            return len(df)

        return total_atual

    def _dialogo_excluir_destinatarios(self, total_atual: int) -> int:
        import tkinter as tk
        import pandas as pd

        df = pd.read_excel(self.ficheiro_envio)
        if "email" not in df.columns or "nome" not in df.columns:
            mb.showwarning("Aviso", "Ficheiro sem colunas 'email'/'nome'.")
            return total_atual

        win = tk.Toplevel(self.root)
        win.title("Excluir destinatários")
        win.geometry("540x520")
        win.transient(self.root)
        win.grab_set()
        win.focus_force()

        tk.Label(win, text="Pesquisar:", font="Verdana 10").pack(anchor="w", padx=12, pady=(10, 0))
        pesquisa_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=pesquisa_var, font="Verdana 10", width=50)
        entry.pack(padx=12, pady=(2, 6))
        entry.focus_set()

        frame_lista = tk.Frame(win)
        frame_lista.pack(fill="both", expand=True, padx=12)

        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            frame_lista, selectmode="multiple",
            yscrollcommand=scrollbar.set,
            font="Courier 9", width=70, height=22,
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        registos = list(zip(df["nome"].fillna(""), df["email"].fillna("")))

        def _preencher(filtro=""):
            listbox.delete(0, tk.END)
            filtro = filtro.lower()
            for nome, email in registos:
                if filtro in nome.lower() or filtro in email.lower():
                    listbox.insert(tk.END, f"{nome:<30}  {email}")

        _preencher()
        pesquisa_var.trace_add("write", lambda *_: _preencher(pesquisa_var.get()))

        resultado = {"excluidos": []}

        def _confirmar():
            selecionados = listbox.curselection()
            filtro = pesquisa_var.get().lower()
            visiveis = [
                (n, e) for n, e in registos
                if filtro in n.lower() or filtro in e.lower()
            ]
            resultado["excluidos"] = [visiveis[i][1] for i in selecionados]
            win.destroy()

        frame_btns = tk.Frame(win)
        frame_btns.pack(pady=8)
        tk.Button(frame_btns, text="Excluir selecionados", command=_confirmar,
                  bg="#F1E2CF", font="Verdana 10 bold").pack(side="left", padx=10)
        tk.Button(frame_btns, text="Não excluir nenhum", command=win.destroy,
                  font="Verdana 10").pack(side="left", padx=10)

        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.wait_window()

        emails_excluir = resultado["excluidos"]
        if emails_excluir:
            df_filtrado = df[~df["email"].isin(emails_excluir)]
            df_filtrado.to_excel(self.ficheiro_envio, index=False)
            restantes = len(df_filtrado)
            logger.info(f"✅ {len(emails_excluir)} excluído(s). Restam {restantes} destinatários.")
            return restantes
        else:
            logger.info("ℹ️ Nenhum destinatário excluído.")
            return total_atual

    # ==========================================
    # FASE 2: ANÁLISE (opcional, pode ser chamada da UI)
    # ==========================================
    
    def analisar_mensagens(self):
        """Analisa as mensagens preparadas e mostra preview"""
        if not self.ficheiro_envio or not Path(self.ficheiro_envio).exists():
            logger.error("Nenhum ficheiro preparado. Execute 'Preparar' primeiro.")
            mb.showerror("Erro", "Nenhum ficheiro preparado.\nExecute 'Preparar' primeiro.")
            return

        def worker():
            try:
                self._thread_safe_log("🔍 Analisando mensagens...")

                analise = self.usecase.analisar(
                    ficheiro_envio=str(self.ficheiro_envio),
                    preview_n=5,
                )
                
                self._thread_safe_log(f"\n📊 Estatísticas:")
                self._thread_safe_log(f"   Total: {analise.get('total', 0)}")
                self._thread_safe_log(f"   Válidos: {analise.get('validos', 0)}")
                self._thread_safe_log(f"   Inválidos: {analise.get('invalidos', 0)}")
                self._thread_safe_log(f"   A enviar: {analise.get('a_enviar', analise.get('validos', 0))}")
                
            except Exception as e:
                logger.exception("Erro na análise")
                self._thread_safe_log(f"❌ Erro na análise: {e}")    
        threading.Thread(target=worker, daemon=True).start()
      
    def enviar(self, callback=None):
        """Envia os emails a partir do ficheiro preparado em preparar_envio."""
        if not self.ficheiro_envio or not Path(self.ficheiro_envio).exists():
            logger.error("Nenhum ficheiro de envio preparado. Execute 'Preparar' primeiro.")
            mb.showerror("Erro", "Nenhum ficheiro de envio preparado.\nExecute 'Preparar' primeiro.")
            return

        ficheiro = str(self.ficheiro_envio)
        logger.info("📧 Iniciando envio de emails...")

        resultado = self.usecase.enviar(ficheiro, on_progress=self._thread_safe_log)
        
        if resultado is None:
            resultado = {"status": "erro", "mensagem": "Resultado vazio do usecase"}
            
        if resultado.get("status") == "concluido":
            logger.info(f"✅ Enviados: {resultado.get('enviados', 0)} | Erros: {resultado.get('erros', 0)}")
        
        # Chamar callback com o resultado
        if callback:
            callback(resultado)
        
        return resultado

    def retomar_envio(self):
        """Retoma um envio anterior, enviando apenas os registos ainda por enviar."""
        import pandas as pd

        pasta_padrao = self.usecase.envio_repository.base_dir
        ficheiro = filedialog.askopenfilename(
            title="Selecionar ficheiro de envio para retomar",
            initialdir=str(pasta_padrao) if pasta_padrao.exists() else ".",
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if not ficheiro:
            return

        try:
            df = pd.read_excel(ficheiro)
        except Exception as e:
            mb.showerror("Erro", f"Não foi possível abrir o ficheiro:\n{e}")
            return

        if "data_envio" not in df.columns:
            mb.showerror(
                "Ficheiro inválido",
                "O ficheiro selecionado não contém a coluna 'data_envio'.\n"
                "Selecione um ficheiro de envio gerado por esta aplicação.",
            )
            return

        total = len(df)
        enviados = df["data_envio"].notna().sum()
        por_enviar = total - enviados

        if por_enviar == 0:
            mb.showinfo(
                "Envio já completo",
                f"Todos os {total} registos já foram enviados.\nNão há nada a retomar.",
            )
            return

        erros = 0
        if "status_envio" in df.columns:
            erros = (df["status_envio"].str.upper() == "ERRO").sum()

        resumo_stats = (
            f"Total de registos: {total}\n"
            f"Já enviados (OK):  {enviados}\n"
            f"Com erro:          {erros}\n"
            f"Por enviar:        {por_enviar}"
        )

        if not mb.askyesno(
            "Retomar envio",
            f"Ficheiro: {Path(ficheiro).name}\n\n{resumo_stats}\n\n"
            "Deseja retomar o envio dos registos em falta?",
        ):
            return

        self.ficheiro_envio = Path(ficheiro)
        self.email_gui = self.gui

        resumo_ui = (
            f"Ficheiro: {Path(ficheiro).name}\n"
            f"Destinatários por enviar: {por_enviar} (de {total})"
        )
        self.gui.mostrar_resumo_envio(resumo_ui)

        self._thread_safe_log(f"Ficheiro: {Path(ficheiro).name}")
        self._thread_safe_log(resumo_stats.replace("\n", " | "))
        self._thread_safe_log("A iniciar envio...")

        def worker():
            try:
                resultado = self.usecase.enviar(
                    str(self.ficheiro_envio),
                    on_progress=self._thread_safe_log,
                )
                if resultado is None:
                    resultado = {"status": "erro", "mensagem": "Resultado vazio do usecase"}

                if resultado.get("status") == "concluido":
                    logger.info(
                        "✅ Enviados: %s | Erros: %s",
                        resultado.get("enviados", 0),
                        resultado.get("erros", 0),
                    )
                    self.root.after(0, lambda: mb.showinfo(
                        "Envio concluído",
                        f"Enviados: {resultado.get('enviados', 0)}\n"
                        f"Erros:    {resultado.get('erros', 0)}",
                    ))
                else:
                    msg = resultado.get("mensagem", "Erro desconhecido")
                    self.root.after(0, lambda: mb.showerror("Erro no envio", msg))

            except Exception as e:
                logger.exception("Erro ao retomar envio")
                self.root.after(0, lambda: mb.showerror("Erro no envio", str(e)))

        threading.Thread(target=worker, daemon=True).start()

            # ==========================================
            # MÉTODOS DE SUPORTE (mantidos da sua versão)
            # ==========================================
        
    def _aplicar_filtros_se_existir(self):
        """Aplica filtros se a GUI de filtros existir"""
        if self.email_gui is None:
            return self._mensagens_preparadas
        
        saldo_op = self.email_gui.saldo_op.get() if hasattr(self.email_gui, 'saldo_op') else ""
        saldo_val = self.email_gui.saldo_val.get() if hasattr(self.email_gui, 'saldo_val') else ""
        idade_op = self.email_gui.idade_op.get() if hasattr(self.email_gui, 'idade_op') else ""
        idade_val = self.email_gui.idade_val.get() if hasattr(self.email_gui, 'idade_val') else ""
        
        filtros = []
        if saldo_val:
            filtros.append(("saldo", saldo_op, float(saldo_val)))
        if idade_val:
            filtros.append(("idade", idade_op, int(idade_val)))
        
        if filtros:
            df_filtrado = aplicar_filtros(self._mensagens_preparadas, filtros)
            logger.info(f"Após filtros: {len(df_filtrado)} associados")
            return df_filtrado
        
        return self._mensagens_preparadas
    
    def _thread_safe_log(self, msg: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        def update_ui():
            if hasattr(self, 'email_gui') and self.email_gui:
                if hasattr(self.email_gui, 'log'):
                    self.email_gui.log(f"[{timestamp}] {msg}")
                elif hasattr(self.email_gui, 'log_text'):
                    self.email_gui.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
                    self.email_gui.log_text.see(tk.END)
                    self.email_gui.log_text.update_idletasks()    
        self.root.after(0, update_ui)
    
    def _envio_terminado(self, resultado):
        # ==========================================
        # RESTAURAR SUSPENSÃO DO SISTEMA
        # ==========================================
        import ctypes
        import sys
        
        if sys.platform == "win32":
            try:
                # Restaurar estado normal (apenas contínuo, sem impedir suspensão)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                self._thread_safe_log("💤 Suspensão do sistema restaurada")
            except Exception as e:
                pass

        """Callback quando o envio termina"""
        logging.info(
            "Envio terminado | total=%s | Enviados=%s | Erros=%s",
            resultado.get("total", 0),
            resultado.get("enviados", 0),
            resultado.get("erros", 0)
        )
        
        self._thread_safe_log(f"\n--- ENVIO CONCLUÍDO ---")
        self._thread_safe_log(f"total: {resultado.get('total', 0)}")
        self._thread_safe_log(f"Enviados: {resultado.get('enviados', 0)}")
        self._thread_safe_log(f"Erros: {resultado.get('erros', 0)}")
        self._thread_safe_log(f"Log: {resultado.get('log_file', 'N/A')}")
        
        if mb.askyesno("Envio Concluído", "Deseja voltar ao menu principal?"):
            self.voltar_menu()
    
    def voltar_menu(self):
        """Limpa estado e volta ao menu"""
        self.email_gui = None
        self.template = None
        self.anexos = []
        self.df_envio = None
        self.ficheiro_envio = None
        self._mensagens_preparadas = None
        self._assunto_log = None
        
        for w in self.root.winfo_children():
            w.destroy()
        
        self.start()
    
    def preparar_filtro_envio(self, saldo_op=None, saldo_val=None, idade_op=None, idade_val=None):
        """Prepara envio com filtros (mantido da sua versão)"""
        filtros = []
        if saldo_val:
            filtros.append(("saldo", saldo_op, float(saldo_val)))
        if idade_val:
            filtros.append(("idade", idade_op, int(idade_val)))

        df_filtrado = aplicar_filtros(self.df_envio, filtros)
        ficheiro = self.usecase.guardar_envio(
            df_filtrado,
            self.template.stem + "_filtrado"
        )

        logger.info(f"Associados selecionados: {len(df_filtrado)}")
        logger.info(f"Ficheiro criado: {ficheiro}")
    
    def filtrar_envio(self):
        if self.email_gui is None:
            logging.info("Janela de envio não inicializada.")
            return     
        saldo_op = self.email_gui.saldo_op.get()
        saldo_val = self.email_gui.saldo_val.get()
        idade_op = self.email_gui.idade_op.get()
        idade_val = self.email_gui.idade_val.get()
        filtros = []
        if saldo_val: filtros.append(("saldo", saldo_op, float(saldo_val)))
        if idade_val: filtros.append(("idade", idade_op, int(idade_val)))
        df_filtrado = aplicar_filtros(self.df_envio, filtros)
        logger.info(f"Associados selecionados: {len(df_filtrado)}")
          
    def processar_quotas(self):
        from tkinter import messagebox
        messagebox.showinfo("Associados", "Processamento de quotas ainda não implementado.")

    def relatorios(self):
        from tkinter import messagebox
        messagebox.showinfo("Associados", "Relatórios ainda não implementados.")
    
    def obter_template(self):
        return self.template

    def obter_anexos(self):
        return self.anexos