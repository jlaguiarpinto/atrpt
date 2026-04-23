#atrpt #presentation/associados_gui.py
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from application.email.word_template_loader import carregar_template_word


class AssociadosGUI(tk.Frame):

    def __init__(self, root, controller):
        super().__init__(root)
        self.controller = controller

        self.word_template = None
        self.anexos = None
        self.ficheiro_envio = None

        ttk.Label(self, text="Envio de Emails aos Associados").pack(pady=10)

        frame = ttk.Frame(self)
        frame.pack(pady=10)

        # template
        ttk.Button(
            frame,
            text="Selecionar Template",
            command=self.selecionar_template
        ).grid(row=0, column=0, pady=5, sticky="ew")

        # anexo
        ttk.Button(
            frame,
            text="Selecionar Anexo",
            command=self.selecionar_anexo
        ).grid(row=1, column=0, pady=5, sticky="ew")

        # ficheiro envio
        ttk.Button(
            frame,
            text="Selecionar ficheiro de envio",
            command=self.selecionar_ficheiro_envio
        ).grid(row=2, column=0, pady=5, sticky="ew")

        # enviar
        self.btn = ttk.Button(
            frame,
            text="Enviar Emails",
            command=self.controller.executar_envio
        ).grid(row=3, column=0, pady=5, sticky="ew")

        self.btn.grid(row=3, column=0, pady=15)
        self.txt = tk.Text(self, height=15)
        self.txt.pack(fill="both", expand=True)

    # --------------------------

    def selecionar_template(self):

        path = filedialog.askopenfilename(
            title="Selecionar template Word",
            filetypes=[("Word", "*.docx")]
        )

        if not path:
            return

        subject, html = carregar_template_word(Path(path))

        self.word_template = path
        self.subject_template = subject
        self.html_template = html

        self.log(f"Template carregado: {Path(path).name}")

    # --------------------------

    def selecionar_anexo(self):

        path = filedialog.askopenfilename(
            title="Selecionar anexo",
            filetypes=[("Todos", "*.*")]
        )

        if not path:
            return

        self.anexos = path
        self.log(f"Anexo selecionado: {Path(path).name}")

    # --------------------------

    def selecionar_ficheiro_envio(self):

        path = filedialog.askopenfilename(
            title="Selecionar ficheiro de envio",
            filetypes=[("Excel", "*.xlsx")]
        )

        if not path:
            return

        self.ficheiro_envio = path
        self.log(f"Ficheiro de envio: {Path(path).name}")

    # --------------------------

    def enviar(self):

        if not self.word_template:
            self.log("Selecione um template Word.")
            return

        if not self.ficheiro_envio:
            self.log("Selecione o ficheiro de envio.")
            return

        self.controller.enviar_emails(
            subject=self.subject_template,
            html=self.html_template,
            anexo=self.anexos,
            ficheiro_envio=self.ficheiro_envio
        )

    # --------------------------

    def log(self, msg):
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.root.update_idletasks()

    def set_busy(self, busy):
        self.btn.config(state="disabled" if busy else "normal")

