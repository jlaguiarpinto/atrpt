# atrpt/utils/gerir_users.py
# Utilitário de gestão de utilizadores — corre directamente
# python utils/gerir_users.py

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# garantir que o projecto está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import load_config
from infrastructure.persistence.user_repository import UserRepositorySQL
from core.security import PERFIS

_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")

PERFIS_OPCOES = [""] + [f"{cod} — {desc}" for cod, desc in PERFIS.items()]


class GerirUsersApp:

    def __init__(self, root: tk.Tk, repo: UserRepositorySQL):
        self.root = root
        self.repo = repo
        root.title("Gestão de Utilizadores")
        root.geometry("820x500")
        root.resizable(True, True)
        self._build()
        self._carregar()

    def _build(self):
        # ── toolbar ──────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, pady=6)
        toolbar.pack(fill="x", padx=8)

        ttk.Button(toolbar, text="↻ Actualizar", command=self._carregar).pack(side="left", padx=4)
        ttk.Button(toolbar, text="✎ Editar seleccionado", command=self._editar).pack(side="left", padx=4)
        ttk.Button(toolbar, text="⊘ Desactivar", command=self._toggle_ativo).pack(side="left", padx=4)

        # ── treeview ─────────────────────────────────────────────────
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        cols = ("username", "nome", "email", "nif", "perfil", "ativo")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")

        hdrs = {"username": ("Username", 100), "nome": ("Nome", 200),
                "email": ("Email", 200), "nif": ("NIF", 100),
                "perfil": ("Perfil", 120), "ativo": ("Activo", 60)}
        for col, (lbl, w) in hdrs.items():
            self.tree.heading(col, text=lbl)
            self.tree.column(col, width=w, anchor="w")

        self.tree.tag_configure("inativo", foreground="gray")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._editar())

        # ── rodapé ───────────────────────────────────────────────────
        self.lbl_count = ttk.Label(self.root, text="", foreground="gray")
        self.lbl_count.pack(anchor="w", padx=10, pady=(0, 4))

    def _carregar(self):
        self.tree.delete(*self.tree.get_children())
        self._users = {}
        try:
            users = self.repo.list_all()
        except AttributeError:
            # list_all pode não existir — usar alternativa
            users = self._list_all_fallback()

        for u in users:
            perfil_desc = PERFIS.get(u.perfil, u.perfil or "—")
            tag = "" if u.ativo else "inativo"
            iid = self.tree.insert("", "end", tags=(tag,), values=(
                u.username,
                u.nome,
                u.email or "",
                u.nif or "",
                f"{u.perfil} — {perfil_desc}" if u.perfil else "—",
                "Sim" if u.ativo else "Não",
            ))
            self._users[iid] = u

        n = len(self._users)
        self.lbl_count.config(text=f"{n} utilizador{'es' if n != 1 else ''}")

    def _list_all_fallback(self):
        """Lê todos os users directamente via SQL se list_all não existir."""
        from domain.users.users import user as User
        with self.repo._connect() as conn:
            rows = conn.execute(
                "SELECT username, nome, email, nif, ativo, perfil FROM users ORDER BY nome"
            ).fetchall()
            result = []
            for r in rows:
                perms = [p[0] for p in conn.execute(
                    "SELECT recurso FROM permissions WHERE username=?", (r[0],)
                ).fetchall()]
                result.append(User(
                    username=r[0], nome=r[1], email=r[2],
                    nif=r[3], ativo=bool(r[4]),
                    permissions=perms,
                    perfil=r[5] if len(r) > 5 else None,
                ))
        return result

    def _sel(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione um utilizador.", parent=self.root)
            return None
        return self._users.get(sel[0])

    def _editar(self):
        u = self._sel()
        if not u:
            return

        win = tk.Toplevel(self.root)
        win.title(f"Editar — {u.username}")
        win.resizable(False, False)
        win.grab_set()

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        def _lbl(row, txt):
            ttk.Label(frame, text=txt).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))

        def _entry(row, valor, width=32):
            e = ttk.Entry(frame, width=width)
            e.insert(0, valor or "")
            e.grid(row=row, column=1, sticky="w", pady=4)
            return e

        ttk.Label(frame, text=f"Username: {u.username}",
                  font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        _lbl(1, "Nome:"); ent_nome  = _entry(1, u.nome)
        _lbl(2, "Email:"); ent_email = _entry(2, u.email)
        _lbl(3, "NIF:");   ent_nif   = _entry(3, u.nif, width=16)

        _lbl(4, "Perfil:")
        perfil_actual = f"{u.perfil} — {PERFIS.get(u.perfil,'')}" if u.perfil else ""
        cb_perfil = ttk.Combobox(frame, values=PERFIS_OPCOES, state="readonly", width=30)
        cb_perfil.set(perfil_actual)
        cb_perfil.grid(row=4, column=1, sticky="w", pady=4)

        _lbl(5, "Activo:")
        var_ativo = tk.BooleanVar(value=u.ativo)
        ttk.Checkbutton(frame, variable=var_ativo).grid(row=5, column=1, sticky="w")

        def _gravar():
            nome  = ent_nome.get().strip()
            email = ent_email.get().strip()
            nif   = ent_nif.get().strip() or None
            perfil_sel = cb_perfil.get()
            perfil_cod = perfil_sel.split(" — ")[0].strip() if perfil_sel else None
            ativo = var_ativo.get()

            if not nome or not email:
                messagebox.showerror("Erro", "Nome e email são obrigatórios.", parent=win)
                return

            with self.repo._connect() as conn:
                conn.execute(
                    "UPDATE users SET nome=?, email=?, nif=?, perfil=?, ativo=? WHERE username=?",
                    (nome, email, nif, perfil_cod, int(ativo), u.username)
                )

            messagebox.showinfo("OK", "Utilizador actualizado.", parent=win)
            win.destroy()
            self._carregar()

        btn = ttk.Frame(frame)
        btn.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(btn, text="Gravar",   command=_gravar).pack(side="left", padx=5)
        ttk.Button(btn, text="Cancelar", command=win.destroy).pack(side="left", padx=5)

        ent_nome.focus_set()

    def _toggle_ativo(self):
        u = self._sel()
        if not u:
            return
        novo = not u.ativo
        estado = "activar" if novo else "desactivar"
        if not messagebox.askyesno("Confirmar",
                                   f"Confirma {estado} o utilizador {u.nome}?",
                                   parent=self.root):
            return
        with self.repo._connect() as conn:
            conn.execute("UPDATE users SET ativo=? WHERE username=?",
                         (int(novo), u.username))
        self._carregar()


def main():
    cfg  = load_config(_APP_INI)
    repo = UserRepositorySQL(cfg.paths["atrpt_db"])

    root = tk.Tk()
    GerirUsersApp(root, repo)
    root.mainloop()


if __name__ == "__main__":
    main()
