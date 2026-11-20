"""Peças de interface compartilhadas entre mestre, jogador e qualquer sistema de ficha."""
import queue
import tkinter as tk
import traceback

import customtkinter as ctk

# Paleta (tons de cinza; a cor de destaque vem de cada ficha)
BG = "#121212"
PANEL = "#1e1e1e"
PANEL_DARK = "#151515"
INPUT = "#121212"
BORDER = "#333333"
BUTTON = "#2b2b2b"
BUTTON_HOVER = "#3e3e3e"
DANGER_HOVER = "#a83232"
TEXT = "#ffffff"
TEXT_DIM = "#aaaaaa"
TEXT_MUTED = "#888888"
TEXT_FAINT = "#555555"
OK = "#2ecc71"
WARN = "#d4af37"
ERROR = "#e74c3c"
TITLE_FONT = "Cinzel"


class UiDispatcher:
    """Leva chamadas das threads de rede para a thread da interface.

    Tkinter não é thread-safe: chamar root.after() de outra thread falha (às vezes em silêncio).
    As threads só colocam a chamada numa fila; a interface esvazia a fila a cada poucos ms.
    """

    def __init__(self, root, interval_ms=30):
        self.root = root
        self.interval_ms = interval_ms
        self._queue = queue.SimpleQueue()
        self.root.after(self.interval_ms, self._drain)

    def post(self, fn, *args):
        self._queue.put((fn, args))

    def wrap(self, fn):
        """Devolve uma função que pode ser chamada de qualquer thread."""
        return lambda *args: self.post(fn, *args)

    def _drain(self):
        while True:
            try:
                fn, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:
                traceback.print_exc()
        try:
            self.root.after(self.interval_ms, self._drain)
        except tk.TclError:
            pass  # janela fechada


def fmt_bonus(value) -> str:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"+{value}" if value >= 0 else str(value)


def install_click_defocus(root):
    """Clicar fora de um campo de texto tira o foco dele (dispara o salvamento por FocusOut)."""

    def on_click(event):
        widget = event.widget
        while widget is not None:
            try:
                if "entry" in widget.__class__.__name__.lower() or "entry" in widget.winfo_class().lower():
                    return
                parent = widget.winfo_parent()
                widget = widget._nametowidget(parent) if parent else None
            except Exception:
                break
        root.focus()

    root.bind("<Button-1>", on_click, add="+")


def stat_widget(parent, label_text, value):
    frame = ctk.CTkFrame(parent, fg_color=PANEL_DARK, corner_radius=6)
    ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=9, weight="bold"), text_color="#666666").pack(pady=(4, 0))
    ctk.CTkLabel(frame, text=str(value), font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(pady=(0, 4))
    return frame


def small_button(parent, text, command, width=35, danger=False, **kwargs):
    return ctk.CTkButton(
        parent, text=text, width=width, height=kwargs.pop("height", 22), fg_color=BUTTON,
        hover_color=DANGER_HOVER if danger else BUTTON_HOVER, font=ctk.CTkFont(size=10),
        command=command, **kwargs,
    )


def text_entry(parent, placeholder="", **kwargs):
    return ctk.CTkEntry(
        parent, placeholder_text=placeholder, fg_color=INPUT, border_color=BORDER,
        height=kwargs.pop("height", 26), font=kwargs.pop("font", ctk.CTkFont(size=11)), **kwargs,
    )


class TabBar:
    """Barra de abas com indicador colorido. Serve tanto para abas principais quanto sub-abas."""

    def __init__(self, parent, content_parent, get_color, main=False):
        self.get_color = get_color
        self.content_parent = content_parent
        self.main = main
        self.header = ctk.CTkFrame(
            parent, fg_color=PANEL_DARK, height=40 if main else 32, corner_radius=0 if main else 5,
        )
        self.header.grid_rowconfigure(0, weight=1)
        self.header.grid_rowconfigure(1, weight=0)
        self.views = {}
        self.indicators = {}
        self.on_switch = {}
        self.active = None

    def add(self, name, view, on_switch=None):
        col = len(self.views)
        self.header.grid_columnconfigure(col, weight=1)
        ctk.CTkButton(
            self.header, text=name.upper(), fg_color="transparent", hover_color=PANEL,
            text_color=TEXT if self.main else TEXT_DIM,
            font=ctk.CTkFont(size=10 if self.main else 9, weight="bold"), corner_radius=0, width=10,
            command=lambda n=name: self.switch(n),
        ).grid(row=0, column=col, sticky="nsew")
        indicator = ctk.CTkFrame(self.header, height=3 if self.main else 2, fg_color="transparent", corner_radius=0)
        indicator.grid(row=1, column=col, sticky="ew")
        self.views[name] = view
        self.indicators[name] = indicator
        if on_switch:
            self.on_switch[name] = on_switch
        if self.active is None:
            self.active = name

    def switch(self, name=None):
        name = name if name in self.views else self.active
        if name is None:
            return
        self.active = name
        for other, view in self.views.items():
            if other == name:
                view.pack(fill=tk.BOTH, expand=True)
                self.indicators[other].configure(fg_color=self.get_color())
            else:
                view.pack_forget()
                self.indicators[other].configure(fg_color="transparent")
        callback = self.on_switch.get(name)
        if callback:
            callback()
