# presentation/correio/recolher_dados_gui.py
#
# Fase 3 — Ler PDFs do disco, extrair campos e persistir em faturacao_documentos.
#
# Apresenta os resultados numa tabela com indicação de estado:
#   Importado  — novo registo inserido na BD
#   Já existe  — número de documento já constava
#   Sem dados  — PDF sem campos suficientes para importar

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from presentation.shared.base_gui import BaseGui as BG
from infrastructure.persistence.aprovisionamento.faturacao_fornecedores_repository import (
    FaturacaoFornecedoresRepository,
)

_CORRECOES_JSON = Path(__file__).parent.parent.parent / "tools" / "correcoes_faturas.json"

_COLS = [
    ("pdf_nome",   "Ficheiro PDF",    140, "w"),
    ("n_fatura",   "N.º Fatura",      110, "w"),
    ("data",       "Data Emissão",     88, "center"),
    ("vencimento", "Data Pagamento",   88, "center"),
    ("nif",        "NIF",              95, "center"),
    ("total",      "Total (€)",        82, "e"),
    ("iva",        "IVA (€)",          72, "e"),
    ("fornecedor", "Fornecedor",       155, "w"),
    ("estado",     "Estado",           80, "center"),
]

_CAMPOS_DLG = [
    ("n_fatura",   "N.º Fatura"),
    ("nif",        "NIF emitente"),
    ("data",       "Data emissão"),
    ("vencimento", "Data pagamento"),
    ("total",      "Total (€)"),
    ("iva",        "IVA (€)"),
]


# ------------------------------------------------------------------
# Persistência de correções (partilhada com debug_faturas.py)
# ------------------------------------------------------------------

