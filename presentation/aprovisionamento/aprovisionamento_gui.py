# atrpt/presentation/aprovisionamento/aprovisionamneto_gui.py

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)
from presentation.shared.base_gui import BaseGui as BG
from presentation.aprovisionamento.pedido_autorizar_gui import AutorizarGUI
from presentation.aprovisionamento.pedido_encomendar_gui import EncomendarGUI
from presentation.aprovisionamento.fornecedores_gui import FornecedoresGUI
from presentation.aprovisionamento.pedidos_menu_gui import PedidosMenuGUI
from presentation.aprovisionamento.encomendas_gui import EncomendasMenuGUI

class AprovisionamentoGUI(BG):

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.set_title("Aprovisionamento")
        self._build_main_menu()
        # registar callback para restaurar o friso raiz ao fazer go_back
        self._restore_root_menu = self._build_main_menu

    def _build_main_menu(self):

        frame = self.abrir_work_area()
        #self.build_header(frame,"Módulo Aprovisionamento","Gestão de pedidos, fornecedores e encomendas")

        opcoes = [
            ("Pedidos de Compra", self._open_pedidos),
            ("Encomendas", self._open_encomendas),
            ("Fornecedores", self._open_fornecedores),
            ("Relatórios", self._open_relatorios)
        ]

        self.build_menu_buttons(opcoes)

    def _open_pedidos(self):
        self.show_view(PedidosMenuGUI, self.controller)

    def _open_encomendas(self):
        self.show_view(EncomendasMenuGUI, self.controller)

    def _open_fornecedores(self):
        self.show_view(FornecedoresGUI, self.controller)


    def form_fornecedor_dialog(self):
        from presentation.aprovisionamento.pedido_gui_forms import form_fornecedor_dialog
        return form_fornecedor_dialog(self.root)

    def mostrar_lista_fornecedores(self, fornecedores):

        texto = "\n".join([
            f"{f.id} | {f.nome} | {f.nif or ''}"
            for f in fornecedores
        ])

        self.informuser("Fornecedores", texto or "Sem registos")

    def _open_relatorios(self):
        self.informuser("Info", "Ainda não implementado.")

