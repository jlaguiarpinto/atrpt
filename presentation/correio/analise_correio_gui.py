# presentation/correio/analise_correio_gui.py
#
# Análise global da caixa de correio (todas as pastas com conteúdo).
#
# Layout (vertical):
#   topo  — Treeview: Pasta | Total | Anexos | % Anexos | Top 5 Palavras
#   baixo — Treeview: Palavra | Ocorrências (agregado de todas as pastas)
#   barra — status

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from presentation.shared.base_gui import BaseGui as BG


class AnaliseCorreioGUI(BG):

    def __init__(self, parent, controller):
        self._dados = None
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([
            ("Analisar",      self._analisar),
            ("Exportar XLSX", self._exportar),
        ])
        self._build()
        self._conectar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=6, pady=6)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        pw = ttk.PanedWindow(outer, orient="vertical")
        pw.grid(row=0, column=0, sticky="nsew")

        # ── topo: resumo por pasta ────────────────────────────────────
        top = tk.Frame(pw, bg=self.BG)
        pw.add(top, weight=2)
        top.rowconfigure(1, weight=1)
        top.columnconfigure(0, weight=1)

        tk.Label(
            top, text="Resumo por pasta",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 2))

        cols_r = ("pasta", "total", "anexos", "pct", "palavras")
        self.tree_resumo = ttk.Treeview(top, columns=cols_r, show="headings", selectmode="browse")
        cfg_r = {
            "pasta":    ("Pasta",              220, "w"),
            "total":    ("Total",               70, "center"),
            "anexos":   ("Com Anexos",           90, "center"),
            "pct":      ("% Anexos",             70, "center"),
            "palavras": ("Top 5 Palavras-chave", 380, "w"),
        }
        for c, (lbl, w, a) in cfg_r.items():
            self.tree_resumo.heading(c, text=lbl)
            self.tree_resumo.column(c, width=w, anchor=a, minwidth=40, stretch=(c == "palavras"))

        sb_r = ttk.Scrollbar(top, orient="vertical", command=self.tree_resumo.yview)
        self.tree_resumo.configure(yscrollcommand=sb_r.set)
        self.tree_resumo.grid(row=1, column=0, sticky="nsew")
        sb_r.grid(row=1, column=1, sticky="ns")

        # ── baixo: palavras globais ───────────────────────────────────
        bot = tk.Frame(pw, bg=self.BG)
        pw.add(bot, weight=1)
        bot.rowconfigure(1, weight=1)
        bot.columnconfigure(0, weight=1)

        tk.Label(
            bot, text="Palavras mais usadas em assuntos (todas as pastas)",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(8, 2))

        self.tree_palavras = ttk.Treeview(
            bot, columns=("palavra", "n"), show="headings", selectmode="browse",
        )
        self.tree_palavras.heading("palavra", text="Palavra")
        self.tree_palavras.heading("n",       text="Ocorrências")
        self.tree_palavras.column("palavra", anchor="w",      width=300, minwidth=80)
        self.tree_palavras.column("n",       anchor="center", width=100, minwidth=60, stretch=False)

        sb_p = ttk.Scrollbar(bot, orient="vertical", command=self.tree_palavras.yview)
        self.tree_palavras.configure(yscrollcommand=sb_p.set)
        self.tree_palavras.grid(row=1, column=0, sticky="nsew")
        sb_p.grid(row=1, column=1, sticky="ns")

        # ── barra de estado ───────────────────────────────────────────
        self.lbl_status = tk.Label(
            outer, text="Prima «Analisar» para iniciar.",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_status.grid(row=1, column=0, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------------
    # Ligação e análise
    # ------------------------------------------------------------------

    def _conectar(self):
        self._set_status("A ligar…")
        self.frame.update_idletasks()
        if not self.controller.conectar_se_necessario():
            self._set_status("Erro: sem ligação ao servidor.")
        else:
            self._set_status("Ligado. Prima «Analisar» para iniciar.")

    def _analisar(self):
        self.tree_resumo.delete(*self.tree_resumo.get_children())
        self.tree_palavras.delete(*self.tree_palavras.get_children())

        def progresso(i, total, pasta):
            self._set_status(f"A analisar {i}/{total}: {pasta}…")
            self.frame.update_idletasks()

        dados = self.controller.analisar_todas_pastas(callback=progresso)
        self._dados = dados

        for info in dados["por_pasta"]:
            total = info["total"]
            pct   = f"{round(100 * info['num_anexos'] / total, 1):.1f}%" if total else "—"
            palavras_str = ", ".join(w for w, _ in info["palavras_chave"])
            self.tree_resumo.insert("", "end", values=(
                info["pasta"], total, info["num_anexos"], pct, palavras_str,
            ))

        for w, n in dados["palavras_global"]:
            self.tree_palavras.insert("", "end", values=(w, n))

        total_msgs  = sum(p["total"]      for p in dados["por_pasta"])
        total_anx   = sum(p["num_anexos"] for p in dados["por_pasta"])
        n_pastas    = len(dados["por_pasta"])
        self._set_status(
            f"{n_pastas} pastas  |  {total_msgs} mensagens  |  {total_anx} com anexos"
        )

    # ------------------------------------------------------------------
    # Exportação
    # ------------------------------------------------------------------

    def _exportar(self):
        if not self._dados:
            self.informuser("Sem dados", "Execute a análise antes de exportar.", "warning")
            return

        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Guardar análise da caixa de correio",
            initialfile="analise_correio.xlsx",
        )
        if not caminho:
            return

        try:
            from infrastructure.email.analise_xlsx import exportar_analise_xlsx
            exportar_analise_xlsx(self._dados, Path(caminho))
            self.informuser("Exportado", f"Ficheiro guardado:\n{caminho}")
        except Exception as exc:
            self.informuser("Erro ao exportar", str(exc), "error")

    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)
