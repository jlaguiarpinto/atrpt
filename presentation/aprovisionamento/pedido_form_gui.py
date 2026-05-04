# atrpt/presentation/aprovisionamento/pedido_form_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG
from presentation.aprovisionamento.proposta_form_widget import PropostaFormWidget
import logging
import os

logger = logging.getLogger(__name__)


class PedidoFormGUI(BG):
    """Formulário para criação de novo pedido."""

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Novo Pedido")
        self.centros_custo = self.controller.get_centros_custo()
        self._propostas_confirmadas = []   # lista de dicts já confirmados
        self._widget_ativo = None          # PropostaFormWidget em edição (ou None)
        self._frame_ativo  = None          # frame do widget em edição
        self._build()

    # ── construção da interface ───────────────────────────────────────────────

    def _build(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # Centro de Custo
        ttk.Label(frame, text="Centro de Custo:").grid(row=0, column=0, sticky="w")
        self.cb_cc = ttk.Combobox(
            frame, values=self.centros_custo, state="readonly", width=30,
        )
        self.cb_cc.grid(row=0, column=1, columnspan=2, pady=5, sticky="w")

        # Descrição
        ttk.Label(frame, text="Descrição:").grid(row=1, column=0, sticky="nw")
        self.txt_desc = tk.Text(frame, width=40, height=4)
        self.txt_desc.grid(row=1, column=1, columnspan=2, pady=5)

        # Secção de propostas
        self._lf_propostas = ttk.LabelFrame(frame, text="Propostas", padding=5)
        self._lf_propostas.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")
        self._lf_propostas.columnconfigure(0, weight=1)

        # listbox de propostas confirmadas
        ttk.Label(self._lf_propostas, text="Propostas confirmadas:",
                  foreground="gray").pack(anchor="w")
        self.lista_propostas = tk.Listbox(self._lf_propostas, height=4, width=70)
        self.lista_propostas.pack(fill="x", pady=(2, 6))

        # frame onde o widget de edição activo aparece
        self._frame_edicao = ttk.Frame(self._lf_propostas)
        self._frame_edicao.pack(fill="x")

        # botão "+ Adicionar proposta" — sempre visível, desactivado durante edição
        self.btn_adicionar = ttk.Button(
            self._lf_propostas,
            text="+ Adicionar proposta",
            command=self._abrir_nova_proposta,
        )
        self.btn_adicionar.pack(anchor="w", pady=(4, 0))

        # Botões principais
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Gravar Pedido", command=self._gravar).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Fechar",        command=self.root.destroy).pack(side="left", padx=5)

        # Abrir logo o primeiro formulário de proposta
        self._abrir_nova_proposta()

    # ── gestão de propostas ───────────────────────────────────────────────────

    def _abrir_nova_proposta(self):
        """Cria um novo PropostaFormWidget em edição, com botões Confirmar/Descartar."""
        if self._widget_ativo is not None:
            return  # já há um widget em edição

        self.btn_adicionar.config(state="disabled")

        self._frame_ativo = ttk.LabelFrame(
            self._frame_edicao, text="Nova proposta", padding=4
        )
        self._frame_ativo.pack(fill="x", pady=4)

        self._widget_ativo = PropostaFormWidget(
            self._frame_ativo, self.controller, gui=self
        )
        self._widget_ativo.build(parent_frame=self._frame_ativo, show_label_frame=False)

        # botões Confirmar / Descartar dentro do frame da proposta
        btn_f = ttk.Frame(self._frame_ativo)
        btn_f.pack(pady=(4, 0))
        ttk.Button(
            btn_f, text="✔ Confirmar",
            command=self._confirmar_proposta,
        ).pack(side="left", padx=4)
        ttk.Button(
            btn_f, text="✖ Descartar",
            command=self._descartar_proposta,
        ).pack(side="left", padx=4)

    def _confirmar_proposta(self):
        """Valida e move a proposta activa para a lista de confirmadas."""
        if self._widget_ativo is None:
            return
        valido, fornecedor_id, valor, pdf_path = self._widget_ativo.validar(
            show_errors=True, parent=self.root
        )
        if not valido:
            return

        fornecedor_nome = next(
            (n for n, fid in self._widget_ativo.fornecedores_obj.items()
             if fid == fornecedor_id),
            fornecedor_id,
        )
        self._propostas_confirmadas.append({
            "fornecedor_id":   fornecedor_id,
            "fornecedor_nome": fornecedor_nome,
            "valor":           valor,
            "documento":       pdf_path,
        })
        self.lista_propostas.insert(
            tk.END,
            f"{fornecedor_nome}  |  {valor:.2f} €"
            f"  |  {os.path.basename(pdf_path) if pdf_path else 'Sem PDF'}",
        )
        self._fechar_widget_ativo()

    def _descartar_proposta(self):
        """Descarta a proposta em edição sem gravar."""
        self._fechar_widget_ativo()

    def _fechar_widget_ativo(self):
        """Destrói o frame de edição e reactiva o botão Adicionar."""
        if self._frame_ativo:
            self._frame_ativo.destroy()
        self._frame_ativo  = None
        self._widget_ativo = None
        self.btn_adicionar.config(state="normal")

    # ── gravar pedido ─────────────────────────────────────────────────────────

    def _gravar(self):
        # se há proposta em edição, obrigar a confirmar ou descartar primeiro
        if self._widget_ativo is not None:
            messagebox.showwarning(
                "Proposta em edição",
                "Confirme ou descarte a proposta em edição antes de gravar o pedido.",
                parent=self.root,
            )
            return

        cc   = self.cb_cc.get().strip()
        desc = self.txt_desc.get("1.0", "end").strip()

        if not cc or not desc:
            messagebox.showerror(
                "Erro", "Centro de Custo e Descrição são obrigatórios.",
                parent=self.root,
            )
            return

        if not self._propostas_confirmadas:
            messagebox.showerror(
                "Erro", "É necessário confirmar pelo menos uma proposta.",
                parent=self.root,
            )
            return

        self.controller.criar_pedido(
            centro_custo=cc,
            descricao=desc,
            proposta=self._propostas_confirmadas,
        )

        messagebox.showinfo("OK", "Pedido criado com sucesso!", parent=self.root)
        self.root.destroy()
