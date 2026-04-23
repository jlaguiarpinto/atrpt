import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Teste autocomplete")

valores = ["Fornecedor Alpha", "Fornecedor Beta", "Fornecedor Gamma", "Delta Lda", "Epsilon SA"]

var = tk.StringVar()
combo = ttk.Combobox(root, textvariable=var, values=valores, width=30)
combo.pack(padx=20, pady=20)

def on_change(*args):
    texto = var.get()
    print(f"trace: '{texto}'")
    filtrados = [v for v in valores if texto.lower() in v.lower()] if texto else valores
    combo['values'] = filtrados
    if filtrados:
        try:
            combo.event_generate('<Down>')
        except:
            pass

var.trace_add("write", on_change)
root.mainloop()