# atrpt/presentation/associados_email_gui.py

import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
import logging

from presentation.shared.base_gui import BaseGui as BG
logger = logging.getLogger(__name__)

class AssociadosEmailGUI(BG):

    def __init__(self, parent, controller):

        BG.__init__(self, parent, controller)
        controller.email_gui = self

        self.parent = parent
        self.controller = controller

        self.template = None
        self.anexos = []  # Alterado para lista

        self.build()

    def build(self):

        self.set_title("Associados", "Enviar Emails")

        frame = self.parent

        # Frame para seleção de template
        template_frame = tk.LabelFrame(frame, text="Template")
        template_frame.pack(fill="x", padx=20, pady=10)

        btn_template = tk.Button(
            template_frame,
            text="Selecionar Template Word",
            command=self.escolher_template
        )
        btn_template.pack(pady=5)

        # Frame para seleção de anexos
        anexo_frame = tk.LabelFrame(frame, text="Anexos (opcional)")
        anexo_frame.pack(fill="x", padx=20, pady=10)

        btn_anexo = tk.Button(
            anexo_frame,
            text="Selecionar Anexos",
            command=self.escolher_anexo
        )
        btn_anexo.pack(pady=5)

        # Frame para filtros
        filtros = tk.LabelFrame(frame, text="Filtros")
        filtros.pack(fill="x", padx=20, pady=10)

        tk.Label(filtros, text="saldo").grid(row=0, column=0, padx=5, pady=5)

        self.saldo_op = ttk.Combobox(
            filtros,
            values=[">", "<", ">=", "<=", "="],
            width=5
        )
        self.saldo_op.grid(row=0, column=1, padx=5, pady=5)

        self.saldo_val = tk.Entry(filtros, width=8)
        self.saldo_val.grid(row=0, column=2, padx=5, pady=5)

        tk.Label(filtros, text="Idade").grid(row=1, column=0, padx=5, pady=5)

        self.idade_op = ttk.Combobox(
            filtros,
            values=[">", "<", ">=", "<=", "="],
            width=5
        )
        self.idade_op.grid(row=1, column=1, padx=5, pady=5)

        self.idade_val = tk.Entry(filtros, width=8)
        self.idade_val.grid(row=1, column=2, padx=5, pady=5)

        # Botão de envio
        btn = tk.Button(
            frame,
            text="Enviar Emails",
            command=self.enviar_emails,
            bg="green",
            fg="white",
            font=("Arial", 10, "bold")
        )
        btn.pack(pady=20)

        # Área de log
        self.log_text = tk.Text(frame, height=10, width=80)
        self.log_text.pack(fill="both", expand=True, padx=20, pady=10)

    def log(self, mensagem):
        """Método para logging na interface"""
        if hasattr(self, 'log_text'):
            self.log_text.insert("end", mensagem + "\n")
            self.log_text.see("end")
            self.log_text.update_idletasks()

    def escolher_template(self):
        path = filedialog.askopenfilename(
            title="Selecionar Template Word",
            filetypes=[("Word", "*.docx")]
        )

        if not path:
            self.log("Template não selecionado.")
            return

        self.template = path
        self.controller.template = path
        logger.info(f"Template selecionado: {Path(path).name}")
        logger.info(f"Caminho: {path}")

        # atualiza no controller se necessário
        if hasattr(self.controller, 'template'):
            self.controller.template = path

    def escolher_anexo(self):
        paths = filedialog.askopenfilenames(
            title="Selecione um ou mais anexos",
            filetypes=[("Todos os ficheiros", "*.*")]
        )
        
        if paths:
            self.anexos = list(paths)
            quantidade = len(paths)
            nomes_arquivos = [Path(path).name for path in paths]
            
            if quantidade == 1:
                self.log(f"Anexo selecionado: {nomes_arquivos[0]}")
                self.log(f"Caminho: {paths[0]}")
            else:
                self.log(f"{quantidade} anexos selecionados: {', '.join(nomes_arquivos)}")
                for i, path in enumerate(paths, 1):  # <-- NOVO
                    self.log(f"  Anexo {i}: {path}")
        else:
            self.anexos = []
            self.log("Nenhum anexo selecionado.")

    def enviar_emails(self):
        self.controller.enviar()

