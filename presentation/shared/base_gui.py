# atrpt/presentation/shared/base_gui.py
#
# Layout fixo em todos os módulos:
#
#  ┌──────────────────────────────────────────────────────┐
#  │ TOPO:  Logo | Módulo – Submódulo          [Sair]     │
#  ├──────────────────────────────────────────────────────┤
#  │ MENU:  [Op1] [Op2] [Op3]          [← Voltar]        │
#  ├──────────────────────────────────────────────────────┤
#  │                                                      │
#  │  ÁREA DE TRABALHO  (conteúdo dinâmico)               │
#  │                                                      │
#  ├──────────────────────────────────────────────────────┤
#  │ LOGS  (8 linhas, fundo preto)                        │
#  └──────────────────────────────────────────────────────┘
#
# Regras:
#   - Menu = navegação entre ecrãs
#   - Área de trabalho = conteúdo (tabelas, forms, resultados)
#   - Botão Voltar só aparece quando há subnível (push de view)
#   - self.root  = janela real (Tk ou Toplevel) — para attributes(), etc.
#   - self.frame = contentor de renderização (pode ser Frame)

import getpass
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk
from tkinter import simpledialog, messagebox as mb, filedialog
from tkinter import Menu
from typing import List, Callable, Optional
import logging
from infrastructure.logging.log_handler_gui import GuiLogHandler



