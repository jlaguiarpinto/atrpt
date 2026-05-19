# utils/importar_pim_historico.py
#
# Utilitário de migração: carrega ficheiros PIM mensais (Excel) para
# a tabela pim_historico em atrpt.db.
#
# Fluxo por ficheiro:
#   1. Utilizador selecciona o ficheiro Excel.
#   2. App detecta ano/mês pela pasta (ex: .../202304/...) — editável.
#   3. Utilizador mapeia as colunas do ficheiro para os campos canónicos.
#      O mapeamento é memorizado entre ficheiros (sticky).
#   4. Pré-visualização das primeiras linhas com o mapeamento aplicado.
#   5. Utilizador confirma → arquiva em SQLite.

import sys
from pathlib import Path

# -- adicionar raiz do projecto ao path ----------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
# ------------------------------------------------------------------------------

import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from core.config import load_config, load_paths
from application.secretaria.arquivar_pim_usecase import ArquivarPimUseCase

_APP_INI = _ROOT / "app.ini"

# Campos canónicos que queremos guardar na BD
_CAMPOS = [
    ("numero_residente", "Nº Residente *"),
    ("atual",            "Atual"),
    ("recebido",         "Recebido"),
    ("saldo",            "Saldo"),
    ("data",             "Data pagamento"),
]
_CAMPO_NOMES = [c for c, _ in _CAMPOS]


def _detectar_ano_mes(path: Path) -> tuple[str, str]:
    """Tenta extrair ano/mês do nome da pasta (ex: 202304 → 2023, 04)."""
    for parte in reversed(path.parts):
        m = re.fullmatch(r"(\d{4})(\d{2})", parte)
        if m:
            return m.group(1), m.group(2)
    return "", ""


