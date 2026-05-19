# atrpt/presentation/aprovisionamento/pedido_autorizar_gui.py

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG


class AutorizarGUI(BG):
    """
    Formulário para autorizar ou recusar pedidos em estado 'pendente'.

    Fluxo:
      1. Combobox com pedidos em estado 'pendente'
      2. Ao seleccionar, mostra descrição e TODAS as propostas:
           ★ laranja  — proposta sinalizada pelo requerente (pré-seleccionada)
           azul        — válida com PDF
           verde       — válida sem PDF
           cinzento    — incompleta (não seleccionável)
      3. O autorizador pode manter a proposta sinalizada ou escolher outra válida
      4. Botões: Autorizar | Recusar | Fechar
    """

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Autorizar Pedido")
        self._pedidos_map      = {}
        self._mapa_forn        = {}
        self._proposta_sel     = None
        self._validas          = []
        self._validas_iids     = []
        self._proposta_por_iid = {}
        # Remover zona de logs — formulário modal não precisa de output
        if hasattr(self, 'frame_logs') and self.frame_logs.winfo_exists():
            paned = self.frame_logs.master
            paned.forget(self.frame_logs)
            self.frame_logs.destroy()
            self.frame_logs = None
            self.txt_output = None
        self._build()

    def _build(self):
        frame = self.abrir_work_area()
        frame.columnconfigure(1, weight=1)

        # ── pedidos pendentes ──────────────────────────────────────────
        pedidos = self.controller.listar_pedidos("pendente")
        self._pedidos_map = {p.numero: p for p in pedidos}
        self._mapa_forn   = self.controller.get_mapa_fornecedores()
        numeros = list(self._pedidos_map.keys())

        ttk.Label(frame, text="Pedido:").grid(row=0, column=0, sticky="w", pady=4)
        self.cb_pedido = self.criar_combobox_autocomplete(
            frame, valores=numeros, largura=24,
            placeholder="Selecione o pedido..." if numeros else "Sem pedidos pendentes",
        )
        self.cb_pedido.grid(row=0, column=1, sticky="w", pady=4)
        self.cb_pedido.bind("<<ComboboxSelected>>", self._on_pedido_select)

        # ── detalhe do pedido (oculto até seleccionar) ────────────────
        self.frame_info = ttk.LabelFrame(frame, text="Detalhe do Pedido", padding=6)
        self.frame_info.columnconfigure(1, weight=1)

        for i, (lbl_text, attr) in enumerate([
            ("Descrição:",    "_lbl_desc"),
            ("Centro Custo:", "_lbl_cc"),
            ("Estado:",       "_lbl_estado"),
            ("Criado por:",   "_lbl_criado"),
        ]):
            ttk.Label(self.frame_info, text=lbl_text, foreground="gray").grid(
                row=i, column=0, sticky="w", padx=(0, 10), pady=2)
            lbl = ttk.Label(self.frame_info, text="")
            lbl.grid(row=i, column=1, sticky="w", pady=2)
            setattr(self, attr, lbl)

        # ── propostas ─────────────────────────────────────────────────
        self.frame_prop = ttk.LabelFrame(frame, text="Propostas", padding=6)
        self.frame_prop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.frame_prop.columnconfigure(0, weight=1)

        cols = ("Fornecedor", "Valor (€)", "PDF")
        self.tree = ttk.Treeview(
            self.frame_prop, columns=cols, show="headings",
            height=6, selectmode="browse",
        )
        self.tree.heading("Fornecedor", text="Fornecedor")
        self.tree.heading("Valor (€)",  text="Valor (€)")
        self.tree.heading("PDF",        text="PDF   ✦ duplo clique para abrir")
        self.tree.column("Fornecedor", width=240, anchor="w")
        self.tree.column("Valor (€)",  width=100, anchor="e")
        self.tree.column("PDF",        width=280, anchor="w")

        # sinalizada = laranja/bold; com_pdf = azul; valida = verde; incompleta = cinzento
        self.tree.tag_configure("sinalizada",  foreground="#b85c00", font=("", 9, "bold"))
        self.tree.tag_configure("com_pdf",     foreground="#1a6bbf")
        self.tree.tag_configure("valida",      foreground="#1a7a1a")
        self.tree.tag_configure("incompleta",  foreground="gray")

        vsb = ttk.Scrollbar(self.frame_prop, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.lbl_sel = ttk.Label(self.frame_prop, text="", foreground="gray")
        self.lbl_sel.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.tree.bind("<<TreeviewSelect>>", self._on_proposta_select)
        self.tree.bind("<Double-1>",         self._abrir_pdf)

        # ── botões ────────────────────────────────────────────────────
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=12)

        self.btn_autorizar = ttk.Button(
            btn_frame, text="✔ Autorizar", command=self._autorizar, state="disabled"
        )
        self.btn_autorizar.pack(side="left", padx=6)

        self.btn_nao_autorizar = ttk.Button(
            btn_frame, text="↩ Não Autorizar", command=self._nao_autorizar, state="disabled"
        )
        self.btn_nao_autorizar.pack(side="left", padx=6)

        self.btn_recusar = ttk.Button(
            btn_frame, text="✖ Recusar", command=self._recusar, state="disabled"
        )
        self.btn_recusar.pack(side="left", padx=6)

        ttk.Button(btn_frame, text="Fechar", command=self.root.destroy).pack(side="left", padx=6)

    # ------------------------------------------------------------------

    @staticmethod
    def _mesma_proposta(p1, p2) -> bool:
        if p1 is None or p2 is None:
            return False
        return (str(p1.fornecedor_id) == str(p2.fornecedor_id)
                and p1.valor == p2.valor)

    def _on_pedido_select(self, event=None):
        numero = self.cb_pedido.get().strip()
        pedido = self._pedidos_map.get(numero)
        if not pedido:
            return

        # detalhe do pedido
        self._lbl_desc.config(text=pedido.descricao or "—")
        self._lbl_cc.config(text=pedido.centro_custo or "—")
        self._lbl_estado.config(text=str(getattr(pedido, "estado", "—")))
        self._lbl_criado.config(text=pedido.criado_por or "—")
        self.frame_info.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 4))

        # reset
        self._proposta_sel     = None
        self._validas          = []
        self._validas_iids     = []
        self._proposta_por_iid = {}
        self.btn_autorizar.config(state="disabled")
        self.btn_nao_autorizar.config(state="disabled")
        self.btn_recusar.config(state="disabled")
        self.tree.delete(*self.tree.get_children())

        todas = getattr(pedido, "propostas", []) or []
        if not todas:
            self.lbl_sel.config(text="⚠  Sem propostas registadas neste pedido.", foreground="red")
            return

        proposta_sinalizada = getattr(pedido, "proposta_selecionada", None)
        validas_ids = {id(p) for p in pedido.propostas_validas()}
        iid_sinalizada = None

        for i, p in enumerate(todas):
            iid      = str(i)
            is_sin   = self._mesma_proposta(p, proposta_sinalizada)
            is_val   = id(p) in validas_ids

            nome_raw = self._mapa_forn.get(str(p.fornecedor_id),
                                           str(p.fornecedor_id) if p.fornecedor_id else "—")
            nome     = f"★ {nome_raw}" if is_sin else nome_raw
            valor_s  = f"{p.valor:,.2f}" if p.valor else "—"
            pdf_s    = p.pdf_path or "— sem documento —"

            if is_sin:
                tag = "sinalizada"
                if is_val:
                    self._validas.append(p)
                    self._validas_iids.append(iid)
                    iid_sinalizada = iid
            elif is_val:
                tag = "com_pdf" if p.pdf_path else "valida"
                self._validas.append(p)
                self._validas_iids.append(iid)
            else:
                tag = "incompleta"

            self._proposta_por_iid[iid] = p
            self.tree.insert("", "end", iid=iid, values=(nome, valor_s, pdf_s), tags=(tag,))

        # ativar Recusar e Não Autorizar assim que há pedido selecionado
        self.btn_recusar.config(state="normal")
        self.btn_nao_autorizar.config(state="normal")

        if not self._validas:
            self.lbl_sel.config(
                text="⚠  Sem propostas válidas — adicione fornecedor e valor antes de autorizar.",
                foreground="red",
            )
            return

        # pré-seleccionar: sinalizada se existir, caso contrário única válida
        iid_pre = iid_sinalizada or (self._validas_iids[0] if len(self._validas) == 1 else None)
        if iid_pre:
            self.tree.selection_set(iid_pre)
            self._proposta_sel = self._proposta_por_iid[iid_pre]
            if iid_sinalizada:
                self.lbl_sel.config(
                    text="★ Proposta sinalizada pelo requerente — pode alterar antes de autorizar.",
                    foreground="#b85c00",
                )
            else:
                self.lbl_sel.config(
                    text="Proposta seleccionada automaticamente (única válida).",
                    foreground="gray",
                )
            self.btn_autorizar.config(state="normal")
        else:
            n = len(self._validas)
            self.lbl_sel.config(
                text=f"{n} propostas válidas — seleccione a proposta a adjudicar.",
                foreground="gray",
            )

    def _on_proposta_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid not in self._validas_iids:
            self.tree.selection_remove(iid)
            self.lbl_sel.config(
                text="⚠  Esta proposta está incompleta (sem fornecedor ou valor).",
                foreground="orange",
            )
            self._proposta_sel = None
            self.btn_autorizar.config(state="disabled")
            return

        self._proposta_sel = self._proposta_por_iid[iid]
        nome_raw = self._mapa_forn.get(
            str(self._proposta_sel.fornecedor_id), str(self._proposta_sel.fornecedor_id)
        )
        self.lbl_sel.config(
            text=f"Seleccionada: {nome_raw}  —  {self._proposta_sel.valor:,.2f} €",
            foreground="navy",
        )
        self.btn_autorizar.config(state="normal")

    def _abrir_pdf(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        p = self._proposta_por_iid.get(sel[0])
        if not p or not p.pdf_path:
            return
        path = p.pdf_path
        if not os.path.exists(path):
            messagebox.showerror("Ficheiro não encontrado", path, parent=self.root)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)

    def _autorizar(self):
        numero = self.cb_pedido.get().strip()
        if not numero or numero not in self._pedidos_map:
            messagebox.showerror("Erro", "Selecione um pedido.", parent=self.root)
            return
        if self._proposta_sel is None:
            messagebox.showerror("Erro", "Seleccione a proposta a adjudicar.", parent=self.root)
            return
        try:
            self.controller.autorizar_pedido(numero, self._proposta_sel)
        except ValueError as e:
            messagebox.showwarning("Não permitido", str(e), parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return

        messagebox.showinfo("OK", f"Pedido {numero} autorizado.", parent=self.root)
        self.root.destroy()

    def _nao_autorizar(self):
        numero = self.cb_pedido.get().strip()
        if not numero or numero not in self._pedidos_map:
            messagebox.showerror("Erro", "Selecione um pedido.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Confirmar",
            f"Não autorizar o pedido {numero}?\n\nO pedido será devolvido ao requerente para revisão (estado 'criado').",
            parent=self.root,
        ):
            return
        try:
            self.controller.nao_autorizar_pedido(numero)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return
        messagebox.showinfo("OK", f"Pedido {numero} devolvido ao requerente.", parent=self.root)
        self.root.destroy()

    def _recusar(self):
        numero = self.cb_pedido.get().strip()
        if not numero or numero not in self._pedidos_map:
            messagebox.showerror("Erro", "Selecione um pedido.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Confirmar Recusa",
            f"Recusar o pedido {numero}?\n\nO pedido passará a estado 'cancelado'.",
            parent=self.root,
        ):
            return
        try:
            self.controller.recusar_pedido(numero)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return
        messagebox.showinfo("OK", f"Pedido {numero} recusado.", parent=self.root)
        self.root.destroy()
