# atrpt/presentation/aprovisionamento/encomendas_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG


ESTADOS_ENCOMENDA = ["colocada", "recebida", "pagar", "paga"]


class EncomendasMenuGUI(BG):
    """Menu principal de Encomendas — friso de opções."""

    def __init__(self, parent, controller):
        super().__init__(parent, controller)

    def _post_init(self):
        self._build()

    def _build(self):
        opcoes = [
            ("Listar Encomendas", self._dialogo_listar_encomendas),
            ("Receber Encomenda", self._receber_encomenda),
            ("Pagar Encomenda",   self._pagar_encomenda),
        ]
        self.build_menu_buttons(opcoes)

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------

    def _dialogo_listar_encomendas(self):
        win = tk.Toplevel(self.root)
        win.title("Filtrar Encomendas")
        win.resizable(False, False)
        BG.make_modal(win, self.root)

        ttk.Label(win, text="Selecione os estados a listar:").pack(padx=16, pady=(12, 4))

        vars_estados = {}
        for estado in ESTADOS_ENCOMENDA:
            var = tk.BooleanVar(value=False)
            vars_estados[estado] = var
            ttk.Checkbutton(win, text=estado.capitalize(), variable=var).pack(anchor="w", padx=24)

        ttk.Label(win, text="(nenhum selecionado = todos)", foreground="gray").pack(pady=(4, 0))

        def _confirmar():
            selecionados = [e for e, v in vars_estados.items() if v.get()]
            win.destroy()
            encomendas = self.controller.listar_encomendas(*selecionados)
            self._mostrar_encomendas(encomendas)

        ttk.Button(win, text="Listar", command=_confirmar).pack(pady=10)
        self.root.wait_window(win)

    def _mostrar_encomendas(self, encomendas):
        if not encomendas:
            self.informuser("Info", "Nenhuma encomenda encontrada.")
            return

        mapa_forn = self.controller.get_mapa_fornecedores()

        win = tk.Toplevel(self.root)
        win.title("Lista de Encomendas")
        win.geometry("1100x500")
        win.resizable(True, True)

        cols = ("Nº", "Pedido", "Fornecedor", "Descrição", "Valor (€)",
                "Data", "Prazo", "Local", "Estado", "Pode Pagar")
        tree = ttk.Treeview(win, columns=cols, show="headings")

        widths = {"Nº": 80, "Pedido": 80, "Fornecedor": 160, "Descrição": 200,
                  "Valor (€)": 90, "Data": 100, "Prazo": 100, "Local": 120,
                  "Estado": 110, "Pode Pagar": 80}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 100), anchor="w")

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(win, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        for e in encomendas:
            estado = self._estado_display(e)
            tree.insert("", "end", values=(
                e.numero,
                e.pedido_numero,
                mapa_forn.get(str(e.fornecedor_id), e.fornecedor_id),
                (e.descricao or "")[:50],
                f"{e.valor:,.2f}",
                e.data_encomenda.strftime("%Y-%m-%d") if e.data_encomenda else "",
                e.prazo_entrega.strftime("%Y-%m-%d") if e.prazo_entrega else "",
                e.local_entrega or "",
                estado,
                "Sim" if e.pode_pagar else "",
            ))

        ttk.Button(win, text="Fechar", command=win.destroy).pack(pady=8)

    def _estado_display(self, e) -> str:
        if e.pode_pagar and e.recebido == "pago":
            return "paga"
        if e.pode_pagar:
            return "pagar"
        if e.recebido == "ok":
            return "recebida"
        return "colocada"

    # ------------------------------------------------------------------
    # Receber
    # ------------------------------------------------------------------

    def _receber_encomenda(self):
        encomendas = self.controller.listar_encomendas("colocada")
        if not encomendas:
            self.informuser("Info", "Não existem encomendas por receber.")
            return

        mapa_forn = self.controller.get_mapa_fornecedores()
        win = tk.Toplevel(self.root)
        win.title("Receber Encomenda")
        win.resizable(False, False)
        BG.make_modal(win, self.root)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        # combobox de encomendas
        ttk.Label(frame, text="Encomenda:").grid(row=0, column=0, sticky="w", pady=4)
        numeros = [e.numero for e in encomendas]
        self._enc_map = {e.numero: e for e in encomendas}

        cb_enc = self.criar_combobox_autocomplete(
            frame, valores=numeros, largura=20,
            placeholder="Selecione...",
        )
        cb_enc.grid(row=0, column=1, sticky="w", pady=4)

        lbl_info = ttk.Label(frame, text="", foreground="gray")
        lbl_info.grid(row=1, column=0, columnspan=2, sticky="w")

        def _on_sel(event=None):
            e = self._enc_map.get(cb_enc.get())
            if e:
                nome = mapa_forn.get(str(e.fornecedor_id), e.fornecedor_id)
                lbl_info.config(text=f"{nome}  |  {e.descricao}  |  {e.valor:,.2f} €")

        cb_enc.bind("<<ComboboxSelected>>", _on_sel)

        # resultado
        ttk.Label(frame, text="Resultado:").grid(row=2, column=0, sticky="w", pady=8)
        var_resultado = tk.StringVar(value="ok")
        ttk.Radiobutton(frame, text="OK — conforme", variable=var_resultado,
                        value="ok").grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(frame, text="Não conforme", variable=var_resultado,
                        value="notok").grid(row=3, column=1, sticky="w")

        # botões
        btn_f = ttk.Frame(frame)
        btn_f.grid(row=4, column=0, columnspan=2, pady=12)

        def _confirmar():
            numero = cb_enc.get().strip()
            if numero not in self._enc_map:
                messagebox.showerror("Erro", "Selecione uma encomenda.", parent=win)
                return
            try:
                self.controller.receber_encomenda(numero, var_resultado.get())
                messagebox.showinfo("OK", f"Encomenda {numero} marcada como recebida.", parent=win)
                win.destroy()
            except Exception as ex:
                messagebox.showerror("Erro", str(ex), parent=win)

        ttk.Button(btn_f, text="Confirmar", command=_confirmar).pack(side="left", padx=6)
        ttk.Button(btn_f, text="Cancelar", command=win.destroy).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Pagar
    # ------------------------------------------------------------------

    def _pagar_encomenda(self):
        encomendas = self.controller.listar_encomendas("pagar")
        if not encomendas:
            self.informuser("Info", "Não existem encomendas prontas a pagar.")
            return

        mapa_forn = self.controller.get_mapa_fornecedores()
        win = tk.Toplevel(self.root)
        win.title("Pagar Encomenda")
        win.resizable(False, False)
        BG.make_modal(win, self.root)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Encomenda:").grid(row=0, column=0, sticky="w", pady=4)
        numeros = [e.numero for e in encomendas]
        self._enc_pagar_map = {e.numero: e for e in encomendas}

        cb_enc = self.criar_combobox_autocomplete(
            frame, valores=numeros, largura=20, placeholder="Selecione...",
        )
        cb_enc.grid(row=0, column=1, sticky="w", pady=4)

        lbl_info = ttk.Label(frame, text="", foreground="gray")
        lbl_info.grid(row=1, column=0, columnspan=2, sticky="w")

        def _on_sel(event=None):
            e = self._enc_pagar_map.get(cb_enc.get())
            if e:
                nome = mapa_forn.get(str(e.fornecedor_id), e.fornecedor_id)
                lbl_info.config(text=f"{nome}  |  {e.descricao}  |  {e.valor:,.2f} €")

        cb_enc.bind("<<ComboboxSelected>>", _on_sel)

        btn_f = ttk.Frame(frame)
        btn_f.grid(row=2, column=0, columnspan=2, pady=12)

        def _confirmar():
            numero = cb_enc.get().strip()
            if numero not in self._enc_pagar_map:
                messagebox.showerror("Erro", "Selecione uma encomenda.", parent=win)
                return
            try:
                self.controller.pagar_encomenda(numero)
                messagebox.showinfo("OK", f"Encomenda {numero} marcada como paga.", parent=win)
                win.destroy()
            except Exception as ex:
                messagebox.showerror("Erro", str(ex), parent=win)

        ttk.Button(btn_f, text="Confirmar Pagamento", command=_confirmar).pack(side="left", padx=6)
        ttk.Button(btn_f, text="Cancelar", command=win.destroy).pack(side="left", padx=6)
