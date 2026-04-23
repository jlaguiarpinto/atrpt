# atrpt/presentation/pessoas/pessoas_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG


class PessoasGUI(BG):
    """Menu principal do módulo Pessoas."""

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.set_title("Pessoas")
        self._build_main_menu()
        self._restore_root_menu = self._build_main_menu

    def _build_main_menu(self):
        frame = self.abrir_work_area()

        opcoes = [
            ("Consultar Empregados", self._consultar),
            ("Listar Activos",       self._listar_ativos),
            ("Listar Todos",         self._listar_todos),
        ]
        self.build_menu_buttons(opcoes)

    def _consultar(self):
        from presentation.pessoas.empregado_consulta_gui import EmpregadoConsultaGUI
        self.show_view(EmpregadoConsultaGUI, self.controller)

    def _listar_ativos(self):
        empregados = self.controller.get_empregados(apenas_ativos=True)
        self._mostrar_lista(empregados, titulo="Empregados Activos")

    def _listar_todos(self):
        empregados = self.controller.get_empregados(apenas_ativos=False)
        self._mostrar_lista(empregados, titulo="Todos os Empregados")

    def _mostrar_lista(self, empregados, titulo="Empregados"):
        if not empregados:
            self.informuser("Info", "Nenhum empregado encontrado.")
            return

        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.geometry("1100x520")
        win.resizable(True, True)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        cols = ("Nº", "Nome", "Activo", "Local", "Sector",
                "Categoria Actual", "Admissão", "Antiguidade", "Vencimento")
        widths = {"Nº": 50, "Nome": 220, "Activo": 55, "Local": 80,
                  "Sector": 140, "Categoria Actual": 220,
                  "Admissão": 90, "Antiguidade": 80, "Vencimento": 90}

        frame = tk.Frame(win)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=cols, show="headings")
        tree.tag_configure("inativo", foreground="gray")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 100), anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # mapeamento col → índice e tipo para ordenação
        col_idx = {c: i for i, c in enumerate(cols)}
        col_num = {"Nº", "Antiguidade"}  # colunas numéricas
        sort_state = {"col": None, "rev": False}

        def _popular(dados):
            tree.delete(*tree.get_children())
            for e in dados:
                tag = "" if e.ativo_bool else "inativo"
                tree.insert("", "end", tags=(tag,), values=(
                    e.numero,
                    e.nome,
                    "Sim" if e.ativo_bool else "Não",
                    e.local or "",
                    e.sector or "",
                    e.categoria_atual or "",
                    e.data_admissao.strftime("%Y-%m-%d") if e.data_admissao else "",
                    e.antiguidade if e.antiguidade is not None else 0,
                    f"{e.vencimento:,.2f}" if e.vencimento else "",
                ))

        def _ordenar(col):
            rev = not sort_state["rev"] if sort_state["col"] == col else False
            sort_state["col"] = col
            sort_state["rev"] = rev

            idx = col_idx[col]
            # indicador visual na coluna
            for c in cols:
                tree.heading(c, text=c)
            seta = " ▲" if not rev else " ▼"
            tree.heading(col, text=col + seta)

            def _chave(iid):
                val = tree.set(iid, col)
                if col in col_num:
                    try: return int(val)
                    except: return 0
                if col == "Vencimento":
                    try: return float(val.replace(",", "").replace(" €", ""))
                    except: return 0.0
                return val.lower()

            itens = list(tree.get_children())
            itens.sort(key=_chave, reverse=rev)
            for i, iid in enumerate(itens):
                tree.move(iid, "", i)

        for col in cols:
            tree.heading(col, text=col,
                         command=lambda c=col: _ordenar(c))

        _popular(empregados)

        lbl = ttk.Label(win, text=f"{len(empregados)} empregados", foreground="gray")
        lbl.grid(row=1, column=0, sticky="w", padx=8, pady=(2, 0))
        ttk.Button(win, text="Fechar", command=win.destroy).grid(
            row=2, column=0, pady=6)
