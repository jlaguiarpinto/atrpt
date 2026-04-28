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
        self.abrir_work_area()
        opcoes = [
            ("Consultar Empregados", self._consultar),
            ("Listar Empregados",    self._listar),
        ]
        self.build_menu_buttons(opcoes)

    def _consultar(self):
        from presentation.pessoas.empregado_consulta_gui import EmpregadoConsultaGUI
        self.show_view(EmpregadoConsultaGUI, self.controller)

    def _listar(self):
        self._mostrar_lista_janela()

    # ------------------------------------------------------------------
    # Janela de listagem com toggle activos/todos e duplo-clique -> editar
    # ------------------------------------------------------------------

    def _mostrar_lista_janela(self):
        win = tk.Toplevel(self.root)
        win.title("Empregados")
        win.geometry("1100x560")
        win.resizable(True, True)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)

        # -- barra de controlo ----------------------------------------
        barra = tk.Frame(win)
        barra.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))

        var_ativos = tk.BooleanVar(value=True)

        lbl_count = ttk.Label(barra, text="", foreground="gray")
        lbl_count.pack(side="right", padx=8)

        def _recarregar():
            dados = self.controller.get_empregados(apenas_ativos=var_ativos.get())
            _popular(dados)
            n = len(dados)
            lbl_count.config(text=f"{n} empregado{'s' if n != 1 else ''}")

        ttk.Radiobutton(barra, text="So activos", variable=var_ativos,
                        value=True,  command=_recarregar).pack(side="left")
        ttk.Radiobutton(barra, text="Todos",      variable=var_ativos,
                        value=False, command=_recarregar).pack(side="left", padx=(8, 0))

        # -- treeview -------------------------------------------------
        cols = ("Num", "Nome", "Activo", "Local", "Sector",
                "Categoria Actual", "Admissao", "Antiguidade", "Vencimento")
        headers = {
            "Num": ("N", 50), "Nome": ("Nome", 220), "Activo": ("Activo", 55),
            "Local": ("Local", 80), "Sector": ("Sector", 140),
            "Categoria Actual": ("Categoria Actual", 200),
            "Admissao": ("Admissao", 90), "Antiguidade": ("Antiguidade", 80),
            "Vencimento": ("Vencimento", 90),
        }

        frame = tk.Frame(win)
        frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=2)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=cols, show="headings")
        tree.tag_configure("inativo", foreground="gray")

        for col in cols:
            lbl, width = headers[col]
            tree.heading(col, text=lbl)
            tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        iid_map = {}

        # -- ordenacao por coluna -------------------------------------
        col_num    = {"Num", "Antiguidade"}
        sort_state = {"col": None, "rev": False}

        def _ordenar(col):
            rev = not sort_state["rev"] if sort_state["col"] == col else False
            sort_state.update({"col": col, "rev": rev})
            for c in cols:
                lbl, _ = headers[c]
                tree.heading(c, text=lbl)
            lbl_col, _ = headers[col]
            tree.heading(col, text=lbl_col + (" (A)" if not rev else " (D)"))

            def _chave(iid):
                val = tree.set(iid, col)
                if col in col_num:
                    try: return int(val)
                    except: return 0
                if col == "Vencimento":
                    try: return float(val.replace(",", ""))
                    except: return 0.0
                return val.lower()

            itens = sorted(tree.get_children(), key=_chave, reverse=rev)
            for i, iid in enumerate(itens):
                tree.move(iid, "", i)

        for col in cols:
            tree.heading(col, command=lambda c=col: _ordenar(c))

        # -- popular --------------------------------------------------
        def _popular(dados):
            tree.delete(*tree.get_children())
            iid_map.clear()
            for e in dados:
                tag = "" if e.ativo_bool else "inativo"
                iid = tree.insert("", "end", tags=(tag,), values=(
                    e.numero,
                    e.nome,
                    "Sim" if e.ativo_bool else "Nao",
                    e.local or "",
                    e.sector or "",
                    e.categoria_atual or "",
                    e.data_admissao.strftime("%Y-%m-%d") if e.data_admissao else "",
                    e.antiguidade if e.antiguidade is not None else 0,
                    f"{e.vencimento:,.2f}" if e.vencimento else "",
                ))
                iid_map[iid] = e

        # -- duplo-clique -> editar -----------------------------------
        def _on_dblclick(event):
            sel = tree.selection()
            if not sel:
                return
            e = iid_map.get(sel[0])
            if e:
                _abrir_edicao(e, sel[0])

        tree.bind("<Double-1>", _on_dblclick)

        def _abrir_edicao(empregado, iid):
            from presentation.pessoas.empregado_edicao_gui import EmpregadoEdicaoGUI
            EmpregadoEdicaoGUI(
                win, self.controller, empregado,
                on_save=lambda e: _after_save(e, iid),
            )

        def _after_save(empregado, iid):
            tree.item(iid, values=(
                empregado.numero,
                empregado.nome,
                "Sim" if empregado.ativo_bool else "Nao",
                empregado.local or "",
                empregado.sector or "",
                empregado.categoria_atual or "",
                empregado.data_admissao.strftime("%Y-%m-%d") if empregado.data_admissao else "",
                empregado.antiguidade if empregado.antiguidade is not None else 0,
                f"{empregado.vencimento:,.2f}" if empregado.vencimento else "",
            ))

        # -- rodape ---------------------------------------------------
        ttk.Label(win, text="Duplo-clique para editar", foreground="gray").grid(
            row=2, column=0, sticky="w", padx=10, pady=(0, 2))
        ttk.Button(win, text="Fechar", command=win.destroy).grid(
            row=3, column=0, pady=(0, 6))

        _recarregar()
