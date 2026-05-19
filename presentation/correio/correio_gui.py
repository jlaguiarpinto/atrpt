# presentation/correio/correio_gui.py
#
# Vista principal do leitor de correio (IMAP).
# Layout de 3 painéis:
#   esquerdo  — lista de pastas
#   direito-alto  — lista de mensagens (De, Assunto, Data)
#   direito-baixo — corpo da mensagem seleccionada

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG


class CorreioGUI(BG):

    def __init__(self, parent, controller, pasta_inicial: str | None = None):
        self._pasta_inicial = pasta_inicial
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar_pastas()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        pw_h = ttk.PanedWindow(outer, orient="horizontal")
        pw_h.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # ── painel esquerdo: pastas ───────────────────────────────────
        left = tk.Frame(pw_h, bg=self.BG, width=200)
        left.pack_propagate(False)
        pw_h.add(left, weight=0)

        tk.Label(left, text="Pastas", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 2))

        list_frame = tk.Frame(left, bg=self.BG)
        list_frame.pack(fill="both", expand=True, padx=(6, 0), pady=(0, 6))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.lst_pastas = tk.Listbox(
            list_frame, activestyle="dotbox", selectmode="browse",
            font=("Segoe UI", 9), relief="flat", borderwidth=1,
        )
        sb_p = ttk.Scrollbar(list_frame, orient="vertical", command=self.lst_pastas.yview)
        self.lst_pastas.configure(yscrollcommand=sb_p.set)
        self.lst_pastas.grid(row=0, column=0, sticky="nsew")
        sb_p.grid(row=0, column=1, sticky="ns")
        self.lst_pastas.bind("<<ListboxSelect>>", self._on_pasta_select)

        # ── painel direito ────────────────────────────────────────────
        right = tk.Frame(pw_h, bg=self.BG)
        pw_h.add(right, weight=1)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        pw_v = ttk.PanedWindow(right, orient="vertical")
        pw_v.grid(row=0, column=0, sticky="nsew")

        # ── lista de mensagens ────────────────────────────────────────
        top = tk.Frame(pw_v, bg=self.BG)
        pw_v.add(top, weight=1)
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)

        cols = ("de", "assunto", "data")
        self.tree_msgs = ttk.Treeview(
            top, columns=cols, show="headings", selectmode="browse", height=12,
        )
        cfg = {
            "de":      ("De",      220, "w"),
            "assunto": ("Assunto", 420, "w"),
            "data":    ("Data",    180, "w"),
        }
        for c, (lbl, w, a) in cfg.items():
            self.tree_msgs.heading(c, text=lbl)
            self.tree_msgs.column(c, width=w, anchor=a, minwidth=60)

        self.tree_msgs.tag_configure("nao_lida", font=("Segoe UI", 9, "bold"))
        self.tree_msgs.tag_configure("lida",     font=("Segoe UI", 9))

        sb_m = ttk.Scrollbar(top, orient="vertical", command=self.tree_msgs.yview)
        self.tree_msgs.configure(yscrollcommand=sb_m.set)
        self.tree_msgs.grid(row=0, column=0, sticky="nsew")
        sb_m.grid(row=0, column=1, sticky="ns")
        self.tree_msgs.bind("<<TreeviewSelect>>", self._on_msg_select)

        # ── corpo da mensagem ─────────────────────────────────────────
        bot = tk.Frame(pw_v, bg=self.BG)
        pw_v.add(bot, weight=1)
        bot.rowconfigure(1, weight=1)
        bot.columnconfigure(0, weight=1)

        self.lbl_headers = tk.Label(
            bot, text="", bg="#f0f0f0", fg="#333333",
            font=("Segoe UI", 8), anchor="w", justify="left",
            padx=6, pady=4,
        )
        self.lbl_headers.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.txt_corpo = tk.Text(
            bot, wrap="word", state="disabled",
            font=("Segoe UI", 9), bg="#fafafa", relief="flat",
        )
        sb_c = ttk.Scrollbar(bot, orient="vertical", command=self.txt_corpo.yview)
        self.txt_corpo.configure(yscrollcommand=sb_c.set)
        self.txt_corpo.grid(row=1, column=0, sticky="nsew")
        sb_c.grid(row=1, column=1, sticky="ns")

        # barra de status
        self.lbl_status = tk.Label(
            outer, text="", bg=self.BG, fg=self.FG,
            font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_status.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 2))

    # ------------------------------------------------------------------
    # Pastas
    # ------------------------------------------------------------------

    def _carregar_pastas(self):
        self.lst_pastas.delete(0, "end")
        self._set_status("A ligar…")
        self.frame.update_idletasks()

        if not self.controller.conectar_se_necessario():
            self._set_status("Erro: sem ligação ao servidor.")
            return

        pastas = self.controller.listar_pastas()
        for p in pastas:
            self.lst_pastas.insert("end", p)

        if pastas:
            if self._pasta_inicial and self._pasta_inicial in pastas:
                idx = pastas.index(self._pasta_inicial)
                self.lst_pastas.selection_set(idx)
                self.lst_pastas.see(idx)
                self._carregar_mensagens(self._pasta_inicial)
            else:
                self.lst_pastas.selection_set(0)
                self._carregar_mensagens(pastas[0])
        else:
            self._set_status("Nenhuma pasta encontrada.")

    def _on_pasta_select(self, _event=None):
        sel = self.lst_pastas.curselection()
        if not sel:
            return
        pasta = self.lst_pastas.get(sel[0])
        self._carregar_mensagens(pasta)

    # ------------------------------------------------------------------
    # Lista de mensagens
    # ------------------------------------------------------------------

    def _carregar_mensagens(self, pasta: str):
        self.tree_msgs.delete(*self.tree_msgs.get_children())
        self._limpar_corpo()
        self._set_status(f"A carregar «{pasta}»…")
        self.frame.update_idletasks()

        msgs = self.controller.listar_mensagens(pasta)

        for m in msgs:
            tag = "lida" if m["lida"] else "nao_lida"
            self.tree_msgs.insert("", "end", iid=m["uid"], tags=(tag,), values=(
                m["de"],
                m["assunto"],
                m["data"],
            ))

        n = len(msgs)
        self._set_status(f"{pasta}  —  {n} mensagem{'ns' if n != 1 else ''}")

    def _on_msg_select(self, _event=None):
        sel = self.tree_msgs.selection()
        if not sel:
            return
        uid = sel[0]
        self._set_status("A obter mensagem…")
        self.frame.update_idletasks()

        msg = self.controller.obter_mensagem(uid)
        if not msg:
            self._set_status("Erro ao obter mensagem.")
            return

        self.lbl_headers.config(
            text=(
                f"De: {msg['de']}\n"
                f"Para: {msg['para']}\n"
                f"Data: {msg['data']}\n"
                f"Assunto: {msg['assunto']}"
            )
        )
        self._mostrar_corpo(msg["corpo"])
        self._set_status("")

    # ------------------------------------------------------------------
    # Corpo
    # ------------------------------------------------------------------

    def _limpar_corpo(self):
        self.lbl_headers.config(text="")
        self.txt_corpo.configure(state="normal")
        self.txt_corpo.delete("1.0", "end")
        self.txt_corpo.configure(state="disabled")

    def _mostrar_corpo(self, texto: str):
        self.txt_corpo.configure(state="normal")
        self.txt_corpo.delete("1.0", "end")
        self.txt_corpo.insert("1.0", texto)
        self.txt_corpo.configure(state="disabled")
        self.txt_corpo.yview_moveto(0)

    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)
