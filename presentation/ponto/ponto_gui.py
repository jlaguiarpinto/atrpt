# presentation/ponto/ponto_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG


class PontoGUI(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()

    def _build(self):
        frame = self.abrir_work_area()

        # ── botões de acção ───────────────────────────────────────────────────
        btn_frame = tk.Frame(frame, bg=self.BG)
        btn_frame.pack(fill="x", pady=8, padx=10)

        tk.Button(
            btn_frame,
            text="⚙  Processar Ponto",
            command=self._on_processar,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            fg=self.FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Rever / Editar Resumo",
            command=self._on_rever,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            fg=self.FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Resumo por Empregado",
            command=self._on_resumo_empregado,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            fg=self.FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Erros de Picagem",
            command=self._on_erros_picagem,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            fg=self.FG,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Ausências (Férias/Baixas)",
            command=self._on_ausencias,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            fg=self.FG,
        ).pack(side="left", padx=(0, 8))

        # ── área de log ───────────────────────────────────────────────────────
        log_frame = tk.Frame(frame, bg=self.BG)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.txt = tk.Text(log_frame, height=16, state="disabled",
                           bg="#1e1e1e", fg="#d4d4d4",
                           font=("Consolas", 9), wrap="word")
        sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

    def _on_processar(self):
        self.controller.processar()

    def _on_rever(self):
        self.controller.rever_resumo()

    def _on_resumo_empregado(self):
        self.controller.resumo_empregado()

    def _on_erros_picagem(self):
        self.controller.ver_erros_picagem()

    def _on_ausencias(self):
        self.controller.gerir_ausencias()


    def log(self, msg):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")
