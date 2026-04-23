#atrpt/presentation/tesouraria_validacao_gui.py
import tkinter as tk
from tkinter import ttk, messagebox


class TesourariaValidacaoGUI(tk.Toplevel):

    def __init__(self, parent, df, residentes_lookup=None):
        super().__init__(parent)

        self.title("Validar Movimentos Tesouraria")

        self.df = df.copy()
        self.residentes_lookup = residentes_lookup or {}

        self.resultado = None
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.geometry("1100x500")

        self._build_ui()
        self._populate()

    # ------------------------------------------------------

    def _build_ui(self):

        self.tree = ttk.Treeview(
            self,
            columns=list(self.df.columns),
            show="headings"
        )

        for col in self.df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130)

        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self._on_double_click)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Confirmar e Registar",
            command=self._confirmar
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame,
            text="Cancelar",
            command=self.destroy
        ).pack(side="left", padx=10)

    # ------------------------------------------------------

    def _populate(self):

        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=list(row))

    # ------------------------------------------------------

    def _on_double_click(self, event):

        item_id = self.tree.focus()
        if not item_id:
            return

        row_index = self.tree.index(item_id)

        # construir dict com nomes de coluna
        row_values = self.tree.item(item_id)["values"]
        row_dict = dict(zip(self.df.columns, row_values))

        EditarMovimentoGUI(
            parent=self,
            row_data=row_dict, residentes_lookup=self.residentes_lookup,
            callback=lambda novos_dados: self._atualizar_linha(
                item_id,
                row_index,
                novos_dados))

    # ------------------------------------------------------

    def _atualizar_linha(self, item_id, row_index, novos_dados):

        for col in self.df.columns:
            valor = novos_dados[col]
            if self.df[col].dtype == "float64":
                try:
                    valor = float(valor)
                except:
                    valor = 0.0
            elif str(self.df[col].dtype) == "Int64":
                try:
                    valor = int(valor)
                except:
                    valor = None
            self.df.at[row_index, col] = valor
        valores_ordenados = [self.df.at[row_index, col] for col in self.df.columns]
        self.tree.item(item_id, values=valores_ordenados)

    # ------------------------------------------------------

    def _confirmar(self):
        if self.df["tipo"].isna().any():
            messagebox.showerror("Erro", "Existem movimentos sem Tipo.")
            return
        self.resultado = self.df.copy()
        self.destroy()

class EditarMovimentoGUI(tk.Toplevel):

    TIPOS = [
        "Mensalidade",
        "PIM",
        "Mensalidade + PIM",
        "Caução",
        "Almoço",
        "Quota",
        "Financeiro",
        "P/ averiguar"
    ]

    def __init__(self, parent, row_data, residentes_lookup, callback):
        super().__init__(parent)

        self.title("Editar Movimento")

        self.row_data = dict(row_data)
        self.residentes_lookup = residentes_lookup or{}
        self.callback = callback

        self.geometry("350x220")
        self._build_ui()

    # ------------------------------------------------------

    def _build_ui(self):

        tk.Label(self, text="Nº de Residente").pack(pady=5)

        self.entry_num = tk.Entry(self)
        self.entry_num.insert(0, self.row_data.get("numero_residente", ""))
        self.entry_num.pack()

        tk.Label(self, text="tipo").pack(pady=5)

        self.combo_tipo = ttk.Combobox(
            self,
            values=self.TIPOS,
            state="readonly"
        )
        self.combo_tipo.set(self.row_data.get("tipo", ""))
        self.combo_tipo.pack()

        tk.Button(
            self,
            text="Aceitar",
            command=self._aceitar
        ).pack(pady=15)

    # ------------------------------------------------------

    def _aceitar(self):

        try:
            novo_num = int(self.entry_num.get())
        except ValueError:
            messagebox.showerror("Erro", "Número inválido.")
            return

        novo_tipo = self.combo_tipo.get()
        if not novo_tipo:
            messagebox.showerror("Erro", "Tipo obrigatório.")
            return

        # atualizar Num
        self.row_data["numero_residente"] = novo_num

        # atualizar Nome automaticamente
        novo_nome = self.residentes_lookup.get(novo_num, "")
        self.row_data["nome"] = novo_nome

        # atualizar Tipo
        self.row_data["tipo"] = novo_tipo

        self.callback(self.row_data)

        self.destroy()