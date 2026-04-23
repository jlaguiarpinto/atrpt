# atrpt/presentation/associados/associados_envio_submenu.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import logging
from presentation.shared.base_gui import BaseGui
import pandas as pd
import threading

logger = logging.getLogger(__name__)


class AssociadosEnvioSubmenu(BaseGui):
    
    def __init__(self, parent, controller, menu_gui):
        self.menu_gui = menu_gui
        BaseGui.__init__(self, parent, controller)
        self.controller = controller
        self.ficheiro_base = None      # Ficheiro de associados (para preparar)
        self.ficheiro_envio = None     # Ficheiro de envio (para enviar)
        self.enviando = False
        self.build_ui()
    
    def build_ui(self):
        # Limpar área de trabalho
        for w in self.frame_work.winfo_children():
            w.destroy()
        
        # Limpar menu (friso) e criar novo com as opções
        for w in self.frame_menu.winfo_children():
            w.destroy()
        
        # Criar friso horizontal com os 3 botões
        btn_frame = tk.Frame(self.frame_menu, bg=self.BG)
        btn_frame.pack(pady=5)
        
        tk.Button(
            btn_frame,
            text="Preparar",
            command=self.preparar_envio,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            width=15
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame,
            text="Analisar",
            command=self.analisar_mensagens,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            width=15
        ).pack(side="left", padx=10)
        
        tk.Button(
            btn_frame,
            text="Enviar",
            command=self.enviar_emails,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            width=15
        ).pack(side="left", padx=10)
        
        # Área de trabalho
        main_frame = tk.Frame(self.frame_work, bg=self.BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        tk.Label(
            main_frame,
            text="Envio de Emails",
            font=self.FONT_TITLE,
            fg=self.FG,
            bg=self.BG
        ).pack(pady=(0, 20))
        
        # Botão voltar
        tk.Button(
            main_frame,
            text="← Voltar ao Menu Principal",
            command=self.voltar_menu,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG
        ).pack(anchor="nw", pady=(0, 20))
        
        # -------------------------------------------------
        # SEÇÃO: Ficheiro Base (para preparar)
        # -------------------------------------------------
        frame_base = tk.LabelFrame(main_frame, text="Ficheiro Base (Associados)", bg=self.BG, fg=self.FG)
        frame_base.pack(fill="x", pady=10)
        
        self.label_base = tk.Label(
            frame_base,
            text="Nenhum ficheiro selecionado",
            fg="gray",
            bg=self.BG
        )
        self.label_base.pack(pady=5)
        
        tk.Button(
            frame_base,
            text="Selecionar Ficheiro Base",
            command=self.selecionar_ficheiro_base,
            bg=self.BTN_BG
        ).pack(pady=5)
        
        # -------------------------------------------------
        # SEÇÃO: Ficheiro de Envio (para enviar)
        # -------------------------------------------------
        frame_envio = tk.LabelFrame(main_frame, text="Ficheiro de Envio (Preparado)", bg=self.BG, fg=self.FG)
        frame_envio.pack(fill="x", pady=10)
        
        self.label_envio = tk.Label(
            frame_envio,
            text="Nenhum ficheiro selecionado",
            fg="gray",
            bg=self.BG
        )
        self.label_envio.pack(pady=5)
        
        tk.Button(
            frame_envio,
            text="Selecionar Ficheiro de Envio",
            command=self.selecionar_ficheiro_envio,
            bg=self.BTN_BG
        ).pack(pady=5)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)
        self.progress.pack_forget()
        
        # Área de log
        log_frame = tk.LabelFrame(main_frame, text="Log", bg=self.BG, fg=self.FG)
        log_frame.pack(fill="both", expand=True, pady=10)
        
        self.log_text = tk.Text(
            log_frame,
            height=12,
            bg="black",
            fg="white",
            wrap="word"
        )
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)
        
        tk.Button(
            log_frame,
            text="Limpar Log",
            command=self.limpar_log,
            bg=self.BTN_BG
        ).pack(side="bottom", pady=5)
    
    def log(self, msg):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        logger.info(msg)
    
    def limpar_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def selecionar_ficheiro_base(self):
        """Seleciona o ficheiro Excel base com os dados dos associados"""
        path = filedialog.askopenfilename(
            title="Selecionar Ficheiro Base de Associados",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        
        if path:
            self.ficheiro_base = Path(path)
            self.label_base.config(text=self.ficheiro_base.name, fg="green")
            self.log(f"✅ Ficheiro base selecionado: {self.ficheiro_base.name}")
            
            # Atualizar no repositório
            if hasattr(self.controller.repo_associados, "associados_file"):
                self.controller.repo_associados.associados_file = self.ficheiro_base
            
            try:
                df = pd.read_excel(self.ficheiro_base)
                self.log(f"📊 Total de registos: {len(df)}")
            except Exception as e:
                self.log(f"⚠️ Erro: {e}")
    
    def selecionar_ficheiro_envio(self):
        """Seleciona o ficheiro de envio já preparado"""
        path = filedialog.askopenfilename(
            title="Selecionar Ficheiro de Envio",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        
        if path:
            self.ficheiro_envio = Path(path)
            self.label_envio.config(text=self.ficheiro_envio.name, fg="green")
            self.controller.ficheiro_envio = self.ficheiro_envio
            self.log(f"✅ Ficheiro de envio selecionado: {self.ficheiro_envio.name}")
            
            try:
                df = pd.read_excel(self.ficheiro_envio)
                if 'data_envio' in df.columns:
                    pendentes = df[df['data_envio'].isna() | (df['data_envio'] == '')].shape[0]
                    self.log(f"📊 Total: {len(df)} | Pendentes: {pendentes}")
                else:
                    self.log(f"📊 Total: {len(df)} mensagens")
            except Exception as e:
                self.log(f"⚠️ Erro: {e}")
    
    def preparar_envio(self):  #cria ficheiro de envio a partir do ficheiro base, template e anexos
        ficheiro = filedialog.askopenfilename(
            title="Selecionar ficheiro de associados",
            filetypes=[("Excel", "*.xlsx *.xls")])
        if not ficheiro:
            logger.info("❌ Preparação cancelada (sem ficheiro base)")
            return
        self.ficheiro_base = Path(ficheiro)
        self.controller.repo_associados.associados_file = self.ficheiro_base
        self.log(f"📊 Ficheiro base: {self.ficheiro_base.name}")

        template = filedialog.askopenfilename(
            title="Selecionar Template Word",
            filetypes=[("Word", "*.docx")])
        if not template:
            self.log("❌ Preparação cancelada")
            return
        
        anexos = filedialog.askopenfilenames(title="Selecionar Anexos (opcional)")
        
        self.controller.template = Path(template)
        self.controller.anexos = list(anexos) if anexos else []
        
        self.log(f"📄 Template: {Path(template).name}")
        if self.controller.anexos:
            self.log(f"📎 Anexos: {len(self.controller.anexos)}")
        
        resultado = self.controller.preparar_envio()
        
        if resultado and resultado.get("status") == "ok":
            self.ficheiro_envio = self.controller.ficheiro_envio
            self.label_envio.config(text=self.ficheiro_envio.name, fg="green")
            self.log(f"✅ Ficheiro de envio criado: {self.ficheiro_envio.name}")
            self.log(f"📊 Total: {resultado.get('total', 0)} mensagens")
    
    def analisar_mensagens(self):
        """Analisa o ficheiro de envio selecionado"""
        
        if not self.ficheiro_envio:
            self.log("❌ Nenhum ficheiro de envio selecionado")
            resposta = messagebox.askyesno("Aviso", "Selecionar ficheiro de envio para analisar?")
            if resposta:
                self.selecionar_ficheiro_envio()
            return
        
        try:
            df = pd.read_excel(self.ficheiro_envio)
            self.log(f"\n📊 Análise: {self.ficheiro_envio.name}")
            self.log(f"   Total: {len(df)} mensagens")
            
            if 'email' in df.columns:
                self.log(f"   Emails únicos: {df['email'].nunique()}")
            
            if 'data_envio' in df.columns:
                pendentes = df[df['data_envio'].isna() | (df['data_envio'] == '')].shape[0]
                self.log(f"   Pendentes: {pendentes}")
                self.log(f"   Enviados: {len(df) - pendentes}")
            
            self.log("✅ Análise concluída")
            
        except Exception as e:
            self.log(f"❌ Erro: {e}")
    
    def enviar_emails(self):
        """Envia emails pendentes do ficheiro de envio selecionado"""
        
        if not self.ficheiro_envio:
            self.log("❌ Nenhum ficheiro de envio selecionado")
            resposta = messagebox.askyesno("Aviso", "Deseja selecionar um ficheiro de envio?")
            if not resposta:
                return
            self.selecionar_ficheiro_envio()
            if not self.ficheiro_envio:
                return
        
        try:
            df = pd.read_excel(self.ficheiro_envio)
            
            # Filtrar pendentes
            if 'data_envio' in df.columns:
                df_pendentes = df[df['data_envio'].isna() | (df['data_envio'] == '')].copy()
                ja_enviados = len(df) - len(df_pendentes)
                
                if len(df_pendentes) == 0:
                    self.log("✅ Nenhum email pendente")
                    messagebox.showinfo("Info", "Todos os emails já foram enviados!")
                    return
                
                self.log(f"📊 {ja_enviados} já enviados, {len(df_pendentes)} pendentes")
            else:
                df_pendentes = df.copy()
                self.log(f"📊 Total: {len(df_pendentes)} emails")
            
            # Confirmar envio
            if not messagebox.askyesno("Confirmar Envio", f"Enviar {len(df_pendentes)} emails?\n\nFicheiro: {self.ficheiro_envio.name}"):
                self.log("❌ Envio cancelado")
                return
            
            self.progress.pack(pady=10)
            self.progress['value'] = 0
            
            self.log("🚀 Iniciando envio...")
            
            # Executar envio em thread
            def executar():
                try:
                    # Chamar diretamente o usecase com os parâmetros
                    resultado = self.controller.usecase.enviar_emails(
                        df_envio=df_pendentes,
                        ficheiro_envio=str(self.ficheiro_envio),
                        anexo_paths=self.controller.anexos if hasattr(self.controller, 'anexos') else [],
                        on_progress=self.log
                    )
                    self.root.after(0, lambda: self._finalizar_envio(resultado))
                except Exception as e:
                    self.root.after(0, lambda: self._erro_envio(str(e)))
            
            thread = threading.Thread(target=executar, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
            self.progress.pack_forget()

    def _finalizar_envio(self, resultado):
        """Callback chamado quando o envio termina"""
        self.progress.pack_forget()
        
        if resultado is None:
            self.log("❌ Erro: Resultado None")
            messagebox.showerror("Erro", "Erro no envio: resultado vazio")
            return
        
        if resultado.get("status") == "concluido":
            self.log(f"\n✅ ENVIO CONCLUÍDO")
            self.log(f"   Enviados: {resultado.get('enviados', 0)}")
            self.log(f"   Erros: {resultado.get('erros', 0)}")
            
            # Atualizar informações do ficheiro
            try:
                df = pd.read_excel(self.ficheiro_envio)
                if 'data_envio' in df.columns:
                    pendentes = df[df['data_envio'].isna() | (df['data_envio'] == '')].shape[0]
                    self.log(f"📊 Restam pendentes: {pendentes}")
            except:
                pass
            
            messagebox.showinfo(
                "Envio Concluído",
                f"Envio finalizado!\n\n"
                f"Enviados: {resultado.get('enviados', 0)}\n"
                f"Erros: {resultado.get('erros', 0)}"
            )
        else:
            erro_msg = resultado.get('mensagem', 'Erro desconhecido')
            self.log(f"❌ Erro: {erro_msg}")
            messagebox.showerror("Erro", f"Erro no envio:\n{erro_msg}")

    def _erro_envio(self, erro):
        """Trata erro no envio"""
        self.progress.pack_forget()
        self.log(f"❌ Erro: {erro}")
        messagebox.showerror("Erro", f"Erro no envio:\n{erro}")
    
    def voltar_menu(self):
        # Limpar menu e restaurar
        for w in self.frame_menu.winfo_children():
            w.destroy()
        
        # Limpar área de trabalho
        for w in self.frame_work.winfo_children():
            w.destroy()
        
        # Recriar menu principal
        self.menu_gui.build_ui()