# atrpt/presentation/aprovisionamento/proposta_form_widget.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class PropostaFormWidget:
    """
    Widget reutilizável para capturar dados de uma proposta:
    - Fornecedor (combobox com autocomplete)
    - Valor (Entry)
    - PDF (Entry + botão para seleccionar)
    """
    
    def __init__(self, parent, controller, fornecedores_lista=None, fornecedores_obj=None, gui=None):
        """
        Inicializa o widget.
        
        Args:
            parent: widget pai onde o formulário será colocado
            controller: controller para aceder aos fornecedores
            fornecedores_lista: lista pré-carregada de nomes de fornecedores (opcional)
            fornecedores_obj: dicionário nome->id de fornecedores (opcional)
        """
        self.parent = parent
        self.controller = controller
        self.gui = gui or getattr(controller, 'gui', None)
        self.fornecedores_lista = fornecedores_lista
        self.fornecedores_obj = fornecedores_obj or {}
        
        self.cb_fornecedor = None
        self.ent_valor = None
        self.ent_pdf = None
        self.frame = None
        
    def build(self, parent_frame=None, row_start=0, show_label_frame=True, label_title="Dados da Proposta"):
        """
        Constrói o formulário.
        
        Args:
            parent_frame: frame onde colocar o formulário (usa self.parent se None)
            row_start: linha inicial para grid
            show_label_frame: se True, coloca dentro de um LabelFrame
            label_title: título do LabelFrame (se show_label_frame=True)
        
        Returns:
            tuple: (frame, ultima_linha_usada)
        """
        from presentation.shared.base_gui import BaseGui
        BG = BaseGui.BG
        target_frame = parent_frame if parent_frame else self.parent
        
        if show_label_frame:
            self.frame = tk.LabelFrame(
                target_frame,
                text=label_title,
                bg=self.parent.bg if hasattr(self.parent, 'bg') else target_frame.cget('bg'),
                fg=self.parent.fg if hasattr(self.parent, 'fg') else 'black',
                font=("Segoe UI", 9, "bold")
            )
            self.frame.pack(fill="x", padx=10, pady=6)
        else:
            self.frame = ttk.Frame(target_frame)
            self.frame.pack(fill="x", padx=10, pady=6)
        
        # Carregar fornecedores se necessário
        if not self.fornecedores_lista:
            self._carregar_fornecedores()
        
        # cor de fundo — LabelFrame (tk) suporta cget('bg'), ttk.Frame não
        _bg = self.frame.cget('bg') if show_label_frame else BG

        # Fornecedor
        tk.Label(self.frame, text="Fornecedor:", bg=_bg).grid(
            row=row_start, column=0, sticky="w", padx=10, pady=6
        )
        
        # Entry com autocomplete inline (Toplevel flutuante)
        self.cb_fornecedor = self._fazer_entry_autocomplete(
            self.frame, self.fornecedores_lista or [], largura=40
        )
        self.cb_fornecedor.grid(row=row_start, column=1, sticky="ew", padx=10, pady=6)


        
        # Valor
        tk.Label(self.frame, text="Valor (€):", bg=_bg).grid(
            row=row_start + 1, column=0, sticky="w", padx=10, pady=6
        )
        self.ent_valor = tk.Entry(self.frame, width=20)
        self.ent_valor.grid(row=row_start + 1, column=1, sticky="w", padx=10, pady=6)
        
        # PDF
        tk.Label(self.frame, text="PDF Proposta:", bg=_bg).grid(
            row=row_start + 2, column=0, sticky="w", padx=10, pady=6
        )
        pdf_frame = tk.Frame(self.frame, bg=_bg)
        pdf_frame.grid(row=row_start + 2, column=1, sticky="ew", padx=10, pady=6)
        
        self.ent_pdf = tk.Entry(pdf_frame, width=38)
        self.ent_pdf.pack(side="left", fill="x", expand=True)
        
        btn_bg = "#0078D4" if hasattr(self.parent, 'BTN_BG') else "#f0f0f0"
        tk.Button(
            pdf_frame, text="📂",
            command=self._selecionar_pdf,
            bg=btn_bg,
        ).pack(side="left", padx=4)
        
        # Configurar grid
        if show_label_frame:
            self.frame.columnconfigure(1, weight=1)
        
        return self.frame, row_start + 3
    
    def _fazer_entry_autocomplete(self, parent, valores, largura=30):
        """Entry com dropdown Toplevel — sem dependência de BaseGui."""
        placeholder = "Digite para pesquisar..."
        _dropdown = [None]  # referência mutável ao Toplevel

        entry = tk.Entry(parent, width=largura)
        entry.insert(0, placeholder)
        entry.config(foreground="gray")
        entry._valores = list(valores)

        def _focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground="black")
            # mostrar todos ao focar
            _mostrar(entry._valores)

        def _focus_out(e):
            entry.after(200, _check_focus)

        def _check_focus():
            try:
                foco = str(entry.focus_get())
                if _dropdown[0] and foco.startswith(str(_dropdown[0])):
                    return
            except Exception:
                pass
            _esconder()
            if not entry.get().strip():
                entry.insert(0, placeholder)
                entry.config(foreground="gray")

        def _esconder():
            if _dropdown[0]:
                _dropdown[0].destroy()
                _dropdown[0] = None

        def _mostrar(filtrados):
            _esconder()
            if not filtrados:
                return
            win = tk.Toplevel(entry)
            win.wm_overrideredirect(True)
            lb = tk.Listbox(win, height=min(8, len(filtrados)))
            lb.pack(fill="both", expand=True)
            for v in filtrados:
                lb.insert(tk.END, v)
            entry.update_idletasks()
            x = entry.winfo_rootx()
            y = entry.winfo_rooty() + entry.winfo_height()
            w = entry.winfo_width()
            win.geometry(f"{w}x{min(8, len(filtrados)) * 18}+{x}+{y}")
            win.lift()
            _dropdown[0] = win

            def _select(e):
                sel = lb.curselection()
                if sel:
                    valor = lb.get(sel[0])
                    entry.delete(0, tk.END)
                    entry.insert(0, valor)
                    entry.config(foreground="black")
                    _esconder()
            lb.bind("<ButtonRelease-1>", _select)

        def _keyrelease(e):
            if e.keysym in ("Escape", "Tab"):
                _esconder(); return
            if e.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
                return
            texto = entry.get().strip()
            if texto == placeholder:
                return
            filtrados = [v for v in entry._valores if texto.lower() in v.lower()] if texto else entry._valores
            _mostrar(filtrados)

        entry.bind("<FocusIn>",    _focus_in)
        entry.bind("<FocusOut>",   _focus_out)
        entry.bind("<KeyRelease>", _keyrelease)

        # interface compatível com o resto do código
        entry.get_value   = lambda: "" if entry.get() == placeholder else entry.get()
        entry.set_value   = lambda v: (entry.delete(0, tk.END), entry.insert(0, v), entry.config(foreground="black"))
        entry._esconder   = _esconder
        entry._valores_originais = list(valores)

        return entry

    def _criar_combobox_autocomplete(self, parent, valores, largura=30, placeholder=""):
        """Cria uma combobox com autocomplete — filtra enquanto digita, sem roubar foco."""
        from tkinter import ttk

        combo = ttk.Combobox(parent, values=valores, width=largura)
        combo._valores_base = list(valores)

        if placeholder:
            combo.insert(0, placeholder)
            combo.config(foreground="gray")

            def _focus_in(e):
                if combo.get() == placeholder:
                    combo.delete(0, tk.END)
                    combo.config(foreground="black")
            def _focus_out(e):
                if not combo.get().strip():
                    combo.insert(0, placeholder)
                    combo.config(foreground="gray")
            combo.bind('<FocusIn>',  _focus_in)
            combo.bind('<FocusOut>', _focus_out)

        def _on_key(event):
            if event.keysym in ('Down', 'Up', 'Return', 'Escape',
                                 'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                                 'Alt_L', 'Alt_R', 'Tab', 'BackSpace'):
                # BackSpace: repor lista completa se campo ficar vazio
                if event.keysym == 'BackSpace':
                    combo.after(10, _filtrar)
                return
            combo.after(10, _filtrar)

        def _filtrar():
            typed = combo.get().strip().lower()
            if typed == placeholder.lower() if placeholder else False:
                return
            base = combo._valores_base
            filtrados = [v for v in base if typed in v.lower()] if typed else base
            combo['values'] = filtrados

        combo.bind('<KeyRelease>', _on_key)
        return combo
    
    def _on_focus_in(self, event, var, placeholder):
        """Remove o placeholder ao focar"""
        if var.get() == placeholder:
            var.set("")
    
    def _on_focus_out(self, event, var, placeholder):
        """Restaura o placeholder se vazio"""
        if var.get().strip() == "":
            var.set(placeholder)
    
    # Tipos de relação excluídos da lista de fornecedores para pedidos
    _RELACOES_EXCLUIDAS = {"avençado", "prestador", "pontual"}

    def _carregar_fornecedores(self):
        """Carrega a lista de fornecedores do controller, excluindo avençados, prestadores e pontuais."""
        try:
            todos = self.controller.get_fornecedores()
            fornecedores = [
                f for f in todos
                if (f.tipo_relacao or "").strip().lower() not in self._RELACOES_EXCLUIDAS
            ]
            self.fornecedores_lista = [f.nome for f in fornecedores]
            self.fornecedores_obj = {f.nome: str(f.id) for f in fornecedores}
        except Exception as e:
            self.fornecedores_lista = []
            self.fornecedores_obj = {}

    def _verificar_novo_fornecedor(self, nome_digitado: str) -> bool:
        """
        Se o nome digitado não existe na lista, oferece criar o fornecedor.
        Devolve True se o fornecedor foi criado e adicionado à lista.
        """
        if not nome_digitado or nome_digitado in self.fornecedores_obj:
            return False

        import tkinter as tk
        from tkinter import ttk, messagebox

        root = self.cb_fornecedor.winfo_toplevel()

        if not messagebox.askyesno(
            "Fornecedor não encontrado",
            f"'{nome_digitado}' não existe.\nDeseja criar este fornecedor?",
            parent=root,
        ):
            return False

        # diálogo simples para nome e NIF
        win = tk.Toplevel(root)
        win.title("Novo Fornecedor")
        win.resizable(False, False)
        win.grab_set()

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nome:").grid(row=0, column=0, sticky="w", pady=4)
        ent_nome = ttk.Entry(frame, width=36)
        ent_nome.insert(0, nome_digitado)
        ent_nome.grid(row=0, column=1, pady=4)

        ttk.Label(frame, text="NIF:").grid(row=1, column=0, sticky="w", pady=4)
        ent_nif = ttk.Entry(frame, width=36)
        ent_nif.insert(0, "999999999")   # placeholder editável
        ent_nif.grid(row=1, column=1, pady=4)

        ttk.Label(
            frame,
            text="(NIF 999999999 aceite — actualizar posteriormente)",
            foreground="gray",
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        resultado = {"criado": False}

        def _gravar():
            nome = ent_nome.get().strip()
            nif  = ent_nif.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome é obrigatório.", parent=win)
                return
            if not nif:
                messagebox.showerror("Erro", "O NIF é obrigatório.", parent=win)
                return
            try:
                novo = self.controller.novo_fornecedor({"nome": nome, "nif": nif})
                # recarregar lista e actualizar combobox
                self._carregar_fornecedores()
                self.cb_fornecedor._valores = self.fornecedores_lista
                self.cb_fornecedor._valores_originais = self.fornecedores_lista
                self.cb_fornecedor.set_value(nome)
                resultado["criado"] = True
                win.destroy()
            except Exception as ex:
                messagebox.showerror("Erro", str(ex), parent=win)

        btn_f = ttk.Frame(frame)
        btn_f.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_f, text="Criar Fornecedor", command=_gravar).pack(side="left", padx=4)
        ttk.Button(btn_f, text="Cancelar", command=win.destroy).pack(side="left", padx=4)

        ent_nif.focus()
        root.wait_window(win)
        return resultado["criado"]
    
    def _selecionar_pdf(self):
        """Abre diálogo para seleccionar ficheiro PDF"""
        path = filedialog.askopenfilename(
            title="Seleccionar proposta PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if path:
            self.ent_pdf.delete(0, tk.END)
            self.ent_pdf.insert(0, path)
    
    def get_dados(self):
        """
        Obtém os dados do formulário.
        
        Returns:
            tuple: (fornecedor_id, valor, pdf_path) ou (None, None, None) se inválido
        """
        fornecedor_nome = self.cb_fornecedor.get().strip()
        
        # Verificar se é placeholder
        if hasattr(self.cb_fornecedor, 'get') and self.cb_fornecedor.get() in ["", "Digite para pesquisar..."]:
            return None, None, None
        
        if not fornecedor_nome or fornecedor_nome not in self.fornecedores_obj:
            return None, None, None
        
        valor_str = self.ent_valor.get().strip()
        if not valor_str:
            return None, None, None
        
        try:
            valor = float(valor_str.replace(",", "."))
        except ValueError:
            return None, None, None
        
        pdf_path = self.ent_pdf.get().strip() or None
        
        return self.fornecedores_obj[fornecedor_nome], valor, pdf_path
    
    def validar(self, show_errors=True, parent=None):
        """
        Valida os dados do formulário.
        
        Returns:
            tuple: (valido, fornecedor_id, valor, pdf_path)
        """
        fornecedor_nome = self.cb_fornecedor.get().strip()
        
        # Verificar placeholder
        if hasattr(self.cb_fornecedor, 'get') and self.cb_fornecedor.get() == "Digite para pesquisar...":
            if show_errors:
                messagebox.showerror("Erro", "Seleccione um fornecedor.", parent=parent)
            return False, None, None, None
        
        if not fornecedor_nome:
            if show_errors:
                messagebox.showerror("Erro", "Seleccione um fornecedor.", parent=parent)
            return False, None, None, None
        
        if fornecedor_nome not in self.fornecedores_obj:
            # oferecer criação de novo fornecedor
            criado = self._verificar_novo_fornecedor(fornecedor_nome)
            if not criado:
                if show_errors:
                    messagebox.showerror("Erro", "Fornecedor inválido.", parent=parent)
                return False, None, None, None
            # após criação o combobox já foi actualizado — reler nome
            fornecedor_nome = self.cb_fornecedor.get().strip()
            if fornecedor_nome not in self.fornecedores_obj:
                return False, None, None, None
        
        valor_str = self.ent_valor.get().strip()
        if not valor_str:
            if show_errors:
                messagebox.showerror("Erro", "Indique o valor.", parent=parent)
            return False, None, None, None
        
        try:
            valor = float(valor_str.replace(",", "."))
        except ValueError:
            if show_errors:
                messagebox.showerror("Erro", "Valor inválido.", parent=parent)
            return False, None, None, None
        
        pdf_path = self.ent_pdf.get().strip() or None
        
        return True, self.fornecedores_obj[fornecedor_nome], valor, pdf_path
    
    def limpar(self):
        """Limpa todos os campos do formulário"""
        if self.cb_fornecedor:
            if hasattr(self.cb_fornecedor, 'set'):
                self.cb_fornecedor.set("")
        if self.ent_valor:
            self.ent_valor.delete(0, tk.END)
        if self.ent_pdf:
            self.ent_pdf.delete(0, tk.END)
    
    def pack_forget(self):
        """Remove o frame da interface"""
        if self.frame:
            self.frame.pack_forget()
    
    def pack(self, **kwargs):
        """Mostra o frame na interface"""
        if self.frame:
            self.frame.pack(**kwargs)