def _guardar_correcao(pdf_nome: str, campo: str, extraido, correto: str) -> None:
    dados: list = []
    if _CORRECOES_JSON.exists():
        try:
            dados = json.loads(_CORRECOES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    dados.append({
        "pdf":      pdf_nome,
        "campo":    campo,
        "extraido": str(extraido) if extraido is not None else None,
        "correto":  correto,
        "data":     datetime.now().isoformat(timespec="seconds"),
    })
    _CORRECOES_JSON.parent.mkdir(parents=True, exist_ok=True)
    _CORRECOES_JSON.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class RecolherDadosGUI(BG):

    def __init__(self, parent, controller):
        self._resultados: list[dict] = []
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([
            ("Recolher Dados", self._recolher),
        ])
        self._build()
        self._mostrar_directorio()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=8)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        destino = str(self.controller.pasta_faturas) if self.controller.pasta_faturas else "—"
        tk.Label(
            outer, text=f"Pasta:  {destino}",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 9, "bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.tree = ttk.Treeview(
            outer, columns=[c[0] for c in _COLS],
            show="headings", selectmode="browse",
        )
        for key, label, width, anchor in _COLS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor=anchor, minwidth=40,
                             stretch=(key in ("pdf_nome", "fornecedor")))

        self.tree.tag_configure("importado", foreground="#1a7a1a")
        self.tree.tag_configure("ja_existe", foreground="#4a6fa5")
        self.tree.tag_configure("sem_dados", foreground="#b05000")

        sb_v = ttk.Scrollbar(outer, orient="vertical",   command=self.tree.yview)
        sb_h = ttk.Scrollbar(outer, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb_v.grid(row=1, column=1, sticky="ns")
        sb_h.grid(row=2, column=0, sticky="ew")

        self.lbl_status = tk.Label(
            outer, text="Prima «Recolher Dados» para importar.",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_status.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------------

    def _mostrar_directorio(self):
        d = self.controller.pasta_faturas
        if d and d.exists():
            n = len(list(d.glob("*.pdf")))
            self._set_status(f"{n} PDF(s) em {d}. Prima «Recolher Dados» para importar.")
        elif d:
            self._set_status(f"Pasta ainda não existe: {d}")
        else:
            self._set_status("pasta_faturas não configurada.")

    # ------------------------------------------------------------------
    # Recolha
    # ------------------------------------------------------------------

    def _recolher(self):
        directorio = self.controller.pasta_faturas
        if not directorio or not directorio.exists():
            self.informuser("Pasta não encontrada",
                            f"A pasta não existe:\n{directorio}", "warning")
            return

        pdfs = list(directorio.glob("*.pdf"))
        if not pdfs:
            self.informuser("Sem PDFs", "Não foram encontrados ficheiros PDF.", "warning")
            return

        db_path = self.controller._fornecedor_repo.db_path if self.controller._fornecedor_repo else None
        if not db_path:
            self.informuser("Sem base de dados",
                            "Repositório de fornecedores não configurado.", "error")
            return

        faturacao_repo = FaturacaoFornecedoresRepository(db_path)

        self.tree.delete(*self.tree.get_children())
        self._resultados = []

        def progresso(i, total, nome):
            self._set_status(f"{i}/{total}: {nome}")
            self.frame.update_idletasks()

        ret = self.controller.recolher_faturas_directorio(
            directorio, faturacao_repo,
            callback=progresso,
            on_dados_incompletos=self._pedir_dados_em_falta,
        )
        self._resultados = ret["resultados"]

        for r in self._resultados:
            estado = r.get("estado", "Sem dados")
            tag = {"Importado": "importado", "Já existe": "ja_existe"}.get(estado, "sem_dados")
            self.tree.insert("", "end", tags=(tag,), values=(
                r["pdf_nome"],
                r.get("n_fatura")   or "—",
                r.get("data")       or "—",
                r.get("vencimento") or "—",
                r.get("nif")        or "—",
                f"{r['total']:.2f}" if r.get("total") is not None else "—",
                f"{r['iva']:.2f}"   if r.get("iva")   is not None else "—",
                r.get("fornecedor") or "—",
                estado,
            ))

        imp = ret["importados"]
        dup = ret["ja_existem"]
        vaz = ret["sem_dados"]
        self._set_status(
            f"{len(self._resultados)} PDF(s)  |  "
            f"{imp} importado(s)  |  "
            f"{dup} já existia(m)  |  "
            f"{vaz} sem dados suficientes"
        )
        if imp:
            self.informuser(
                "Importação concluída",
                f"{imp} fatura(s) importada(s) para a base de dados.",
            )

    # ------------------------------------------------------------------
    # Diálogo de preenchimento manual
    # ------------------------------------------------------------------

    def _pedir_dados_em_falta(self, nome_pdf: str, fornecedor: str, campos: dict) -> dict | None:
        """
        Modal que pede ao utilizador os campos não detectados automaticamente.
        Campos em falta aparecem a vermelho.
        Correções são gravadas em tools/correcoes_faturas.json para aprendizagem.
        """
        root = self.frame.winfo_toplevel()
        dlg  = tk.Toplevel(root)
        dlg.title("Dados em falta — ajuda necessária")
        dlg.resizable(False, False)
        dlg.transient(root)

        pad = 14

        # Cabeçalho
        tk.Label(
            dlg,
            text="Não foi possível detectar automaticamente todos os campos.",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=pad, pady=(12, 2))

        info = tk.Frame(dlg)
        info.pack(fill="x", padx=pad, pady=(0, 6))
        for row, (label, val) in enumerate([
            ("PDF:",         nome_pdf[:80]),
            ("Fornecedor:",  fornecedor[:80]),
        ]):
            tk.Label(info, text=label, font=("Segoe UI", 9, "bold"),
                     width=12, anchor="w").grid(row=row, column=0, sticky="w")
            tk.Label(info, text=val, font=("Segoe UI", 9),
                     wraplength=380, justify="left").grid(row=row, column=1, sticky="w")

        tk.Frame(dlg, height=1, bg="#cccccc").pack(fill="x", padx=pad, pady=(0, 8))

        # Campos — vermelho se em falta, cinzento se preenchido
        entries: dict[str, tk.StringVar] = {}
        form = tk.Frame(dlg)
        form.pack(fill="x", padx=pad)
        primeiro_vazio = None

        for row, (chave, label) in enumerate(_CAMPOS_DLG):
            val_atual = campos.get(chave)
            em_falta  = val_atual is None or (isinstance(val_atual, str) and not val_atual.strip())
            cor = "#cc0000" if em_falta else "#333333"
            sufixo = " *" if em_falta else ""

            tk.Label(
                form,
                text=label + sufixo,
                font=("Segoe UI", 9, "bold" if em_falta else "normal"),
                fg=cor, width=16, anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=2)

            var = tk.StringVar(value=str(val_atual) if val_atual is not None else "")
            ent = tk.Entry(form, textvariable=var, width=34, font=("Segoe UI", 9))
            ent.grid(row=row, column=1, sticky="ew", pady=2)
            entries[chave] = var

            if em_falta and primeiro_vazio is None:
                primeiro_vazio = ent

        tk.Label(
            dlg, text="* campo em falta  |  Enter = confirmar  |  Esc = ignorar fatura",
            font=("Segoe UI", 8), fg="#888888",
        ).pack(anchor="w", padx=pad, pady=(6, 0))

        resultado = [None]

        def _confirmar():
            correcao = {}
            for chave, var in entries.items():
                v = var.get().strip()
                if not v:
                    continue
                val_orig = campos.get(chave)
                # Guardar correção se diferente do original
                if str(val_orig or "") != v:
                    _guardar_correcao(nome_pdf, chave, val_orig, v)
                # Converter numéricos
                if chave in ("total", "iva"):
                    try:
                        correcao[chave] = float(v.replace(",", "."))
                    except ValueError:
                        pass
                else:
                    correcao[chave] = v
            resultado[0] = correcao if correcao else {}
            dlg.destroy()

        def _ignorar():
            dlg.destroy()

        btns = tk.Frame(dlg)
        btns.pack(fill="x", padx=pad, pady=(10, 14))
        tk.Button(btns, text="Usar estes dados", command=_confirmar,
                  font=("Segoe UI", 9), width=16).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Ignorar fatura",   command=_ignorar,
                  font=("Segoe UI", 9), width=14).pack(side="left")

        dlg.bind("<Return>", lambda _: _confirmar())
        dlg.bind("<Escape>", lambda _: _ignorar())

        # Centrar, garantir visibilidade, depois grab (ordem importa no Windows)
        dlg.update_idletasks()
        rx = root.winfo_rootx() + (root.winfo_width()  - dlg.winfo_width())  // 2
        ry = root.winfo_rooty() + (root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{rx}+{ry}")
        dlg.deiconify()
        dlg.attributes("-topmost", True)
        dlg.update()          # mapear a janela antes de grab_set
        dlg.grab_set()
        dlg.attributes("-topmost", False)   # manter visível mas não bloquear Alt+Tab
        if primeiro_vazio:
            primeiro_vazio.focus_set()

        dlg.wait_window()
        return resultado[0]

    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)
