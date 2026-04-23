# atrpt/presentation/aprovisionamento/pedido_proposta_gui.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from presentation.shared.base_gui import BaseGui as BG
import traceback
import logging

logger = logging.getLogger(__name__)

class JuntarPropostaGUI(BG):
    """
    Abre dentro da área de trabalho (não modal).
    Mostra pedidos elegíveis (não aprovado/cancelado/concluido)
    e permite adicionar uma proposta ao pedido seleccionado.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.fornecedores_obj: dict[str, str] = {}   # nome → id
        self._pedido_seleccionado = None
        self._build()

    def _build(self):
        frame = self.abrir_work_area()

        # ── título ────────────────────────────────────
        tk.Label(
            frame,
            text="Adicionar Proposta",
            font=self.FONT_TITLE,
            bg=self.BG, fg=self.FG,
        ).pack(anchor="w", padx=10, pady=(10, 0))

        tk.Label(
            frame,
            text="Seleccione o pedido e preencha os dados da proposta",
            font=self.FONT_SUB,
            bg=self.BG, fg=self.FG,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # ── lista de pedidos ──────────────────────────
        lista_frame = tk.Frame(frame, bg=self.BG)
        lista_frame.pack(fill="x", padx=10, pady=4)

        cols = ("numero", "descricao", "estado", "propostas")
        self.tree = ttk.Treeview(
            lista_frame,
            columns=cols,
            show="headings",
            height=8,
            selectmode="browse",
        )
        self.tree.heading("numero",    text="Nº Pedido")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("estado",    text="Estado")
        self.tree.heading("propostas", text="Propostas")

        self.tree.column("numero",    width=90,  anchor="center")
        self.tree.column("descricao", width=350)
        self.tree.column("estado",    width=160, anchor="center")
        self.tree.column("propostas", width=80,  anchor="center")

        vsb = ttk.Scrollbar(lista_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_pedido_select)

        self._carregar_pedidos()

        # ── form proposta (oculto até seleccionar pedido) ──
        self.form_frame = tk.LabelFrame(
            frame,
            text="Nova Proposta",
            bg=self.BG, fg=self.FG,
            font=self.FONT_SUB,
        )
        # não pack aqui — aparece após selecção

        # fornecedor
        tk.Label(self.form_frame, text="Fornecedor:", bg=self.BG).grid(
            row=0, column=0, sticky="w", padx=10, pady=6
        )
        fornecedores = self._carregar_fornecedores()
        self.cb_fornecedor = self.criar_combobox_autocomplete(
            self.form_frame,
            valores=fornecedores,
            largura=40,
            placeholder="Digite para pesquisar...",
        )
        self.cb_fornecedor.grid(row=0, column=1, sticky="ew", padx=10, pady=6)

        # valor
        tk.Label(self.form_frame, text="Valor (€):", bg=self.BG).grid(
            row=1, column=0, sticky="w", padx=10, pady=6
        )
        self.ent_valor = tk.Entry(self.form_frame, width=20)
        self.ent_valor.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        # PDF
        tk.Label(self.form_frame, text="PDF Proposta:", bg=self.BG).grid(
            row=2, column=0, sticky="w", padx=10, pady=6
        )
        pdf_frame = tk.Frame(self.form_frame, bg=self.BG)
        pdf_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=6)
        self.ent_pdf = tk.Entry(pdf_frame, width=38)
        self.ent_pdf.pack(side="left", fill="x", expand=True)
        tk.Button(
            pdf_frame, text="📂",
            command=self._selecionar_pdf,
            bg=self.BTN_BG,
        ).pack(side="left", padx=4)

        # Anexos
        tk.Label(self.form_frame, text="Anexos:", bg=self.BG).grid(
            row=3, column=0, sticky="nw", padx=10, pady=6
        )
        anx_frame = tk.Frame(self.form_frame, bg=self.BG)
        anx_frame.grid(row=3, column=1, sticky="ew", padx=10, pady=6)

        # lista de anexos
        self.lst_anexos = tk.Listbox(anx_frame, height=4, width=42,
                                     selectmode="single")
        self.lst_anexos.pack(side="left", fill="x", expand=True)
        sb_anx = ttk.Scrollbar(anx_frame, orient="vertical",
                                command=self.lst_anexos.yview)
        self.lst_anexos.configure(yscrollcommand=sb_anx.set)
        sb_anx.pack(side="left", fill="y")

        # botões de gestão de anexos
        btn_anx = tk.Frame(self.form_frame, bg=self.BG)
        btn_anx.grid(row=4, column=1, sticky="w", padx=10, pady=(0, 6))
        tk.Button(btn_anx, text="➕ Adicionar", bg=self.BTN_BG,
                  command=self._adicionar_anexo).pack(side="left", padx=(0, 4))
        tk.Button(btn_anx, text="🗑 Remover", bg=self.BTN_BG,
                  command=self._remover_anexo).pack(side="left")

        self._anexos = []  # lista de {"id": None, "path": str}

        self.form_frame.columnconfigure(1, weight=1)

        # botão adicionar
        self.btn_adicionar = tk.Button(
            frame,
            text="Gravar Proposta",
            command=self._adicionar,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            state="disabled",
        )
        self.btn_adicionar.pack(pady=12)

    # --------------------------------------------------

    def _adicionar_anexo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Anexo",
            filetypes=[
                ("Documentos", "*.pdf *.xlsx *.xls *.docx *.doc"),
                ("PDF", "*.pdf"),
                ("Excel", "*.xlsx *.xls"),
                ("Word", "*.docx *.doc"),
                ("Todos", "*.*"),
            ]
        )
        if not path:
            return
        # se já existe pedido seleccionado, gravar imediatamente na BD
        if self._pedido_seleccionado:
            try:
                self.controller.adicionar_anexo(self._pedido_seleccionado, path)
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=self.root)
                return
        self._anexos.append({"id": None, "path": path})
        self.lst_anexos.insert(tk.END, path)

    def _remover_anexo(self):
        sel = self.lst_anexos.curselection()
        if not sel:
            return
        idx = sel[0]
        anexo = self._anexos[idx]
        if not messagebox.askyesno("Confirmar", "Remover este anexo?",
                                   parent=self.root):
            return
        if anexo.get("id") and self._pedido_seleccionado:
            try:
                self.controller.remover_anexo(anexo["id"])
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=self.root)
                return
        self._anexos.pop(idx)
        self.lst_anexos.delete(idx)

    def _carregar_anexos(self, pedido_numero: str):
        """Carrega anexos existentes de um pedido."""
        self._anexos.clear()
        self.lst_anexos.delete(0, tk.END)
        try:
            for anx in self.controller.listar_anexos(pedido_numero):
                self._anexos.append(anx)
                self.lst_anexos.insert(tk.END, anx["path"])
        except Exception:
            pass

    # --------------------------------------------------

    def _carregar_pedidos(self):
        self.tree.delete(*self.tree.get_children())
        pedidos = self.controller.listar_pedidos_para_proposta()
        if not pedidos:
            self.informuser(
                "Sem pedidos",
                "Não existem pedidos elegíveis para adicionar proposta."
            )
            return
        for p in pedidos:
            self.tree.insert("", "end", iid=str(p.numero), values=(
                p.numero,
                p.descricao[:60] if p.descricao else "",
                p.estado.value if hasattr(p.estado, 'value') else str(p.estado),
                len(p.propostas) if hasattr(p, 'propostas') else 0,
            ))

    def _carregar_fornecedores(self) -> list[str]:
        try:
            fornecedores = self.controller.get_fornecedor()
            self.fornecedores_obj = {f.nome: str(f.id) for f in fornecedores}
            return list(self.fornecedores_obj.keys())
        except Exception as e:
            return []

    def _on_pedido_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self._pedido_seleccionado = sel[0]   # iid = numero do pedido
        self.form_frame.pack(fill="x", padx=10, pady=6)
        self.btn_adicionar.config(state="normal")
        self._carregar_anexos(self._pedido_seleccionado)

    def _selecionar_pdf(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF da Proposta",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if path:
            self.ent_pdf.delete(0, tk.END)
            self.ent_pdf.insert(0, path)

    def _adicionar(self):             
        numero = self._pedido_seleccionado        
        if not numero:
            return
        fornecedor_nome = self.cb_fornecedor.get().strip()
        if fornecedor_nome == "Digite para pesquisar...":
            fornecedor_nome = ""
        if not fornecedor_nome or fornecedor_nome not in self.fornecedores_obj:
            messagebox.showerror("Erro", "Seleccione um fornecedor válido.", parent=self.root)
            return
        valor_str = self.ent_valor.get().strip()      
        if not valor_str:
            messagebox.showerror("Erro", "O valor é obrigatório.", parent=self.root)
            return
        try:
            valor = float(valor_str.replace(",", "."))
            self.escreveOutput(f"DEBUG: valor convertido = {valor}")
        except ValueError:
            self.escreveOutput(f"DEBUG: ERRO - valor inválido: '{valor_str}'")
            messagebox.showerror("Erro", "Valor inválido.", parent=self.root)
            return
        pdf_path = self.ent_pdf.get().strip() or None
        if not messagebox.askyesno(
        "Confirmar",
        f"Gravar proposta?\n\nFornecedor: {fornecedor_nome}\nValor: {valor:.2f} €\nPDF: {pdf_path or 'Sem documento'}",
        parent=self.root):
            return
        try:   
            resultado = self.controller.adicionar_proposta(
                numero=numero,
                fornecedor_id=self.fornecedores_obj[fornecedor_nome],
                valor=valor,
                documento=pdf_path,)                       
            messagebox.showinfo(
                "Sucesso",
                f"Proposta adicionada ao pedido {numero}.",
                parent=self.root,)            
            # limpar form e recarregar lista
            self.cb_fornecedor.set("")
            self.ent_valor.delete(0, tk.END)
            self.ent_pdf.delete(0, tk.END)
            self._anexos.clear()
            self.lst_anexos.delete(0, tk.END)
            self._pedido_seleccionado = None
            self.form_frame.pack_forget()
            self.btn_adicionar.config(state="disabled")
            self._carregar_pedidos()

        except Exception as e:
            # Capturar o erro completo
            self.escreveOutput(f"DEBUG: EXCEÇÃO - {str(e)}")
            self.escreveOutput(traceback.format_exc())
            messagebox.showerror("Erro", str(e), parent=self.root)
        
        self.escreveOutput("=" * 50)
        """Fecha a janela actual"""
        if messagebox.askyesno("Sair", "Tem certeza que deseja sair?", parent=self.root):
            self.root.destroy()