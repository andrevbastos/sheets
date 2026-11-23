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


def allow_ctrl_c(root, on_interrupt):
    """Faz Ctrl+C no terminal fechar o app.

    No Windows, enquanto o Tk espera eventos o Python não roda, então o Ctrl+C nunca é tratado.
    Um "tique" a cada 200 ms devolve o controle ao Python; o handler só agenda o fechamento
    na thread da interface. `on_interrupt` pode ser trocado depois via o atributo devolvido.
    """
    import signal

    state = {"handler": on_interrupt}

    def handle(_signum, _frame):
        root.after(0, lambda: state["handler"]())

    signal.signal(signal.SIGINT, handle)

    def tick():
        try:
            root.after(200, tick)
        except tk.TclError:
            pass

    root.after(200, tick)
    return state


def bring_to_front(root):
    """Traz a janela para frente ao abrir (às vezes ela nasce atrás do terminal)."""

    def lift():
        try:
            root.deiconify()
            root.lift()
            root.attributes("-topmost", True)
            root.after(300, lambda: root.attributes("-topmost", False))
            root.focus_force()
        except tk.TclError:
            pass

    root.after(150, lift)


_ICONS = {}


def dice_icon(size=16, dim=False):
    """Ícone de d20 (hexágono com as faces), desenhado aqui para não depender da fonte do sistema."""
    key = (size, dim)
    if key not in _ICONS:
        import math

        from PIL import Image, ImageDraw

        scale = 8  # desenha grande e reduz: linhas suaves
        big = size * scale
        img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        c, r = big / 2, big * 0.47
        color = (90, 90, 90, 255) if dim else (225, 225, 225, 255)
        width = max(1, round(big * 0.075))

        def point(angle, radius):
            a = math.radians(angle)
            return c + radius * math.cos(a), c + radius * math.sin(a)

        outer = {a: point(a, r) for a in (-90, -30, 30, 90, 150, 210)}
        inner = {a: point(a, r * 0.52) for a in (-90, 30, 150)}  # face da frente, apontando para cima
        draw.polygon([inner[a] for a in (-90, 30, 150)], fill=color[:3] + (70,))
        lines = [(inner[a], outer[a]) for a in inner]  # cada canto da face até o canto de fora
        lines += [(outer[o], inner[i]) for o, pair in ((-30, (-90, 30)), (90, (30, 150)), (210, (150, -90)))
                  for i in pair]
        for p1, p2 in lines:
            draw.line([p1, p2], fill=color, width=width)
        draw.line([inner[a] for a in (-90, 30, 150, -90)], fill=color, width=width, joint="curve")
        draw.line([outer[a] for a in (-90, -30, 30, 90, 150, 210, -90)], fill=color, width=width, joint="curve")
        img = img.resize((size * 2, size * 2), Image.LANCZOS)  # 2x para telas com escala
        _ICONS[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _ICONS[key]


_MISSING = object()


def update(widget, **kwargs):
    """configure() só com o que mudou.

    No CustomTkinter cada configure() redesenha o widget inteiro, mesmo com o mesmo valor; refazer
    dezenas de rótulos a cada edição é o que fazia a tela piscar. Levanta TclError se o widget já
    foi destruído (quem chama usa isso para esquecer o widget).
    """
    if not widget.winfo_exists():
        raise tk.TclError("widget destruído")
    last = widget.__dict__.setdefault("_last_cfg", {})
    changed = {k: v for k, v in kwargs.items() if last.get(k, _MISSING) != v}
    if changed:
        widget.configure(**changed)
        last.update(changed)


def update_bar(bar, value):
    """CTkProgressBar.set() só quando o valor muda (pelo mesmo motivo de update())."""
    if not bar.winfo_exists():
        raise tk.TclError("widget destruído")
    value = round(max(0.0, min(float(value), 1.0)), 4)
    if bar.__dict__.get("_last_value") != value:
        bar.set(value)
        bar._last_value = value


def fmt_bonus(value) -> str:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"+{value}" if value >= 0 else str(value)


def install_click_defocus(root):
    """Clicar fora de um campo de texto tira o foco dele (dispara o salvamento por FocusOut).

    Campos de uma linha (Entry) e áreas de texto com várias linhas (Text/CTkTextbox) contam como campo.
    """
    editable = ("entry", "text")  # "text" pega tanto o Text do Tk quanto o CTkTextbox

    def on_click(event):
        widget = event.widget
        while widget is not None:
            try:
                names = (widget.__class__.__name__.lower(), widget.winfo_class().lower())
                if any(kind in name for kind in editable for name in names):
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