class BaseGui:

    # --------------------------------------------------
    # Tema — igual em todos os módulos
    # --------------------------------------------------
    BG           = "#CADAD9"
    FG           = "#92332C"
    BTN_BG       = "#F1E2CF"
    FONT_TITLE   = "Verdana 16 bold"
    FONT_SUB     = "Verdana 8 bold"
    FONT_BUTTON  = "Verdana 12 bold"
    BUTTON_WIDTH = 30

    # --------------------------------------------------
    # Construtor
    # --------------------------------------------------

    def __init__(self, parent=None, controller=None):
        """
        parent     : tk.Tk, tk.Toplevel ou tk.Frame
        controller : controlador do módulo

        self.root  = janela real (Tk/Toplevel) — usada para attributes(),
                     wait_window(), destroy(), messagebox parent=, etc.
        self.frame = contentor de renderização (idêntico a root quando
                     parent é Tk/Toplevel, senão o Frame recebido)
        """
        if isinstance(parent, (tk.Tk, tk.Toplevel)):
            self.root  = parent
            self.frame = parent
        elif parent is not None:
            self.root  = parent.winfo_toplevel()
            self.frame = parent
        else:
            self.root  = None
            self.frame = None

        self.controller  = controller
        self.txt_output  = None
        self._view_stack = []
        self._back_btn   = None   # criado dinamicamente
        self._modulo     = None

        if self.root is None:
            return

        # ── Quando parent é Frame, reutilizar a estrutura já criada na janela raiz
        # ── Quando parent é Tk/Toplevel, criar toda a estrutura de raiz
        if not isinstance(parent, (tk.Tk, tk.Toplevel)):
            # herdar frames do root_gui existente — encontrá-lo via winfo
            # os atributos serão injectados por show_view após a instanciação
            return

        self._build_menu()

        # ── TOPO ──────────────────────────────────────
        self.frame_top = tk.Frame(self.root, bg="#D3D3D3")
        self.frame_top.pack(fill="x")

        self.frame_top_left = tk.Frame(self.frame_top, bg="#D3D3D3")
        self.frame_top_left.pack(side="left", padx=20, pady=8)

        self.frame_top_right = tk.Frame(self.frame_top, bg="#D3D3D3")
        self.frame_top_right.pack(side="right", padx=20, pady=8)

        # ── MENU ──────────────────────────────────────
        # frame_menu_btns  ← botões de navegação (esquerda)
        # frame_menu_back  ← botão Voltar (direita, só quando há subnível)
        self.frame_menu = tk.Frame(self.root, bg=self.BG)
        self.frame_menu.pack(fill="x", pady=2)

        self.frame_menu_btns = tk.Frame(self.frame_menu, bg=self.BG)
        self.frame_menu_btns.pack(side="left", padx=5)

        self.frame_menu_back = tk.Frame(self.frame_menu, bg=self.BG)
        self.frame_menu_back.pack(side="right", padx=5)

        # ── DIVISOR TRABALHO / LOGS ───────────────────
        paned = tk.PanedWindow(
            self.root, orient="vertical", bg=self.BG,
            sashwidth=6, sashrelief="raised",
        )
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        self.frame_work = tk.Frame(paned, bg=self.BG)
        paned.add(self.frame_work, minsize=60)

        self.frame_logs = tk.Frame(paned, bg=self.BG)
        paned.add(self.frame_logs, minsize=80)

        # posição inicial do sash: trabalho ocupa a maioria; logs ficam em baixo (~150 px)
        def _posicionar_sash():
            if len(paned.panes()) < 2:
                return  # sash removido (janela modal sem zona de logs)
            h = paned.winfo_height()
            if h > 1:
                paned.sash_place(0, 0, max(h - 150, 300))
            else:
                self.root.after(50, _posicionar_sash)
        self.root.after(100, _posicionar_sash)

        # ── LOGS ──────────────────────────────────────
        log_inner = tk.Frame(self.frame_logs, bg="white")
        log_inner.pack(fill="both", expand=True, padx=10, pady=6)

        log_scroll = tk.Scrollbar(log_inner, orient="vertical")
        log_scroll.pack(side="right", fill="y")

        self.txt_output = tk.Text(
            log_inner,
            bg="white",
            fg="#222222",
            wrap="word",
            font=("Courier", 9),
            yscrollcommand=log_scroll.set,
        )
        self.txt_output.pack(side="left", fill="both", expand=True)
        log_scroll.config(command=self.txt_output.yview)

        # ── LOGGING → GUI ─────────────────────────────
        root_logger = logging.getLogger()
        if not any(isinstance(h, GuiLogHandler) for h in root_logger.handlers):
            handler = GuiLogHandler(self.root, self)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(message)s", "%H:%M:%S")
            )
            root_logger.addHandler(handler)

        # ── Botão X da janela usa o mesmo fluxo de saída
        if isinstance(self.root, tk.Tk):
            self.root.protocol("WM_DELETE_WINDOW", self._sair)
            self.root.state("zoomed")

    # --------------------------------------------------
    # Menu global (barra de menus nativa — só na Tk raiz)
    # --------------------------------------------------

    def _build_menu(self):
        if self.root is None:
            return
        if not isinstance(self.root, tk.Tk):
            return

        menuBar = Menu(self.root)
        m_file  = Menu(menuBar, tearoff=0)
        m_file.add_command(
            label="Importar PIM.xlsx",
            command=lambda: self._call_controller("importar_pim_xlsx")
        )
        m_file.add_separator()
        m_file.add_command(label="Sair", command=self._sair)
        menuBar.add_cascade(label="Ficheiro", menu=m_file)
        self.root.config(menu=menuBar)

    def _call_controller(self, method):
        if not self.controller:
            return
        try:
            func = getattr(self.controller, method)
        except AttributeError:
            self.informuser("Erro", f"Função '{method}' não existe.", "error")
            return
        try:
            func()
        except Exception as e:
            self.informuser("Erro", str(e), "error")

    # --------------------------------------------------
    # Topo — título e botão Sair
    # --------------------------------------------------

    def set_title(self, modulo, submodo=None):
        """
        Actualiza o título no topo e coloca o botão Sair.
        set_title("Secretaria")
        set_title("Secretaria", "PIM")
        """
        self._modulo = modulo
        for w in self.frame_top_left.winfo_children():
            w.destroy()
        for w in self.frame_top_right.winfo_children():
            w.destroy()

        titulo = f"{modulo}  —  {submodo}" if submodo else modulo

        tk.Label(
            self.frame_top_left,
            text=titulo,
            font=self.FONT_TITLE,
            bg="#D3D3D3",
            fg=self.FG,
        ).pack(anchor="w")

        tk.Button(
            self.frame_top_right,
            text="Sair",
            command=self._sair,
            bg=self.BTN_BG,
            font=self.FONT_BUTTON,
            width=8,
        ).pack()

    def add_top_title(self, text, side="left"):
        parent = self.frame_top_left if side == "left" else self.frame_top_right
        tk.Label(
            parent,
            text=text,
            font=self.FONT_TITLE,
            bg="#D3D3D3",
            fg=self.FG,
        ).pack()

    def add_sair_button(self):
        for w in self.frame_top_right.winfo_children():
            w.destroy()
        tk.Button(
            self.frame_top_right,
            text="Sair",
            command=self._sair,
            bg=self.BTN_BG,
            font=self.FONT_BUTTON,
            width=10,
        ).pack()

    # --------------------------------------------------
    # Menu — friso de navegação
    # --------------------------------------------------

    def build_menu_buttons(self, options):
        """
        Preenche o friso de menu com botões de navegação.
        options : [(texto, comando), ...]
        O botão Voltar é gerido separadamente por show_view/go_back.
        """
        for w in self.frame_menu_btns.winfo_children():
            w.destroy()

        for text, command in options:
            tk.Button(
                self.frame_menu_btns,
                text=text,
                command=command,
                font=self.FONT_BUTTON,
                bg=self.BTN_BG,
            ).pack(side="left", padx=6, pady=4)

    def _mostrar_voltar(self, comando):
        """Mostra o botão ← Voltar no lado direito do friso."""
        for w in self.frame_menu_back.winfo_children():
            w.destroy()
        self._back_btn = tk.Button(
            self.frame_menu_back,
            text="← Voltar",
            command=comando,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
        )
        self._back_btn.pack(side="right", padx=6, pady=4)

    def _esconder_voltar(self):
        """Remove o botão ← Voltar."""
        for w in self.frame_menu_back.winfo_children():
            w.destroy()
        self._back_btn = None

    def hide_menu(self):
        if self.frame_menu.winfo_ismapped():
            self.frame_menu.pack_forget()

    def show_menu(self):
        if not self.frame_menu.winfo_ismapped():
            self.frame_menu.pack(fill="x", pady=2)

    # --------------------------------------------------
    # Área de trabalho
    # --------------------------------------------------

    def abrir_work_area(self):
        """Limpa e devolve um Frame fresco na área de trabalho."""
        for w in self.frame_work.winfo_children():
            w.destroy()
        frame = tk.Frame(self.frame_work, bg=self.BG)
        frame.pack(fill="both", expand=True)
        return frame

    def add_button(self, parent, text, command, width=None):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.FONT_BUTTON,
            bg=self.BTN_BG,
            width=width or self.BUTTON_WIDTH,
        )
        btn.pack(pady=10)
        return btn

    def build_button_row(self, parent, buttons, padx=10, pady=5):
        """Linha horizontal de botões dentro da área de trabalho."""
        frame = tk.Frame(parent, bg=self.BG)
        frame.pack(pady=pady)
        for text, cmd in buttons:
            tk.Button(
                frame,
                text=text,
                command=cmd,
                font=self.FONT_BUTTON,
                bg=self.BTN_BG,
            ).pack(side="left", padx=padx)
        return frame

    # --------------------------------------------------
    # Navegação entre vistas (push/pop)
    # --------------------------------------------------

    def show_view(self, view_class, controller, *args, push=True, **kwargs):
        """
        Navega para uma nova vista dentro da área de trabalho.
        Guarda (view_class, controller, args, kwargs) na stack — nunca
        widgets que podem ser destruídos entretanto.

        A vista criada herda os frames de navegação (frame_menu_btns,
        frame_menu_back, frame_work) e a view_stack da instância raiz,
        para que build_menu_buttons e go_back operem sempre no friso único.
        """
        # determinar o gui raiz — pode ser self ou o _root_gui que self herdou
        root_gui = getattr(self, '_root_gui', self)

        if push:
            root_gui._view_stack.append((view_class, controller, args, kwargs))
            root_gui._mostrar_voltar(root_gui.go_back)

        for w in root_gui.frame_work.winfo_children():
            w.destroy()

        frame = tk.Frame(root_gui.frame_work, bg=self.BG)
        frame.pack(fill="both", expand=True)

        vista = view_class(frame, controller, *args, **kwargs)

        # injectar referência ao gui raiz na nova vista
        vista._root_gui       = root_gui
        vista.frame_menu_btns = root_gui.frame_menu_btns
        vista.frame_menu_back = root_gui.frame_menu_back
        vista.frame_work      = root_gui.frame_work
        vista._view_stack     = root_gui._view_stack

        # chamar _post_init se existir — permite subclasses inicializarem
        # o friso após receberem os frames injectados
        if callable(getattr(vista, '_post_init', None)):
            vista._post_init()

        return vista

    def go_back(self):
        """Volta à vista anterior reconstruindo-a a partir da stack."""
        root_gui = getattr(self, '_root_gui', self)

        if not root_gui._view_stack:
            return

        # remover vista actual
        root_gui._view_stack.pop()

        for w in root_gui.frame_work.winfo_children():
            w.destroy()

        if not root_gui._view_stack:
            root_gui._esconder_voltar()
            # restaurar o friso do menu raiz se existir callback registado
            if callable(getattr(root_gui, '_restore_root_menu', None)):
                root_gui._restore_root_menu()
            return

        # reconstruir a vista anterior sem novo push
        view_class, controller, args, kwargs = root_gui._view_stack[-1]
        frame = tk.Frame(root_gui.frame_work, bg=self.BG)
        frame.pack(fill="both", expand=True)
        vista = view_class(frame, controller, *args, **kwargs)

        # reinjectar frames na vista reconstruída
        vista._root_gui       = root_gui
        vista.frame_menu_btns = root_gui.frame_menu_btns
        vista.frame_menu_back = root_gui.frame_menu_back
        vista.frame_work      = root_gui.frame_work
        vista._view_stack     = root_gui._view_stack

        if callable(getattr(vista, '_post_init', None)):
            vista._post_init()

        if len(root_gui._view_stack) <= 1:
            root_gui._esconder_voltar()

    # --------------------------------------------------
    # Cabeçalho dentro da área de trabalho (logo + texto)
    # --------------------------------------------------

    def build_header(self, parent, titulo, subtitulo,
                     logo_size=(80, 80),
                     font_title=None,
                     font_sub=None):
        if font_title is None:
            font_title = self.FONT_TITLE
        if font_sub is None:
            font_sub = self.FONT_SUB

        frame = tk.Frame(parent, bg=self.BG)
        frame.pack(pady=10, anchor="w")

        try:
            logo_path = getattr(self.controller, "logo_path", None)
            if logo_path:
                logo  = ler_jpg(logo_path)
                logo  = logo.resize(logo_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(logo)
                frame.logo_img = photo
                tk.Label(frame, image=photo, bg=self.BG).pack(anchor="w", pady=(0, 5))
        except Exception as e:
            print("Erro ao carregar logo:", e)

        tk.Label(frame, text=titulo,    fg=self.FG, bg=self.BG, font=font_title).pack(anchor="w")
        tk.Label(frame, text=subtitulo, fg=self.FG, bg=self.BG, font=font_sub  ).pack(anchor="w")

        return frame

    # --------------------------------------------------
    # Saída com diálogo de feedback
    # --------------------------------------------------

    def _sair(self):
        """Mostra diálogo de sugestão/erro antes de encerrar a aplicação."""
        win = tk.Toplevel(self.root)
        win.title("Antes de sair — ATRPT")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.focus_force()
        self.center_window(win, 520, 300)

        resultado = {"texto": None}

        tk.Label(
            win,
            text="Sugestão ou erro a registar?",
            font="Verdana 11 bold",
            pady=10,
        ).pack()
        tk.Label(
            win,
            text="(deixe em branco para sair sem registar)",
            font="Verdana 9",
            fg="#666666",
        ).pack()

        txt = tk.Text(win, height=7, width=58, wrap="word", font=("Verdana", 10))
        txt.pack(padx=15, pady=10)
        txt.focus_set()

        def _confirmar():
            resultado["texto"] = txt.get("1.0", tk.END).strip()
            win.destroy()

        def _ignorar():
            win.destroy()

        frame_btns = tk.Frame(win, pady=6)
        frame_btns.pack()
        tk.Button(
            frame_btns,
            text="Guardar e sair",
            command=_confirmar,
            bg=self.BTN_BG,
            font=self.FONT_BUTTON,
        ).pack(side="left", padx=12)
        tk.Button(
            frame_btns,
            text="Sair sem registar",
            command=_ignorar,
            font=self.FONT_BUTTON,
            fg="#666666",
        ).pack(side="left", padx=12)

        win.bind("<Escape>", lambda e: _ignorar())
        win.protocol("WM_DELETE_WINDOW", _ignorar)
        win.wait_window()

        if resultado["texto"]:
            self._gravar_feedback(resultado["texto"])

        self.root.quit()

    def _gravar_feedback(self, texto: str):
        hoje = date.today().isoformat()
        user = getpass.getuser()
        app  = self._modulo or "ATRPT"
        linha = f"{hoje} - {user} - {app} - {texto}\n"
        todos_path = Path(__file__).resolve().parents[2] / "ToDos.txt"
        try:
            with open(todos_path, "a", encoding="utf-8") as f:
                f.write(linha)
        except Exception:
            pass

    # --------------------------------------------------
    # Logs
    # --------------------------------------------------

    def log(self, msg):
        if not self.txt_output:
            return
        self.escreveOutput(msg)

    def log_error(self, msg):
        self.escreveOutput(f"ERRO: {msg}")

    def log_ok(self, msg):
        self.escreveOutput(f"OK: {msg}")

    def escreveOutput(self, msg):
        if getattr(self, "txt_output", None):
            self.txt_output.insert(tk.END, f"{msg}\n")
            self.txt_output.see(tk.END)
        else:
            print(msg)

    def clearOutput(self):
        if self.txt_output:
            self.txt_output.delete("1.0", tk.END)

    # --------------------------------------------------
    # Diálogos e interacção com o utilizador
    # --------------------------------------------------

    def _bring_to_front(self):
        """Traz a janela para a frente. root é sempre Tk/Toplevel."""
        if self.root is None:
            return
        self.root.update_idletasks()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(10, lambda: self.root.attributes('-topmost', False))

    def informuser(self, title, message, tipo="info"):
        self._bring_to_front()
        parent = self.root
        if tipo == "info":
            mb.showinfo(title, message, parent=parent)
        elif tipo == "warning":
            mb.showwarning(title, message, parent=parent)
        else:
            mb.showerror(title, message, parent=parent)

    def confirm(self, title, message):
        self._bring_to_front()
        return mb.askyesno(title, message, parent=self.root)

    def pedirInput(self, titulo, pergunta, tipo="str"):
        top = tk.Toplevel(self.root)
        top.title(titulo)
        top.transient(self.root)
        top.bind("<Escape>", lambda e: top.destroy())
        top.grab_set()

        tk.Label(top, text=pergunta).pack(padx=10, pady=10)

        entry = tk.Entry(top)
        entry.pack(padx=10, pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)

        resultado = {"valor": None}

        def confirmar():
            resultado["valor"] = entry.get()
            top.destroy()

        tk.Button(top, text="OK", command=confirmar).pack(pady=10)
        top.bind("<Return>", lambda e: confirmar())
        top.wait_window()

        return resultado["valor"]

    def perguntaMes(self):
        self._bring_to_front()
        mes = simpledialog.askstring(
            "Selecionar mês", "Indique o mês (1-12):", parent=self.root
        )
        if mes and mes.isdigit() and 1 <= int(mes) <= 12:
            return mes
        self.informuser("Mês inválido", "Introduza um mês entre 1 e 12.", "warning")
        return None

    def promptuser(self, title, message, inputType="text"):
        self._bring_to_front()
        if inputType == "int":
            val = simpledialog.askstring(title, message, parent=self.root)
            if not val:
                return None
            try:
                return int(val.strip())
            except ValueError:
                self.informuser("Valor inválido", "Introduza um número inteiro.", "warning")
                return None
        return simpledialog.askstring(title, message, parent=self.root)

    def ask_file(self, title="Selecionar ficheiro", filetypes=None):
        return filedialog.askopenfilename(
            title=title,
            filetypes=filetypes or [("All files", "*.*")]
        )

    def mostrar_dataframe(self, titulo, df):
        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.geometry("900x400")

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=list(df.columns), show="headings")

        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center")

        for _, row in df.iterrows():
            tree.insert("", "end", values=list(row))

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid( row=0, column=1, sticky="ns")
        hsb.grid( row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    # --------------------------------------------------
    # Utilitários de janela
    # --------------------------------------------------

    def set_busy(self, busy=True):
        state = "disabled" if busy else "normal"
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state=state)

    @staticmethod
    def center_window(win, width=None, height=None):
        win.update_idletasks()
        width  = width  or win.winfo_width()
        height = height or win.winfo_height()
        x = (win.winfo_screenwidth()  // 2) - (width  // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

    @staticmethod
    def make_modal(win, parent=None):
        if parent:
            win.transient(parent)
        win.grab_set()
        win.focus_force()

    # --------------------------------------------------
    # Combobox com autocomplete
    # --------------------------------------------------

    def criar_combobox_autocomplete(
        self,
        parent,
        valores: List[str],
        largura: int = 30,
        placeholder: str = "",
        on_select: Optional[Callable] = None,
        case_sensitive: bool = False,
        match_contains: bool = True,
    ) -> ttk.Combobox:
        """
        Combobox com filtragem ao teclar - mantém o foco no campo de entrada.
        """
        combo = ttk.Combobox(parent, width=largura, values=list(valores) if valores else [])
        
        # Armazenar configurações
        combo._valores_originais = list(valores) if valores else []
        combo._case_sensitive = case_sensitive
        combo._match_contains = match_contains
        combo._on_select_callback = on_select
        combo._placeholder_text = placeholder
        combo._mostrando_placeholder = False
        combo._atualizando = False
        combo._dropdown_aberto = False
        
        def filtrar_valores(texto: str) -> List[str]:
            """Filtra valores baseado no texto."""
            if not texto or (placeholder and texto == placeholder):
                return combo._valores_originais.copy()
            
            t = texto if case_sensitive else texto.lower()
            if match_contains:
                return [v for v in combo._valores_originais 
                    if t in (v if case_sensitive else v.lower())]
            else:
                return [v for v in combo._valores_originais 
                    if (v if case_sensitive else v.lower()).startswith(t)]
        
        def abrir_dropdown_sem_perder_foco():
            """Abre o dropdown mantendo o foco no campo de entrada."""
            if not combo._dropdown_aberto:
                combo._dropdown_aberto = True
                # Salvar o widget que tem foco atualmente
                widget_atual = combo.focus_get()
                
                # Abrir dropdown
                try:
                    combo.tk.call('ttk::combobox::Post', combo._w)
                except Exception:
                    # Fallback: usar evento Down
                    combo.event_generate('<Down>')
                
                # Restaurar foco para o campo de entrada
                combo.after(10, lambda: combo.focus_set())
        
        def atualizar_dropdown(texto: str):
            """Atualiza os valores do dropdown sem fechar."""
            if combo._atualizando:
                return
            
            combo._atualizando = True
            try:
                # Salvar posição do cursor
                pos_cursor = combo.index(tk.INSERT)
                
                filtrados = filtrar_valores(texto)
                combo['values'] = filtrados
                
                # Restaurar texto e posição do cursor
                if combo.get() != texto:
                    combo.set(texto)
                try:
                    combo.icursor(pos_cursor)
                except:
                    pass
                
                # Se houver resultados, abrir dropdown sem perder foco
                if filtrados:
                    combo.after(10, abrir_dropdown_sem_perder_foco)
                else:
                    # Fechar dropdown se não houver resultados
                    try:
                        combo.tk.call('ttk::combobox::Unpost', combo._w)
                        combo._dropdown_aberto = False
                    except:
                        pass
            finally:
                combo._atualizando = False
        
        def on_keyrelease(event):
            """Manipula teclas para filtrar valores."""
            # Ignorar teclas especiais
            if event.keysym in ('Down', 'Up', 'Return', 'KP_Enter', 'Escape', 'Tab',
                            'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                            'Alt_L', 'Alt_R'):
                return
            
            if combo._mostrando_placeholder:
                return
            
            texto = combo.get()
            
            # Pequeno delay para permitir processamento da tecla
            combo.after(10, lambda: atualizar_dropdown(texto))
        
        def on_select(event):
            """Manipula seleção de item."""
            if combo._mostrando_placeholder:
                return
            
            # Restaurar lista completa após seleção
            combo['values'] = combo._valores_originais
            combo._dropdown_aberto = False
            
            if combo._on_select_callback:
                combo._on_select_callback(combo.get())
            
            # Garantir que o foco volte ao campo
            combo.focus_set()
        
        def on_focus_out(event):
            """Valida valor ao perder foco."""
            # Ignorar se o foco foi para o dropdown
            try:
                # Verificar se o novo foco é um widget filho ou o próprio dropdown
                widget_foco = combo.tk.call('focus')
                if widget_foco and (widget_foco == combo._w or 
                                'combobox' in str(widget_foco).lower()):
                    return
            except:
                pass
            
            if combo._mostrando_placeholder:
                return
            
            texto = combo.get().strip()
            
            # Limpar se não for um valor válido
            if texto and texto not in combo._valores_originais:
                combo.set('')
            elif not texto and placeholder:
                # Restaurar placeholder se houver
                mostrar_placeholder()
            
            # Restaurar lista original
            combo['values'] = combo._valores_originais
            combo._dropdown_aberto = False
        
        def mostrar_placeholder():
            """Mostra o placeholder no campo."""
            if not placeholder:
                return
            
            combo._mostrando_placeholder = True
            combo.set(placeholder)
            combo.config(foreground="gray")
        
        def remover_placeholder():
            """Remove o placeholder do campo."""
            if combo._mostrando_placeholder:
                combo._mostrando_placeholder = False
                combo.set('')
                combo.config(foreground="black")
        
        def on_focus_in(event):
            """Remove placeholder ao ganhar foco."""
            if combo._mostrando_placeholder:
                remover_placeholder()
        
        def on_dropdown_close(event=None):
            """Marca que o dropdown foi fechado."""
            combo._dropdown_aberto = False
        
        # Configurar eventos
        combo.bind('<KeyRelease>', on_keyrelease)
        combo.bind('<<ComboboxSelected>>', on_select)
        combo.bind('<FocusOut>', on_focus_out)
        combo.bind('<FocusIn>', on_focus_in)
        
        # Detectar quando o dropdown é fechado
        combo.bind('<Button-1>', lambda e: None)  # Prevenir fechamento indesejado
        
        # Configurar placeholder inicial
        if placeholder:
            mostrar_placeholder()
        
        return combo

# --------------------------------------------------
# Diálogo de input reutilizável
# --------------------------------------------------

class InputDialog(simpledialog.Dialog):

    def __init__(self, parent, title, prompt, tipo="text"):
        self.prompt = prompt
        self.tipo   = tipo
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text=self.prompt, justify="left").pack(padx=10, pady=10)
        self.entry = tk.Entry(master, width=30)
        self.entry.pack(padx=10, pady=5)
        self.entry.focus_set()
        self.entry.icursor(tk.END)
        return self.entry

    def validate(self):
        valor = self.entry.get().strip()
        if not valor:
            self.result = None
            return True
        if self.tipo == "int":
            try:
                self.result = int(valor)
                return True
            except ValueError:
                mb.showerror("Valor inválido", "Introduza um número inteiro válido.")
                return False
        elif self.tipo == "float":
            try:
                self.result = float(valor.replace(",", "."))
                return True
            except ValueError:
                mb.showerror("Valor inválido", "Introduza um número decimal válido.")
                return False
        else:
            self.result = valor
            return True

    def apply(self):
        pass