class PedidosMenuGUI(BG):                                          #   Sub-menu Pedidos de Compra

    def __init__(self, parent, controller):                                      
        super().__init__(parent, controller)
        # _build é chamado via _post_init pelo show_view, após injecção dos frames

    def _post_init(self):
        self._build()


    # Estados conhecidos — ajustar conforme o domínio
    ESTADOS_DISPONIVEIS = ["criado","pendente", "autorizado", "encomendado", "recebido", "cancelado"]

    def _build(self):
        opcoes = [
            ("Criar Pedido",       self._criar_pedido),
            ("Adicionar Proposta", self._adicionar_proposta),
            ("Listar Pedidos",     self._dialogo_listar_pedidos),
            ("Pedir Aprovação",    self._pedir_aprovacao),
            ("Autorizar",          self._autorizar),
            ("Encomendar",         self._encomendar),
        ]
        self.build_menu_buttons(opcoes)

    # ------------------------------------------------------------------
    # get_pedidos — método central reutilizável (GUI + dropdowns, etc.)
    #   estados: None ou [] → todos
    #            ["Pendente"] → só pendentes
    #            ["Pendente", "Autorizado"] → pendentes e autorizados
    # ------------------------------------------------------------------
    def get_pedidos(self, estados=None):
        """estados=None → todos; estados=[...] → filtrado na query."""
        if estados:
            return self.controller.listar_pedidos(*estados)
        return self.controller.listar_pedidos()

    def _dialogo_listar_pedidos(self):
        """Abre um diálogo para o utilizador escolher os estados a filtrar."""
        win = tk.Toplevel(self.root)
        win.title("Filtrar Pedidos")
        win.resizable(False, False)
        BG.make_modal(win, self.root)
        ttk.Label(win, text="Selecione os estados a listar:").pack(padx=16, pady=(12, 4))
        vars_estados = {}
        for estado in self.ESTADOS_DISPONIVEIS:
            var = tk.BooleanVar(value=False)
            vars_estados[estado] = var
            ttk.Checkbutton(win, text=estado, variable=var).pack(anchor="w", padx=24)

        ttk.Label(win, text="(nenhum selecionado = todos)", foreground="gray").pack(pady=(4, 0))

        def _confirmar():
            selecionados = [e for e, v in vars_estados.items() if v.get()]
            win.destroy()
            pedidos = self.get_pedidos(selecionados or None)
            self._mostrar_pedidos(pedidos)

        ttk.Button(win, text="Listar", command=_confirmar).pack(pady=10)
        self.root.wait_window(win)

    def _mostrar_pedidos(self, pedidos):
        """Mostra pedidos (zona superior) e propostas do pedido selecionado (zona inferior).
        O nome do fornecedor é resolvido via controller.
        Duplo clique no path de uma proposta abre o documento.
        """
        if not pedidos:
            self.informuser("Info", "Nenhum pedido encontrado.")
            return

        # mapa id → nome para resolução de fornecedores
        mapa_fornecedores = self.controller.get_mapa_fornecedores()

        win = tk.Toplevel(self.root)
        win.title("Lista de Pedidos")
        win.geometry("1000x640")
        win.resizable(True, True)

        # ---------- zona superior: pedidos ----------
        frame_top = ttk.LabelFrame(win, text="Pedidos", padding=6)
        frame_top.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        cols_pedidos = ("Número", "Centro Custo", "Descrição", "Estado", "Criado Por")
        tree_pedidos = ttk.Treeview(frame_top, columns=cols_pedidos, show="headings", height=10)

        col_widths = {"Número": 90, "Centro Custo": 120, "Descrição": 300, "Estado": 160, "Criado Por": 120}
        for col in cols_pedidos:
            tree_pedidos.heading(col, text=col)
            tree_pedidos.column(col, width=col_widths.get(col, 120), anchor="w")

        sb_top = ttk.Scrollbar(frame_top, orient="vertical", command=tree_pedidos.yview)
        tree_pedidos.configure(yscrollcommand=sb_top.set)
        tree_pedidos.pack(side="left", fill="both", expand=True)
        sb_top.pack(side="right", fill="y")

        pedido_por_iid = {}
        for pedido in pedidos:
            iid = tree_pedidos.insert("", "end", values=(
                getattr(pedido, 'numero', 'N/A'),
                getattr(pedido, 'centro_custo', 'N/A'),
                getattr(pedido, 'descricao', 'N/A')[:60],
                getattr(pedido, 'estado', 'N/A'),
                getattr(pedido, 'criado_por', 'N/A'),
            ))
            pedido_por_iid[iid] = pedido

        # ---------- zona inferior: propostas ----------
        frame_bot = ttk.LabelFrame(win, text="Propostas do pedido selecionado", padding=6)
        frame_bot.pack(fill="x", padx=10, pady=(4, 0))

        cols_prop = ("Fornecedor", "Valor (€)", "Documento / PDF")
        tree_prop = ttk.Treeview(frame_bot, columns=cols_prop, show="headings", height=6)

        tree_prop.heading("Fornecedor",      text="Fornecedor")
        tree_prop.heading("Valor (€)",       text="Valor (€)")
        tree_prop.heading("Documento / PDF", text="Documento / PDF   ✦ duplo clique para abrir")

        tree_prop.column("Fornecedor",      width=210, anchor="w")
        tree_prop.column("Valor (€)",       width=110, anchor="e")
        tree_prop.column("Documento / PDF", width=560, anchor="w")

        tree_prop.tag_configure("com_pdf", foreground="#1a6bbf")   # azul → clicável
        tree_prop.tag_configure("sem_pdf", foreground="gray")

        sb_bot = ttk.Scrollbar(frame_bot, orient="vertical", command=tree_prop.yview)
        tree_prop.configure(yscrollcommand=sb_bot.set)
        tree_prop.pack(side="left", fill="both", expand=True)
        sb_bot.pack(side="right", fill="y")

        # ---------- etiqueta de resumo ----------
        lbl_resumo = ttk.Label(win, text="", foreground="gray")
        lbl_resumo.pack(anchor="w", padx=12, pady=(2, 0))

        # ---------- callback: selecção de pedido ----------
        def _on_pedido_select(event):
            sel = tree_pedidos.selection()
            tree_prop.delete(*tree_prop.get_children())
            if not sel:
                lbl_resumo.config(text="")
                return

            pedido = pedido_por_iid.get(sel[0])
            if not pedido:
                return

            propostas = getattr(pedido, 'propostas', [])
            if not propostas:
                lbl_resumo.config(text=f"Pedido {pedido.numero} — sem propostas registadas.")
                return

            for p in propostas:
                nome_forn = mapa_fornecedores.get(str(p.fornecedor_id), p.fornecedor_id)
                valor_fmt = f"{p.valor:,.2f}" if p.valor is not None else "—"
                path      = p.pdf_path or ""
                tag       = "com_pdf" if path else "sem_pdf"
                tree_prop.insert("", "end", values=(
                    nome_forn,
                    valor_fmt,
                    path if path else "— sem documento —",
                ), tags=(tag,))

            n = len(propostas)
            lbl_resumo.config(
                text=f"Pedido {pedido.numero} — {n} proposta{'s' if n != 1 else ''}"
                     "   |   Duplo clique numa linha azul para abrir o documento"
            )

        tree_pedidos.bind("<<TreeviewSelect>>", _on_pedido_select)

        # ---------- callback: duplo clique na proposta → abrir documento ----------
        def _on_proposta_dblclick(event):
            import os, subprocess, sys
            sel = tree_prop.selection()
            if not sel:
                return
            valores = tree_prop.item(sel[0], "values")
            path = valores[2] if valores else ""
            if not path or path.startswith("—"):
                return
            if not os.path.exists(path):
                tk.messagebox.showerror(
                    "Ficheiro não encontrado",
                    f"Não foi possível encontrar:\n{path}",
                    parent=win,
                )
                return
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            except Exception as exc:
                tk.messagebox.showerror("Erro", str(exc), parent=win)

        tree_prop.bind("<Double-1>", _on_proposta_dblclick)

        # ---------- botão fechar ----------
        ttk.Button(win, text="Fechar", command=win.destroy).pack(pady=8)


    def _criar_pedido(self):
        from presentation.aprovisionamento.pedido_form_gui import PedidoFormGUI
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        PedidoFormGUI(win, self.controller)
        self.root.wait_window(win)

    def _pedir_aprovacao(self):
        from presentation.aprovisionamento.pedido_pedir_aprovacao_gui import PedirAprovacaoGUI
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        PedirAprovacaoGUI(win, self.controller)
        self.root.wait_window(win)
    
    def _adicionar_proposta(self):
        from presentation.aprovisionamento.pedido_proposta_gui import JuntarPropostaGUI
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        JuntarPropostaGUI(win, self.controller)
        self.root.wait_window(win)

    def _autorizar(self):
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        AutorizarGUI(win, self.controller)
        self.root.wait_window(win)

    def _encomendar(self):
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        EncomendarGUI(win, self.controller)
        self.root.wait_window(win)

class FornecedoresListGUI:

    def __init__(self, parent, controller, fornecedores):

        self.controller = controller
        self.frame = parent

        self._build(fornecedores)

    def _build(self, fornecedores):

        tree = ttk.Treeview(
            self.frame,
            columns=("id", "nome", "nif", "email"),
            show="headings"
        )

        tree.heading("id", text="ID")
        tree.heading("nome", text="Nome")
        tree.heading("nif", text="NIF")
        tree.heading("email", text="Email")

        tree.column("id", width=60)
        tree.column("nome", width=250)
        tree.column("nif", width=120)
        tree.column("email", width=200)

        # inserir dados
        for f in fornecedores:
            tree.insert("", "end", values=(
                f.id,
                f.nome,
                f.nif or "",
                f.email or ""
            ))

        tree.pack(fill="both", expand=True)

        # scrollbar
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")



