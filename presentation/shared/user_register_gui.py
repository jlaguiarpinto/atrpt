# atrpt/presentation/shared/user_register_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from core.security import PERFIS


class userRegisterGUI:
    """
    Diálogo de registo de novo utilizador.
    Chamado quando o utilizador entra pela primeira vez.
    """

    @staticmethod
    def ask(parent, username: str) -> dict | None:
        """
        Abre diálogo modal e devolve dict com nome, email, nif, perfil
        ou None se cancelado.
        """
        result = {"dados": None}

        win = tk.Toplevel(parent)
        win.title("Primeiro Acesso — Registo")
        win.resizable(False, False)
        win.grab_set()
        win.lift()

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame,
                  text=f"Bem-vindo, {username}!\nPrimeiro acesso — preencha os seus dados.",
                  justify="center").grid(row=0, column=0, columnspan=2, pady=(0, 12))

        def _lbl(row, texto):
            ttk.Label(frame, text=texto).grid(
                row=row, column=0, sticky="w", pady=4, padx=(0, 8))

        def _entry(row, width=30):
            e = ttk.Entry(frame, width=width)
            e.grid(row=row, column=1, sticky="w", pady=4)
            return e

        _lbl(1, "Nome completo:*")
        ent_nome = _entry(1)

        _lbl(2, "Email:*")
        ent_email = _entry(2)

        _lbl(3, "NIF:")
        ent_nif = _entry(3, width=15)

        _lbl(4, "Perfil:*")
        perfil_opcoes = [f"{cod} — {desc}" for cod, desc in PERFIS.items()]
        cb_perfil = ttk.Combobox(frame, values=perfil_opcoes,
                                  state="readonly", width=30)
        cb_perfil.grid(row=4, column=1, sticky="w", pady=4)

        ttk.Label(frame, text="* obrigatório",
                  foreground="gray").grid(row=5, column=0, columnspan=2,
                                          sticky="w", pady=(8, 0))

        def _confirmar():
            nome  = ent_nome.get().strip()
            email = ent_email.get().strip()
            nif   = ent_nif.get().strip() or None
            perfil_sel = cb_perfil.get()

            if not nome:
                messagebox.showerror("Erro", "O nome é obrigatório.", parent=win)
                return
            if not email:
                messagebox.showerror("Erro", "O email é obrigatório.", parent=win)
                return
            if not perfil_sel:
                messagebox.showerror("Erro", "Seleccione o seu perfil.", parent=win)
                return

            # extrair código do perfil — "Dir — Direcção" → "Dir"
            perfil_cod = perfil_sel.split(" — ")[0].strip()

            result["dados"] = {
                "nome":   nome,
                "email":  email,
                "nif":    nif,
                "perfil": perfil_cod,
            }
            win.destroy()

        def _cancelar():
            win.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="Registar",  command=_confirmar).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancelar",  command=_cancelar).pack(side="left", padx=6)

        win.bind("<Return>", lambda e: _confirmar())
        ent_nome.focus_set()

        parent.wait_window(win)
        return result["dados"]
