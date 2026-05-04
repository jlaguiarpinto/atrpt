# presentation/ponto/ponto_mapa_operacao_view.py
"""
Mapa de Capacidade Operacional — vista de gestão de operação.

Mostra, para cada dia do mês, quantas pessoas estão presentes em cada
hora do dia, com base nas picagens e1/s1 e e2/s2.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │ MAPA DE OPERAÇÃO  ·  Abril 2026         [← Anterior] [Seguinte→]│
  │ filtro colaborador ______   [Hora] [15 min]   [Exportar]        │
  ├─────────────────────────────────────────────────────────────────┤
  │       00 01 02 … 23                                             │
  │ 01-Qua ██ ░░ ░░ … ██                                            │
  │ 02-Qui ░░ ██ ██ … ░░                                            │
  │ …                                                               │
  ├─────────────────────────────────────────────────────────────────┤
  │ Painel de detalhe (clique numa célula)                          │
  │  08:00–09:00 · 5 presentes: Gracinda Vieira, Manuel Santos, … │
  └─────────────────────────────────────────────────────────────────┘
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

from presentation.shared.base_gui import BaseGui as _BG

logger = logging.getLogger(__name__)

# ── Tema ──────────────────────────────────────────────────────────────────────
BG        = _BG.BG           # "#CADAD9"
FG        = _BG.FG           # "#92332C"
BTN_BG    = _BG.BTN_BG       # "#F1E2CF"
FONT_UI   = _BG.FONT_SUB
FONT_BOLD = _BG.FONT_SUB
FONT_TITLE= _BG.FONT_TITLE
FONT_MONO = ("Courier New", 9)

BG_HEADER = "#b8cccb"
BG_CANVAS = "#1a1a1a"   # fundo escuro para o heatmap
FG_AXIS   = "#888888"

# Gradiente de cor para células: 0 → escuro, max → verde vivo
_GRAD = [
    "#1a1a1a",  # 0
    "#0d2b1a",  # ~10 %
    "#0d4020",  # ~20 %
    "#0d5c26",  # ~33 %
    "#1a7a30",  # ~50 %
    "#2ea844",  # ~66 %
    "#4fc45e",  # ~80 %
    "#7ade8a",  # ~90 %
    "#adf0a0",  # 100 %
]

_DIAS_ABREV = {
    "Segunda": "Seg", "Terca": "Ter", "Quarta": "Qua",
    "Quinta": "Qui", "Sexta": "Sex", "Sabado": "Sáb", "Domingo": "Dom",
}

# Largura/altura de cada célula do heatmap (pixels)
_CW_H  = 28   # célula hora
_CW_Q  = 8    # célula 15 min
_CH    = 26   # altura da linha
_PAD_Y = 24   # cabeçalho hora
_PAD_X = 86   # largura coluna de datas


def _parse_minutes(val) -> float | None:
    """'E07:12' | 'S13:41' | '07:12'  →  minutos desde meia-noite."""
    if not val:
        return None
    s = str(val).strip().lstrip("EeSs").strip()
    m = __import__("re").match(r"^(\d{1,2})[:\.](\d{2})$", s)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def _heat_color(val: float, max_val: float) -> str:
    if max_val <= 0 or val <= 0:
        return _GRAD[0]
    t = min(val / max_val, 1.0)
    idx = min(int(t * (len(_GRAD) - 1)), len(_GRAD) - 2)
    t2  = t * (len(_GRAD) - 1) - idx
    c1  = [int(_GRAD[idx][i:i+2], 16) for i in (1, 3, 5)]
    c2  = [int(_GRAD[idx+1][i:i+2], 16) for i in (1, 3, 5)]
    r   = [int(c1[j] + t2 * (c2[j] - c1[j])) for j in range(3)]
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"


def _text_color(val: float, max_val: float) -> str:
    if max_val <= 0 or val <= 0:
        return BG_CANVAS
    return "#0d1a0d" if (val / max_val) > 0.45 else "#7ade8a"


def _build_heatmap(df: pd.DataFrame, slot_min: int = 60):
    """
    Devolve:
      datas   : lista ordenada de strings "AAAA-MM-DD"
      matrix  : dict[data] → list[float] com len = 24*60//slot_min
                  cada valor = nº de pessoas presentes (media ponderada) no slot
      who     : dict[(data, slot)] → list[str]  nomes presentes
    """
    n_slots = 24 * 60 // slot_min
    datas   = sorted(df["data"].astype(str).unique())
    matrix  = {}
    who     = {}

    for data in datas:
        arr  = [0.0] * n_slots
        pres = {}  # slot → set(nomes)

        rows = df[(df["data"].astype(str) == data) & (df["presenca"] > 0)]
        for _, row in rows.iterrows():
            nome = str(row.get("nome", "")).strip()
            for ec, sc in [("e1", "s1"), ("e2", "s2")]:
                e = _parse_minutes(row.get(ec))
                s = _parse_minutes(row.get(sc))
                if e is None:
                    continue
                if s is None:
                    s = 24 * 60          # turno aberto até ao fim do dia
                if s <= e:
                    continue
                for slot in range(n_slots):
                    slot_s = slot * slot_min
                    slot_e = slot_s + slot_min
                    if slot_s < s and slot_e > e:
                        overlap = (min(slot_e, s) - max(slot_s, e)) / slot_min
                        arr[slot] += overlap
                        pres.setdefault((data, slot), set()).add(nome)

        matrix[data] = arr
        for (d, sl), names in pres.items():
            who[(d, sl)] = sorted(names)

    return datas, matrix, who


class MapaOperacaoView(tk.Toplevel):

    def __init__(self, parent, df: pd.DataFrame, mes_label: str = ""):
        super().__init__(parent)
        self.title(f"Mapa de Operação — {mes_label}")
        self.configure(bg=BG)
        self.state("zoomed")
        self.resizable(True, True)

        # estado
        self._df_orig   = df.copy()
        self._mes_label = mes_label
        self._slot_min  = 60          # 60 = hora; 15 = quarto de hora
        self._filtro    = ""
        self._sel       = None        # (data, slot) seleccionado
        self._max_val   = 1.0

        self._build()
        self._refresh()
        self.grab_set()

    # ── construção da UI ──────────────────────────────────────────────────────

    def _build(self):
        # ── cabeçalho ──────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_HEADER, pady=6)
        hdr.pack(fill="x")

        tk.Label(hdr, text="MAPA DE OPERAÇÃO",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG
                 ).pack(side="left", padx=16)
        tk.Label(hdr, text=self._mes_label,
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG
                 ).pack(side="left")

        # ── barra de controlo ───────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG, pady=5)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="Filtrar:", font=FONT_UI, bg=BG, fg=FG
                 ).pack(side="left", padx=(0, 4))
        self._ent_filtro = tk.Entry(bar, font=FONT_MONO, width=22,
                                    bg="#f8f8f8", fg="black", relief="solid", bd=1)
        self._ent_filtro.pack(side="left", padx=(0, 10))
        self._ent_filtro.bind("<KeyRelease>", self._on_filtro)

        self._btn_hora = tk.Button(bar, text="Por Hora",
                                    command=lambda: self._set_slot(60),
                                    font=FONT_UI, bg=BTN_BG, fg=FG,
                                    relief="sunken", padx=8, pady=2)
        self._btn_hora.pack(side="left", padx=(0, 4))

        self._btn_15 = tk.Button(bar, text="15 min",
                                  command=lambda: self._set_slot(15),
                                  font=FONT_UI, bg=BTN_BG, fg=FG,
                                  relief="raised", padx=8, pady=2)
        self._btn_15.pack(side="left", padx=(0, 12))

        # legenda de escala
        self._lbl_escala = tk.Label(bar, text="", font=FONT_MONO,
                                     bg=BG, fg=FG)
        self._lbl_escala.pack(side="left", padx=(0, 12))

        tk.Button(bar, text="Fechar", command=self.destroy,
                  font=FONT_UI, bg=BTN_BG, fg=FG,
                  relief="raised", padx=10, pady=2
                  ).pack(side="right", padx=4)

        # ── canvas scrollável para o heatmap ───────────────────────────────
        canvas_frame = tk.Frame(self, bg=BG_CANVAS)
        canvas_frame.pack(fill="both", expand=True, padx=0, pady=0)
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(canvas_frame, bg=BG_CANVAS,
                                  highlightthickness=0, cursor="crosshair")
        vsb = ttk.Scrollbar(canvas_frame, orient="vertical",
                             command=self._canvas.yview)
        hsb = ttk.Scrollbar(canvas_frame, orient="horizontal",
                             command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Motion>",   self._on_motion)

        # ── painel de detalhe (baixo) ───────────────────────────────────────
        det = tk.Frame(self, bg=BG_HEADER, pady=5, relief="groove", bd=1)
        det.pack(fill="x", padx=0, pady=0)

        self._lbl_det_hora = tk.Label(det, text="",
                                       font=FONT_BOLD, bg=BG_HEADER, fg=FG,
                                       width=20, anchor="w")
        self._lbl_det_hora.pack(side="left", padx=12)

        self._lbl_det_nomes = tk.Label(det, text="← clique numa célula para ver quem está presente",
                                        font=FONT_MONO, bg=BG_HEADER, fg="#555555",
                                        anchor="w", wraplength=900, justify="left")
        self._lbl_det_nomes.pack(side="left", fill="x", expand=True, padx=8)

    # ── lógica ────────────────────────────────────────────────────────────────

    def _df_filtrado(self) -> pd.DataFrame:
        df = self._df_orig[self._df_orig["presenca"] > 0].copy()
        if self._filtro:
            f = self._filtro.lower()
            df = df[df["nome"].astype(str).str.lower().str.contains(f, na=False)]
        return df

    def _refresh(self):
        df = self._df_filtrado()
        self._datas, self._matrix, self._who = _build_heatmap(df, self._slot_min)

        # max global
        if self._matrix:
            self._max_val = max(
                (max(v) for v in self._matrix.values() if v),
                default=1.0
            )
        else:
            self._max_val = 1.0

        self._draw()

    def _draw(self):
        c       = self._canvas
        c.delete("all")

        cw       = _CW_H if self._slot_min == 60 else _CW_Q
        n_slots  = 24 * 60 // self._slot_min
        n_datas  = len(self._datas)

        total_w  = _PAD_X + n_slots * (cw + 1)
        total_h  = _PAD_Y + n_datas * (_CH + 1)

        c.configure(scrollregion=(0, 0, total_w + 20, total_h + 20))

        # ── cabeçalho de horas ──────────────────────────────────────────────
        for slot in range(n_slots):
            mins  = slot * self._slot_min
            x     = _PAD_X + slot * (cw + 1)
            if self._slot_min == 60 or mins % 60 == 0:
                label = f"{mins // 60:02d}h"
                c.create_text(x + cw // 2, _PAD_Y - 6,
                               text=label, fill=FG_AXIS,
                               font=("Courier New", 7), anchor="s")

        # ── linhas por dia ──────────────────────────────────────────────────
        for row_i, data in enumerate(self._datas):
            y = _PAD_Y + row_i * (_CH + 1)

            # etiqueta de data
            row_df   = self._df_orig[self._df_orig["data"].astype(str) == data]
            dia_sem  = ""
            feriado  = ""
            if not row_df.empty:
                dia_sem = _DIAS_ABREV.get(
                    str(row_df.iloc[0].get("dia_semana", "")), "")
                feriado = str(row_df.iloc[0].get("feriado_desc", "") or "")

            lbl = f"{data[8:]} {dia_sem}"
            cor_lbl = "#cc4400" if feriado else ("#888888" if dia_sem in ("Sáb", "Dom") else "#cccccc")

            c.create_text(_PAD_X - 4, y + _CH // 2,
                           text=lbl, fill=cor_lbl,
                           font=("Courier New", 8, "bold"), anchor="e")

            arr = self._matrix.get(data, [0.0] * (24 * 60 // self._slot_min))

            for slot, val in enumerate(arr):
                x    = _PAD_X + slot * (cw + 1)
                bg   = _heat_color(val, self._max_val)
                fgc  = _text_color(val, self._max_val)

                c.create_rectangle(x, y, x + cw, y + _CH,
                                    fill=bg, outline="#111111", width=0,
                                    tags=(f"cell_{data}_{slot}",))

                if val >= 0.5 and self._slot_min == 60:
                    c.create_text(x + cw // 2, y + _CH // 2,
                                   text=f"{val:.0f}",
                                   fill=fgc, font=("Courier New", 7, "bold"),
                                   tags=(f"cell_{data}_{slot}",))

        # ── highlight da célula seleccionada ────────────────────────────────
        if self._sel:
            sel_d, sel_s = self._sel
            if sel_d in self._datas:
                row_i = self._datas.index(sel_d)
                y     = _PAD_Y + row_i * (_CH + 1)
                x     = _PAD_X + sel_s * (cw + 1)
                c.create_rectangle(x - 1, y - 1, x + cw + 1, y + _CH + 1,
                                    fill="", outline="#ffffff", width=2)

        # ── escala ──────────────────────────────────────────────────────────
        self._lbl_escala.config(
            text=f"Escala: 0 → {self._max_val:.0f} pessoas"
        )

    # ── eventos ───────────────────────────────────────────────────────────────

    def _cell_at(self, event):
        """Devolve (data, slot) para a posição do rato, ou None."""
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        cw = _CW_H if self._slot_min == 60 else _CW_Q

        col = int((cx - _PAD_X) // (cw + 1))
        row = int((cy - _PAD_Y) // (_CH + 1))

        n_slots = 24 * 60 // self._slot_min
        if 0 <= row < len(self._datas) and 0 <= col < n_slots:
            return self._datas[row], col
        return None

    def _on_click(self, event):
        cell = self._cell_at(event)
        if cell is None:
            return
        data, slot = cell
        self._sel = cell

        mins_inicio = slot * self._slot_min
        mins_fim    = mins_inicio + self._slot_min
        hora_lbl = (
            f"{data}  "
            f"{mins_inicio // 60:02d}:{mins_inicio % 60:02d}"
            f" – {mins_fim // 60:02d}:{mins_fim % 60:02d}"
        )
        nomes = self._who.get((data, slot), [])
        val   = self._matrix.get(data, [])[slot] if data in self._matrix else 0.0

        self._lbl_det_hora.config(
            text=f"{hora_lbl}  ({val:.1f} pessoas)"
        )
        if nomes:
            self._lbl_det_nomes.config(
                text="  ·  ".join(nomes),
                fg=FG
            )
        else:
            self._lbl_det_nomes.config(
                text="(sem presenças registadas neste slot)",
                fg="#888888"
            )

        self._draw()

    def _on_motion(self, event):
        """Tooltip simples via cursor — apenas atualiza o título da janela."""
        cell = self._cell_at(event)
        if cell:
            data, slot = cell
            mins = slot * self._slot_min
            val  = (self._matrix.get(data, [])[slot]
                    if data in self._matrix and slot < len(self._matrix[data])
                    else 0.0)
            self.title(
                f"Mapa de Operação — {self._mes_label}  |  "
                f"{data}  {mins // 60:02d}:{mins % 60:02d}  "
                f"→  {val:.1f} pessoas"
            )

    def _on_filtro(self, _event=None):
        self._filtro = self._ent_filtro.get().strip()
        self._refresh()

    def _set_slot(self, mins: int):
        self._slot_min = mins
        self._sel      = None
        if mins == 60:
            self._btn_hora.config(relief="sunken")
            self._btn_15.config(relief="raised")
        else:
            self._btn_hora.config(relief="raised")
            self._btn_15.config(relief="sunken")
        self._refresh()
