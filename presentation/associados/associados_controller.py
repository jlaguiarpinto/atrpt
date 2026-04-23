# atrpt/presentation/associados_controller.py
import threading
from pathlib import Path
import logging
import tkinter as tk
from tkinter import filedialog, messagebox as mb
from presentation.associados.associados_menu_gui import AssociadosMenuGUI
from presentation.associados.associados_email_gui import AssociadosEmailGUI
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
        anexos = filedialog.askopenfilenames(title="Selecione os anexos")                    # ANEXOS    

        if anexos:
            self.anexos = list(anexos)
            nomes = [Path(a).name for a in anexos]
            logger.info(f"✅ Anexos: {', '.join(nomes)}")
        else:
            self.anexos = []
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


        # ------------------------------------------
        # IR PARA GUI DE ENVIO
        # ------------------------------------------
        self.gui.show_view(AssociadosEmailGUI, self)
    
    # ==========================================
    # FASE 2: ANÁLISE (opcional, pode ser chamada da UI)
    # ==========================================
    
    def analisar_mensagens(self):
        """Analisa as mensagens preparadas e mostra preview"""
        if self._mensagens_preparadas is None:
            logger.error("Nenhuma mensagem preparada. Execute preparar_envio primeiro.")
            return
        
        def worker():
            try:
                self._thread_safe_log("🔍 Analisando mensagens...")
                
                analise = self.usecase.analisar(
                    preview_n=5,
                    on_progress=self._thread_safe_log
                )
                
                # Mostrar recomendações
                if analise.recomendacoes:
                    self.root.after(0, lambda: mb.showwarning(
                        "Recomendações",
                        "\n".join(analise.recomendacoes)
                    ))
                
                # Mostrar estatísticas
                self._thread_safe_log(f"\n📊 Estatísticas:")
                self._thread_safe_log(f"   total: {analise.total_mensagens}")
                self._thread_safe_log(f"   Emails únicos: {analise.estatisticas['total_unicos']}")
                self._thread_safe_log(f"   Tamanho médio HTML: {analise.estatisticas['tamanho_medio_html']:.0f} chars")
                
            except Exception as e:
                logger.exception("Erro na análise")
                self._thread_safe_log(f"❌ Erro na análise: {e}")    
        threading.Thread(target=worker, daemon=True).start()
      
    def enviar(self, callback=None):
        """Envia os emails - lê do ficheiro selecionado e envia apenas pendentes"""
        ficheiro = filedialog.askopenfilename(                                             # TEMPLATE     
            title="Template do email",
            filetypes=[("Arquivos Excel", "*.xlsx *.xls")])

        if not ficheiro:
            logger.info("Envio cancelado:  ficheiro não selecionado")
            return

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
        logger.info(msg)
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