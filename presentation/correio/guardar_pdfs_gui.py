# presentation/correio/guardar_pdfs_gui.py
#
# Fase 1 — Descarregar PDFs de faturas da caixa IMAP e guardar em disco.
#
# Nomeia cada ficheiro:  {fat|nc}_{5chars}_{YYYYMMDD}[_N].pdf
#   5chars = primeiros 5 alnum do nome do fornecedor (identificado pelo NIF do PDF).
#
# Pastas com "fatura/factura/invoice" no nome são pré-selecionadas.

import tkinter as tk
from tkinter import ttk, simpledialog
from presentation.shared.base_gui import BaseGui as BG

_FATURA_KEYS = ("fatura", "factura", "invoice", "fact")


class GuardarPdfsGUI(BG):

    def __init__(self, parent, controller):
        self._pastas_map = {}   # label listbox → nome IMAP real
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([("Ler e Guardar Faturas", self._guardar)])
        self._build()
        self._carregar_pastas()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=8)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── topo: destino ──────────────────────────────────────────────
        info = tk.Frame(outer, bg=self.BG)
        info.grid(row=0, column=0, sticky="new")

        tk.Label(info, text="Destino:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        destino = str(self.controller.pasta_faturas) if self.controller.pasta_faturas else "—"
        tk.Label(info, text=destino, bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=(6, 0))

        # ── pastas IMAP ────────────────────────────────────────────────
        tk.Label(outer, text="Pastas IMAP (selecione uma ou mais):",
                 bg=self.BG, fg=self.FG, font=("Segoe UI", 9, "bold"),
                 ).grid(row=1, column=0, sticky="w", pady=(12, 2))

        list_frame = tk.Frame(outer, bg=self.BG)
        list_frame.grid(row=2, column=0, sticky="nsew")
        outer.rowconfigure(2, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.lst = tk.Listbox(list_frame, selectmode="extended",
                              font=("Segoe UI", 9), relief="flat",
                              borderwidth=1, activestyle="dotbox")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.lst.yview)
        self.lst.configure(yscrollcommand=sb.set)
        self.lst.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # ── barra de estado ────────────────────────────────────────────
        self.lbl_status = tk.Label(
            outer, text="", bg=self.BG, fg=self.FG,
            font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_status.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    # ------------------------------------------------------------------
    # Carregar pastas IMAP
    # ------------------------------------------------------------------

    def _carregar_pastas(self):
        self._set_status("A ligar…")
        self.frame.update_idletasks()

        if not self.controller.conectar_se_necessario():
            self._set_status("Erro: sem ligação ao servidor.")
            return

        pastas_com_n = self.controller.listar_pastas_com_contagem()
        self.lst.delete(0, "end")
        self._pastas_map.clear()

        for pasta, n in sorted(pastas_com_n, key=lambda x: x[0].lower()):
            label = f"{pasta}  ({n})"
            self.lst.insert("end", label)
            self._pastas_map[label] = pasta
            if any(k in pasta.lower() for k in _FATURA_KEYS):
                self.lst.selection_set(self.lst.size() - 1)

        n_sel = len(self.lst.curselection())
        self._set_status(
            f"{len(pastas_com_n)} pasta(s) — {n_sel} pré-selecionada(s). "
            "Prima «Guardar PDFs» para iniciar."
        )

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        sel = self.lst.curselection()
        if not sel:
            self.informuser("Sem seleção", "Selecione pelo menos uma pasta.", "warning")
            return

        destino = self.controller.pasta_faturas
        if not destino:
            self.informuser("Sem destino",
                            "pasta_faturas não configurada no controller.", "error")
            return

        pastas = [self._pastas_map[self.lst.get(i)] for i in sel]

        total_guardados  = 0
        total_ignorados  = 0
        total_ja_existem = 0
        total_descon     = 0

        for pasta in pastas:
            self._set_status(f"A processar «{pasta}»…")
            self.frame.update_idletasks()

            def progresso(i, total, assunto, _p=pasta):
                self._set_status(f"«{_p}» — {i}/{total}: {assunto[:60]}…")
                self.frame.update_idletasks()

            ret = self.controller.guardar_pdfs_pasta(
                pasta, destino,
                callback=progresso,
                on_sem_dados=self._pedir_nif,
            )
            total_guardados  += ret["guardados"]
            total_ignorados  += ret["ignorados"]
            total_ja_existem += ret.get("ja_existem", 0)
            total_descon     += ret["nao_reconhecidos"]

        partes = [f"{total_guardados} PDF(s) guardado(s) em {destino}"]
        if total_ja_existem:
            partes.append(f"{total_ja_existem} já existia(m) — ignorado(s)")
        if total_ignorados:
            partes.append(f"{total_ignorados} recibo(s) ignorado(s)")
        if total_descon:
            partes.append(f"{total_descon} sem fornecedor → DESCON")
        self._set_status("  |  ".join(partes))

        if total_guardados:
            self.informuser(
                "Concluído",
                f"{total_guardados} PDF(s) guardado(s) em:\n{destino}",
            )

    # ------------------------------------------------------------------
    # Diálogo quando o NIF não foi encontrado no PDF nem no histórico
    # ------------------------------------------------------------------

    def _pedir_nif(self, pdf_nome: str, campos: dict) -> dict | None:
        """
        Mostra diálogo modal para o utilizador fornecer o NIF (e opcionalmente
        outros campos) quando o parser não os conseguiu extrair.
        Devolve dict com campos preenchidos, ou None para saltar este PDF.
        """
        dlg = tk.Toplevel(self.frame)
        dlg.title("Dados em falta")
        dlg.resizable(False, False)
        dlg.grab_set()

        resultado = {}

        # Informação do PDF
        tk.Label(dlg, text=f"PDF:  {pdf_nome}",
                 font=("Segoe UI", 9, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 2))

        _CAMPOS_DLGR = [
            ("nif",       "NIF emitente"),
            ("n_fatura",  "N.º Fatura"),
            ("data",      "Data emissão"),
            ("total",     "Total (€)"),
        ]
        entradas = {}
        for r, (chave, label) in enumerate(_CAMPOS_DLGR, 1):
            val = campos.get(chave)
            ok  = val is not None
            cor = "black" if ok else "red"
            tk.Label(dlg, text=label + ":", fg=cor,
                     font=("Segoe UI", 9), anchor="e", width=14).grid(
                row=r, column=0, sticky="e", padx=(12, 4), pady=2)
            var = tk.StringVar(value=str(val) if val is not None else "")
            ent = tk.Entry(dlg, textvariable=var, width=28,
                           fg=cor, font=("Segoe UI", 9))
            ent.grid(row=r, column=1, sticky="w", padx=(0, 12), pady=2)
            entradas[chave] = var

        def _ok():
            for chave, var in entradas.items():
                v = var.get().strip()
                if v:
                    resultado[chave] = v
            dlg.destroy()

        def _saltar():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.grid(row=len(_CAMPOS_DLGR) + 1, column=0, columnspan=2, pady=(8, 12))
        tk.Button(btn_frame, text="OK",     width=10, command=_ok).pack(side="left",  padx=6)
        tk.Button(btn_frame, text="Saltar", width=10, command=_saltar).pack(side="left", padx=6)

        # Focar no primeiro campo vazio
        for chave, var in entradas.items():
            if not var.get():
                entradas[chave]  # referência já existe; vamos focar o widget
                break
        dlg.wait_window()
        return resultado if resultado else None

    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)