def _ler_excel(path: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(path, dtype=str)
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível ler o ficheiro:\n{e}")
        return pd.DataFrame()


class App(tk.Tk):

    def __init__(self, db_path: str, pim_dir: Path):
        super().__init__()
        self.title("Importar Histórico PIM → SQLite")
        self.resizable(True, True)

        self._db_path  = str(db_path)
        self._pim_dir  = pim_dir
        self._df: pd.DataFrame = pd.DataFrame()
        self._colunas_ficheiro: list[str] = []
        self._mapeamento_sticky: dict[str, str] = {}  # campo → coluna (memorizado)

        self._uc = ArquivarPimUseCase(db_path)

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        pad = {"padx": 8, "pady": 4}

        # ── faixa superior: ficheiro + ano/mês ────────────────────────
        topo = tk.LabelFrame(self, text="Ficheiro", **pad)
        topo.pack(fill="x", **pad)

        tk.Button(topo, text="Abrir PIM…", command=self._abrir_ficheiro,
                  width=14).grid(row=0, column=0, **pad)
        self.lbl_ficheiro = tk.Label(topo, text="(nenhum)", anchor="w",
                                     width=60, relief="sunken")
        self.lbl_ficheiro.grid(row=0, column=1, sticky="ew", **pad)
        topo.columnconfigure(1, weight=1)

        tk.Label(topo, text="Ano:").grid(row=1, column=0, sticky="e", padx=(8, 2))
        self.ent_ano = tk.Entry(topo, width=6)
        self.ent_ano.grid(row=1, column=1, sticky="w", pady=4)

        tk.Label(topo, text="Mês:").grid(row=2, column=0, sticky="e", padx=(8, 2))
        self.ent_mes = tk.Entry(topo, width=4)
        self.ent_mes.grid(row=2, column=1, sticky="w", pady=4)

        # ── mapeamento de colunas ────────────────────────────────────
        mapa = tk.LabelFrame(self, text="Mapeamento de colunas", **pad)
        mapa.pack(fill="x", **pad)

        self._cb_mapa: dict[str, ttk.Combobox] = {}
        for i, (campo, label) in enumerate(_CAMPOS):
            obrig = " *" in label
            tk.Label(mapa, text=label,
                     font=("Segoe UI", 9, "bold" if obrig else "normal"),
                     width=18, anchor="e").grid(row=i, column=0, **pad)
            cb = ttk.Combobox(mapa, state="readonly", width=36)
            cb.grid(row=i, column=1, sticky="w", **pad)
            self._cb_mapa[campo] = cb

        tk.Button(mapa, text="Pré-visualizar", command=self._preview,
                  width=14).grid(row=len(_CAMPOS), column=0, columnspan=2,
                                 pady=6)

        # ── pré-visualização ─────────────────────────────────────────
        prev = tk.LabelFrame(self, text="Pré-visualização (primeiras 8 linhas)", **pad)
        prev.pack(fill="both", expand=True, **pad)
        prev.rowconfigure(0, weight=1)
        prev.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(prev, show="headings", height=8)
        vsb = ttk.Scrollbar(prev, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(prev, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ── rodapé: arquivar ─────────────────────────────────────────
        rodape = tk.Frame(self, **pad)
        rodape.pack(fill="x", **pad)

        tk.Button(rodape, text="Arquivar em SQLite", command=self._arquivar,
                  bg="#c8e6c9", font=("Segoe UI", 9, "bold"),
                  width=20).pack(side="left")

        self.lbl_status = tk.Label(rodape, text="", anchor="w",
                                   font=("Segoe UI", 8))
        self.lbl_status.pack(side="left", padx=12)

    # ------------------------------------------------------------------
    # Ficheiro
    # ------------------------------------------------------------------

    def _abrir_ficheiro(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PIM mensal",
            initialdir=str(self._pim_dir),
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
        )
        if not path:
            return
        path = Path(path)
        self._df = _ler_excel(path)
        if self._df.empty:
            return

        self.lbl_ficheiro.config(text=str(path))
        self._colunas_ficheiro = list(self._df.columns)

        # detectar ano/mês
        ano, mes = _detectar_ano_mes(path)
        self.ent_ano.delete(0, "end"); self.ent_ano.insert(0, ano)
        self.ent_mes.delete(0, "end"); self.ent_mes.insert(0, mes)

        # popular comboboxes com as colunas encontradas
        opcoes = ["(ignorar)"] + self._colunas_ficheiro
        for campo, cb in self._cb_mapa.items():
            cb["values"] = opcoes
            # sticky: usar último mapeamento se a coluna ainda existe
            anterior = self._mapeamento_sticky.get(campo, "")
            if anterior and anterior in self._colunas_ficheiro:
                cb.set(anterior)
            else:
                # tentativa de correspondência automática por nome similar
                cb.set(self._auto_match(campo))

        self._set_status(f"{len(self._df)} linhas carregadas. Verifique o mapeamento e pré-visualize.")

    def _auto_match(self, campo: str) -> str:
        """Tenta encontrar a coluna mais provável para o campo canónico."""
        _hints = {
            "numero_residente": ["numero", "residente", "nº", "num"],
            "atual":            ["atual", "pim", "fatura", "valor"],
            "recebido":         ["recebido", "pago", "receb"],
            "saldo":            ["saldo"],
            "data":             ["data", "date", "pagamento"],
        }
        hints = _hints.get(campo, [])
        cols_lower = {c.lower(): c for c in self._colunas_ficheiro}
        for hint in hints:
            for col_l, col_orig in cols_lower.items():
                if hint in col_l:
                    return col_orig
        return "(ignorar)"

    # ------------------------------------------------------------------
    # Pré-visualização
    # ------------------------------------------------------------------

    def _preview(self):
        if self._df.empty:
            messagebox.showwarning("Aviso", "Carregue um ficheiro primeiro.")
            return

        mapa = self._get_mapeamento()
        if mapa is None:
            return

        # construir df mapeado
        df_prev = pd.DataFrame()
        for campo, coluna in mapa.items():
            df_prev[campo] = self._df[coluna] if coluna else None

        self._preencher_tree(df_prev.head(8))

    def _preencher_tree(self, df: pd.DataFrame):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="w")
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=list(row.fillna("").astype(str)))

    # ------------------------------------------------------------------
    # Arquivar
    # ------------------------------------------------------------------

    def _arquivar(self):
        if self._df.empty:
            messagebox.showwarning("Aviso", "Carregue um ficheiro primeiro.")
            return

        mapa = self._get_mapeamento()
        if mapa is None:
            return

        ano_str = self.ent_ano.get().strip()
        mes_str = self.ent_mes.get().strip()
        if not ano_str.isdigit() or not mes_str.isdigit():
            messagebox.showerror("Erro", "Ano e Mês têm de ser numéricos.")
            return
        ano, mes = int(ano_str), int(mes_str)
        if not (1 <= mes <= 12):
            messagebox.showerror("Erro", "Mês deve estar entre 01 e 12.")
            return

        # construir df canónico
        df_canon = pd.DataFrame()
        for campo, coluna in mapa.items():
            df_canon[campo] = self._df[coluna] if coluna else None

        if not messagebox.askyesno(
            "Confirmar",
            f"Arquivar {len(df_canon)} linhas em pim_historico\n"
            f"para {ano}/{mes:02d}?\n\n"
            f"(UPSERT — dados existentes serão actualizados)",
        ):
            return

        try:
            r = self._uc.execute(
                pim_df=df_canon,
                ano=ano,
                mes=mes,
                pim_mensal_file=None,  # sem cópia Excel neste utilitário
            )
            # memorizar mapeamento
            self._mapeamento_sticky = {c: col for c, col in mapa.items() if col}
            self._set_status(
                f"OK — {r['gravados']} linhas arquivadas ({ano}/{mes:02d})."
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_mapeamento(self) -> dict[str, str | None] | None:
        """Devolve {campo: coluna_real} validando o campo obrigatório."""
        mapa = {}
        for campo, cb in self._cb_mapa.items():
            val = cb.get()
            mapa[campo] = None if val == "(ignorar)" else val

        if not mapa.get("numero_residente"):
            messagebox.showerror("Erro", "O campo 'Nº Residente' é obrigatório.")
            return None
        return mapa

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)


def main():
    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_secretaria")
    db_path  = cfg.paths["atrpt_db"]
    pim_dir  = cfg.paths.get("pim_dir", _ROOT)

    app = App(db_path=db_path, pim_dir=pim_dir)
    app.mainloop()


if __name__ == "__main__":
    main()
