"""Base das telas de ficha editáveis (Ordem Paranormal, ameaças, D&D 5e).

Os campos são editáveis no lugar e registrados com o caminho deles na ficha (ex.: ("pv", "atual")).
Depois de cada edição as regras do sistema são reaplicadas (`apply_rules`) e os valores calculados
são redesenhados. Quando chega uma ficha nova pela rede, só os campos que mudaram são reescritos, e o
campo em que a pessoa está digitando não é tocado.

Cada sistema cria uma subclasse com `_build()` e, se tiver regras, `apply_rules()` e `_needs_rebuild()`.
"""
import tkinter as tk
import tkinter.font  # noqa: F401  (tk.font, usado para medir a altura das linhas)

import customtkinter as ctk

from src.sheet_io import to_int
from src.ui.common import (BORDER, BUTTON, BUTTON_HOVER, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, dice_icon, small_button, update)


class BaseSheetView(ctk.CTkFrame):
    DEFAULT_COLOR = "#8e44ad"

    def __init__(self, master, sheet: dict, on_change=None, on_roll=None):
        super().__init__(master, fg_color="transparent")
        self.sheet = sheet
        self.on_change = on_change
        self.on_roll = on_roll
        self.color = sheet.get("cor", self.DEFAULT_COLOR)
        self._build()

    # ================================================================= caminho na ficha
    def _get(self, path):
        value = self.sheet
        for key in path:
            try:
                value = value[key]
            except (KeyError, IndexError, TypeError):
                return None
        return value

    def _set(self, path, value):
        target = self.sheet
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    # ================================================================= campos registrados
    @staticmethod
    def _display(value, kind):
        """Texto mostrado no campo. Subclasses tratam os tipos próprios e chamam esta para o resto."""
        if kind == "circulo":
            return f"{value}º"
        return "" if value is None else str(value)

    @staticmethod
    def _read(widget, kind):
        if kind == "text":
            return "" if getattr(widget, "_hint", False) else widget.get("1.0", "end-1c")
        return widget.get()

    def _write(self, widget, value, kind):
        text = self._display(value, kind)
        if kind == "text":
            self._hide_hint(widget)
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
            self._show_hint(widget)
        elif isinstance(widget, (ctk.CTkOptionMenu, ctk.CTkComboBox)):  # menus: grau, círculo, atributo...
            widget.set(text)
        else:
            widget.delete(0, tk.END)
            if text:
                widget.insert(0, text)

    def _commit(self, path, value):
        """Grava um valor editado, reaplica as regras e avisa quem estiver ouvindo."""
        if value == self._get(path):
            self._sync_fields()
            return
        self._set(path, value)
        self._changed()

    def _field(self, parent, path, kind="str", width=60, placeholder="", size=11, bold=False, justify="left",
               clamp=None, transparent=False, text_color=TEXT, height=26):
        entry = ctk.CTkEntry(
            parent, width=width, height=height, placeholder_text=placeholder, justify=justify,
            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"), text_color=text_color,
            fg_color="transparent" if transparent else INPUT, border_width=0 if transparent else 1,
            border_color=BORDER,
        )
        self._write(entry, self._get(path), kind)
        self.fields.append((entry, path, kind))

        def save(defocus):
            try:
                raw = entry.get()
            except tk.TclError:
                return
            current = self._get(path)
            if kind == "int":
                value = to_int(raw, current if isinstance(current, int) else 0)
                if clamp:
                    value = clamp(value)
            else:
                value = raw.strip()
            self._commit(path, value)
            if defocus:
                self.winfo_toplevel().focus()

        entry.bind("<Return>", lambda *_: save(True))
        entry.bind("<FocusOut>", lambda *_: save(False))
        return entry

    def _combo(self, parent, path, values, width=200):
        """Caixa com lista (dá para escolher ou digitar)."""
        combo = ctk.CTkComboBox(parent, values=values, width=width, height=26, fg_color=INPUT, border_color=BORDER,
                                button_color=BUTTON, button_hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=11),
                                command=lambda v: self._commit(path, v.strip()))
        self._write(combo, self._get(path), "combo")
        self.fields.append((combo, path, "combo"))

        def save(_event=None):
            try:
                self._commit(path, combo.get().strip())
            except tk.TclError:
                pass

        combo.bind("<Return>", save)
        combo.bind("<FocusOut>", save)
        return combo

    def _option(self, parent, path, values, width=100, kind="option", parse=str):
        """Menu fechado (só os valores da lista). `parse` converte o rótulo no valor guardado."""
        menu = ctk.CTkOptionMenu(parent, values=values, width=width, height=22, fg_color=INPUT,
                                 button_color=BUTTON, button_hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=10),
                                 dropdown_font=ctk.CTkFont(size=11),
                                 command=lambda label: self._commit(path, parse(label)))
        self._write(menu, self._get(path), kind)
        self.fields.append((menu, path, kind))
        return menu

    # ================================================================= rolagens
    SHIFT, CONTROL = 0x1, 0x4  # bits de event.state no Tk

    def _roll(self, req, event=None):
        """Envia o pedido. Num teste de d20, Shift+clique = "mais" e Ctrl+clique = "menos" (ver _roll_variant)."""
        if not req or not self.on_roll:
            return
        state = getattr(event, "state", 0)
        variant = "mais" if state & self.SHIFT else "menos" if state & self.CONTROL else None
        req = dict(req)
        after = req.pop("_on_roll", None)  # ação da ficha depois de rolar (ex.: descontar um dado de vida)
        if variant and req.get("sides") == 20 and req.get("qty", 1) == 1:
            req = self._roll_variant(req, variant)
        self.on_roll(req)
        if after:
            after()

    @staticmethod
    def _roll_variant(req, variant):
        """Padrão (D&D): "mais" = vantagem, "menos" = desvantagem (p. 173 do Livro do Jogador)."""
        if req.get("mode", "normal") != "normal":
            return req
        mode = "vantagem" if variant == "mais" else "desvantagem"
        return {**req, "mode": mode, "extra": 1, "label": f"{req.get('label', '')} ({mode})".strip()}

    def _rollable(self, button, make_request):
        """Faz o botão rolar no clique, sabendo se Shift/Ctrl estavam apertados (o command do CTk não sabe)."""
        button.configure(command=None)

        def click(event):
            if str(button.cget("state")) != "disabled":
                self._roll(make_request(), event)

        def bind_parts():
            # O CTkButton é um canvas + rótulos de texto e de ícone, e só cria o rótulo quando o texto/ícone
            # aparece. button.bind() liga só nas partes que já existem: um botão criado sem texto ficava com o
            # número ("+5") surdo ao clique. Liga em cada parte nova, uma vez só.
            for part in (button._canvas, button._text_label, button._image_label):
                if part is not None and not getattr(part, "_roll_bound", False):
                    part.bind("<Button-1>", click, add="+")
                    part._roll_bound = True

        bind_parts()
        button.bind("<Configure>", lambda _e: bind_parts())  # texto/ícone novo recria o rótulo e redimensiona
        button._bind_roll_parts = bind_parts
        return button

    def _bonus_button(self, parent, make_request, text_fn, color_fn=lambda: TEXT, width=56, size=12):
        """O próprio bônus ("+5") é o botão de rolar: não gasta coluna nem linha a mais."""
        button = ctk.CTkButton(parent, text="", width=width, height=22, fg_color=BUTTON, hover_color=BUTTON_HOVER,
                               font=ctk.CTkFont(size=size, weight="bold"), compound="left",
                               image=dice_icon(14) if self.on_roll else None,
                               state="normal" if self.on_roll else "disabled")
        self._rollable(button, make_request)

        def show():
            color = color_fn()
            update(button, text=text_fn(), text_color=color, text_color_disabled=color)
            button._bind_roll_parts()  # o rótulo do número nasce aqui, no primeiro texto
        self._computed(show)
        return button

    def _roll_button(self, parent, make_request, text="", width=26):
        """Botão com o d20 que rola; fica apagado quando o texto do teste/dano não tem o que rolar."""
        button = self._rollable(small_button(parent, text, None, width=width, height=22, image=dice_icon(),
                                             compound="left"), make_request)
        if self.on_roll is None:
            button.configure(state="disabled", image=dice_icon(dim=True))
        else:
            def refresh():
                active = bool(make_request())
                update(button, state="normal" if active else "disabled", image=dice_icon(dim=not active))
            self._computed(refresh)
        return button

    def _show_hint(self, box):
        """Área vazia e sem foco mostra o texto de exemplo em cinza (nunca vai para a ficha)."""
        placeholder = getattr(box, "_placeholder", None)
        if (placeholder and not getattr(box, "_hint", False) and not self._has_focus(box)
                and box.get("1.0", "end-1c") == ""):
            box.insert("1.0", placeholder)
            box.configure(text_color=TEXT_FAINT)
            box._hint = True

    @staticmethod
    def _hide_hint(box):
        if getattr(box, "_hint", False):
            box.delete("1.0", "end")
            box.configure(text_color=box._normal_color)
            box._hint = False

    def _textbox(self, parent, path, auto_height=False, text_color=TEXT, placeholder=None, framed=False):
        """Texto com quebra de linha. Com auto_height, a altura acompanha o tamanho do texto.

        `framed`: parece um campo comum (fundo e borda), cresce com o texto e Enter termina a edição
        (Shift+Enter quebra a linha). Serve para campos curtos que às vezes ficam longos (resistências).
        """
        auto_height = auto_height or framed
        box = ctk.CTkTextbox(parent, height=28 if auto_height else 110, wrap="word", font=ctk.CTkFont(size=11),
                             text_color=text_color,
                             fg_color=INPUT if framed or not auto_height else "transparent",
                             border_color=BORDER, border_width=1 if framed or not auto_height else 0,
                             activate_scrollbars=not auto_height)
        if framed:
            def finish(_event):
                self.winfo_toplevel().focus()  # tira o foco: o FocusOut salva
                return "break"
            box.bind("<Return>", finish)
            box.bind("<Shift-Return>", lambda _e: None)  # Shift+Enter: quebra normal
        box._placeholder, box._normal_color, box._hint = placeholder, text_color, False
        box.bind("<FocusIn>", lambda *_: self._hide_hint(box))
        self._write(box, self._get(path), "text")
        self.fields.append((box, path, "text"))

        if auto_height:
            def fit(_event=None):
                try:
                    inner = box._textbox
                    content = inner.count("1.0", "end", "ypixels")  # altura real do texto, já com as quebras
                    content = content[0] if isinstance(content, tuple) else (content or 0)
                    content = max(content, tk.font.Font(font=inner.cget("font")).metrics("linespace"))
                    # + margens internas do CTkTextbox (pady do texto e 6 px do grid) e uma folga
                    height = (content + 2 * int(inner.cget("pady"))) / box._get_widget_scaling() + 14
                    if abs(box.cget("height") - height) > 1:
                        box.configure(height=height)
                except (tk.TclError, AttributeError):
                    pass

            box._fit = fit
            box.bind("<KeyRelease>", fit)
            box.bind("<FocusOut>", lambda *_: box.after_idle(fit), add="+")
            box._textbox.bind("<Configure>", fit, add="+")
            box.after_idle(fit)

        def save(_event=None):
            try:
                value = self._read(box, "text").strip()
            except tk.TclError:
                return
            if value != self._get(path):
                self._set(path, value)
                self._changed()
            box.after_idle(lambda: box.winfo_exists() and self._show_hint(box))

        box.bind("<FocusOut>", save)
        return box

    def _has_focus(self, widget):
        focus = self.focus_get()
        inner = getattr(widget, "_entry", None) or getattr(widget, "_textbox", None)
        return focus is not None and focus in (widget, inner)

    def _sync_fields(self):
        """Reescreve os campos que não batem com a ficha (menos o que está sendo editado)."""
        alive = []
        for widget, path, kind in self.fields:
            if not widget.winfo_exists():
                continue
            alive.append((widget, path, kind))
            if self._has_focus(widget):
                continue
            value = self._get(path)
            if self._read(widget, kind) != self._display(value, kind):
                self._write(widget, value, kind)
                if hasattr(widget, "_fit"):
                    widget.after_idle(widget._fit)
        self.fields = alive

    def _computed(self, fn):
        """Registra algo calculado (rótulo, barra) para atualizar depois de cada mudança."""
        self.computed.append(fn)
        fn()

    def _refresh_computed(self):
        alive = []
        for fn in self.computed:
            try:
                fn()
                alive.append(fn)
            except tk.TclError:
                pass  # widget destruído
        self.computed = alive

    # ================================================================= regras (cada sistema define)
    @staticmethod
    def apply_rules(sheet):
        """Recalcula os valores derivados da ficha (no lugar)."""
        return sheet

    def _needs_rebuild(self):
        """True quando a edição muda a forma da tela (ex.: campo manual vira calculado)."""
        return False

    def _changed(self):
        self.apply_rules(self.sheet)
        if self._needs_rebuild():
            self.after_idle(self._rebuild)
        else:
            self._sync_fields()
            self._refresh_computed()
        if self.on_change:
            self.on_change(self.sheet)

    # ================================================================= construção
    def _get_color(self):
        return self.color

    def _card(self, parent, title=None, **pack):
        card = ctk.CTkFrame(parent, fg_color=PANEL, border_color=self.color, border_width=2, corner_radius=10)
        card.pack(**pack)
        if title:
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family=TITLE_FONT, size=13, weight="bold"),
                         text_color=TEXT).pack(pady=(8, 4))
        return card

    @staticmethod
    def _caption(parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_MUTED)

    def _value_label(self, parent, fn, size=15, **kwargs):
        """Rótulo com valor calculado, atualizado a cada mudança."""
        label = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=size, weight="bold"), text_color=TEXT, **kwargs)
        self._computed(lambda: update(label, text=str(fn())))
        return label

    def _rebuild(self):
        active = self.tabs.active if hasattr(self, "tabs") else None
        for child in self.winfo_children():
            child.destroy()
        self.color = self.sheet.get("cor", self.color)
        self._build(active)

    # ----------------------------------------------------------------- listas editáveis
    def _list_section(self, view, columns, placeholders, on_add):
        """Linha de 'adicionar' + área rolável. columns = [(largura, expande)]."""
        add = ctk.CTkFrame(view, fg_color="transparent")
        add.pack(fill=tk.X, pady=(0, 8))
        entries = []
        for (width, expand), placeholder in zip(columns, placeholders):
            entry = ctk.CTkEntry(add, width=width, height=26, placeholder_text=placeholder, fg_color=INPUT,
                                 border_color=BORDER, font=ctk.CTkFont(size=11))
            entry.pack(side=tk.LEFT, padx=3, fill=tk.X if expand else None, expand=expand)
            entries.append(entry)
        button = ctk.CTkButton(add, text="Adicionar", width=80, height=26, fg_color=BUTTON, hover_color=BUTTON_HOVER,
                               font=ctk.CTkFont(size=11), command=lambda: on_add(entries))
        button.pack(side=tk.RIGHT, padx=(5, 0))
        for entry in entries:
            entry.bind("<Return>", lambda *_: button.invoke())
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        return scroll

    def _list_rows(self, scroll, base_path, items, columns, keys, on_remove, first_bold=True, wrap_key=None,
                   affixes=None, clamps=None, placeholder=None, rolls=None):
        """Uma linha editável por item. `wrap_key` vai numa área de texto com quebra de linha embaixo.
        `affixes` = {chave: (texto antes, texto depois)} fixos ao redor do campo (ex.: "Pág." e "PE").
        `rolls` = {chave: f(idx) -> pedido}: põe o botão de rolar colado depois desse campo."""
        affixes = affixes or {}
        for child in scroll.winfo_children():
            child.destroy()
        for idx in range(len(items)):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            for c, ((width, expand), key) in enumerate(zip(columns, keys)):
                if key == wrap_key:
                    continue
                kind = "int" if key == "espacos" else "str"
                before, after = affixes.get(key, (None, None))
                if rolls and key in rolls:  # [d20 Teste] Luta: o rótulo é o próprio botão de rolar
                    self._roll_button(line, lambda f=rolls[key], i=idx: f(i), text=before or "",
                                      width=64).pack(side=tk.LEFT, padx=(10, 0))
                    before = None
                elif before:
                    ctk.CTkLabel(line, text=before, font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(
                        side=tk.LEFT, padx=(10, 0))
                clamp = (lambda v, f=clamps[key], i=idx: f(i, v)) if clamps and key in clamps else None
                entry = self._field(line, base_path + (idx, key), kind=kind, width=width, transparent=True,
                                    clamp=clamp, bold=first_bold and c == 0, size=12 if c == 0 else 11,
                                    text_color=self.color if first_bold and c == 0 else TEXT,
                                    # colado no rótulo: "2 PE" alinha à direita, "Pág. 24" à esquerda
                                    justify="right" if after else "left" if before else
                                    "center" if kind == "int" else "left")
                entry.pack(side=tk.LEFT, padx=3, pady=3, fill=tk.X if expand else None, expand=expand)
                if after:
                    ctk.CTkLabel(line, text=after, font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(
                        side=tk.LEFT, padx=(0, 10))
            small_button(line, "X", lambda i=idx: on_remove(i), width=24, danger=True,
                         height=20).pack(side=tk.RIGHT, padx=8)
            if wrap_key:
                self._textbox(row, base_path + (idx, wrap_key), auto_height=True, text_color=TEXT_DIM,
                              placeholder=placeholder).pack(fill=tk.X, padx=6, pady=(0, 6))

    def _append(self, path, item, entries, repopulate):
        if not item.get("nome"):
            return
        self._get(path).append(item)
        for entry in entries:
            entry.delete(0, tk.END)
        repopulate()
        self._changed()

    def _remove(self, path, idx, repopulate):
        items = self._get(path)
        if idx < len(items):
            items.pop(idx)
            repopulate()
            self._changed()
