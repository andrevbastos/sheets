"""Tela da ficha de D&D 5e, usada igual pelo mestre, pelo jogador e no modo offline.

Quem usa só passa `on_change(sheet)`: é chamado toda vez que algo é editado.
Para atualizar a tela com uma ficha vinda de fora (rede), chame `set_sheet(nova)`.
"""
import tkinter as tk

import customtkinter as ctk

from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM,
                           TEXT_FAINT, TEXT_MUTED, TITLE_FONT, TabBar, fmt_bonus, small_button, stat_widget,
                           text_entry)

SYSTEM = "dnd5e"

ATTRIBUTES = [("FOR", "forca"), ("DES", "destreza"), ("CON", "constituicao"),
              ("INT", "inteligencia"), ("SAB", "sabedoria"), ("CAR", "carisma")]
EXTRA_NAMES = {"cartas_destino": "Cartas de Destino"}

# Partes da ficha que só mudam a estrutura da tela (mudou = reconstruir tudo)
STATIC_KEYS = ("nome", "classe_nivel", "raca", "antecedente", "tendencia", "atributos", "pericias",
               "resistencia", "caracteristicas", "idiomas", "proficiencias")


def _combat_without_hp(sheet):
    return {k: v for k, v in sheet.get("combate", {}).items() if k not in ("hp_atual", "hp_max")}


class SheetView(ctk.CTkFrame):
    def __init__(self, master, sheet: dict, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.sheet = sheet
        self.on_change = on_change
        self.color = sheet.get("cor", "#d4af37")
        self.color_widgets = []
        self._build()

    # ================================================================= API
    def set_sheet(self, new_sheet: dict):
        """Atualiza a tela com uma ficha recebida, redesenhando só o que mudou."""
        if not new_sheet or new_sheet == self.sheet:
            return
        old, self.sheet = self.sheet, new_sheet

        structure_changed = (
            any(old.get(k) != new_sheet.get(k) for k in STATIC_KEYS)
            or _combat_without_hp(old) != _combat_without_hp(new_sheet)
            or set(old.get("extra", {})) != set(new_sheet.get("extra", {}))
        )
        if structure_changed:
            self._rebuild()
            return

        if old.get("cor") != new_sheet.get("cor"):
            self.change_color(new_sheet.get("cor", "#d4af37"))
        if old.get("combate") != new_sheet.get("combate"):
            self._render_hp()
        if old.get("inventario") != new_sheet.get("inventario"):
            self._populate_inventory()
        if old.get("ataques") != new_sheet.get("ataques"):
            self._populate_attacks()
        if old.get("magias") != new_sheet.get("magias"):
            self._populate_spells()
        old_extra, new_extra = old.get("extra", {}), new_sheet.get("extra", {})
        for key in new_extra:
            if old_extra.get(key) != new_extra.get(key):
                self._populate_extra(key)

    def change_color(self, new_color):
        self.color = new_color
        self.color_widgets = [w for w in self.color_widgets if w.winfo_exists()]
        for widget in self.color_widgets:
            try:
                if isinstance(widget, (ctk.CTkLabel, ctk.CTkEntry)):
                    widget.configure(text_color=new_color)
                else:
                    widget.configure(border_color=new_color)
            except Exception:
                pass
        self.main_tabs.switch()

    # ================================================================= internos
    def _changed(self):
        if self.on_change:
            self.on_change(self.sheet)

    def _defocus(self):
        self.winfo_toplevel().focus()

    def _bind_save(self, entries, save):
        """Enter ou perder o foco salva. Ignora campos já destruídos por um redesenho."""

        def guarded(defocus):
            try:
                save()
            except tk.TclError:
                return
            if defocus:
                self._defocus()

        for entry in entries:
            entry.bind("<Return>", lambda *_: guarded(True))
            entry.bind("<FocusOut>", lambda *_: guarded(False))

    def _get_color(self):
        return self.color

    def _card(self, parent, **pack):
        card = ctk.CTkFrame(parent, fg_color=PANEL, border_color=self.color, border_width=2, corner_radius=10)
        card.pack(**pack)
        self.color_widgets.append(card)
        return card

    def _rebuild(self):
        state = self._tab_state()
        for child in self.winfo_children():
            child.destroy()
        self.color = self.sheet.get("cor", self.color)
        self.color_widgets = []
        self._build(state)

    def _tab_state(self):
        bars = [self.main_tabs, self.sub_testes, self.sub_detalhes, self.sub_acoes, self.sub_extra]
        return [bar.active for bar in bars]

    # ================================================================= construção
    def _build(self, tab_state=None):
        s = self.sheet

        # --- cabeçalho
        header = self._card(self, fill=tk.X, padx=10, pady=(5, 10))
        self.lbl_nome = ctk.CTkLabel(header, text=s.get("nome", "Sem Nome").upper(),
                                     font=ctk.CTkFont(family=TITLE_FONT, size=20, weight="bold"), text_color=TEXT)
        self.lbl_nome.pack(side=tk.LEFT, padx=20, pady=12)
        info = (f"Classe/Nível: {s.get('classe_nivel', '')}  |  Raça: {s.get('raca', '')}  |  "
                f"Antecedente: {s.get('antecedente', '')}  |  Tendência: {s.get('tendencia', '')}")
        ctk.CTkLabel(header, text=info, font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(side=tk.RIGHT, padx=20, pady=12)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = ctk.CTkFrame(body, fg_color="transparent", width=380)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left.pack_propagate(False)
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self._build_combat(left)
        self._build_attributes(left)
        self._build_tabs(right)

        if tab_state:
            for bar, active in zip(self._bars(), tab_state):
                if active in bar.views:
                    bar.active = active
        self.main_tabs.switch()

    def _bars(self):
        return [self.main_tabs, self.sub_testes, self.sub_detalhes, self.sub_acoes, self.sub_extra]

    def _build_combat(self, parent):
        card = self._card(parent, fill=tk.BOTH, expand=True, pady=(0, 10))
        combate = self.sheet.get("combate", {})

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=15, pady=10)
        stats = [("CA", combate.get("ca", 10)), ("INICIATIVA", fmt_bonus(combate.get("iniciativa", 0))),
                 ("DESLOCAMENTO", combate.get("deslocamento", "9m"))]
        for idx, (label, value) in enumerate(stats):
            stat_widget(grid, label, value).grid(row=0, column=idx, padx=5, sticky="nsew")
            grid.grid_columnconfigure(idx, weight=1)

        hp_frame = ctk.CTkFrame(card, fg_color=PANEL_DARK, corner_radius=8)
        hp_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 12))
        ctk.CTkLabel(hp_frame, text="PONTOS DE VIDA", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT_MUTED).pack(pady=(6, 0))
        self.hp_label = ctk.CTkLabel(hp_frame, text="", font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT)
        self.hp_label.pack(pady=2)
        self.hp_bar = ctk.CTkProgressBar(hp_frame, fg_color=BUTTON, progress_color="#444444", width=280, height=10)
        self.hp_bar.pack(pady=4)

        controls = ctk.CTkFrame(hp_frame, fg_color="transparent")
        controls.pack(pady=(8, 12))
        for delta in (-5, -1):
            small_button(controls, f"{delta}", lambda d=delta: self._adjust_hp(d)).pack(side=tk.LEFT, padx=3)
        self.hp_input = ctk.CTkEntry(controls, width=55, height=22, fg_color=INPUT, border_color=BORDER,
                                     font=ctk.CTkFont(size=11), placeholder_text="Val")
        self.hp_input.pack(side=tk.LEFT, padx=4)
        self.hp_input.bind("<Return>", lambda *_: (self._set_hp_from_input(), self._defocus()))
        small_button(controls, "Def", self._set_hp_from_input).pack(side=tk.LEFT, padx=3)
        for delta in (1, 5):
            small_button(controls, f"+{delta}", lambda d=delta: self._adjust_hp(d)).pack(side=tk.LEFT, padx=3)
        self._render_hp()

    def _build_attributes(self, parent):
        card = self._card(parent, fill=tk.BOTH, expand=True, pady=(10, 0))
        ctk.CTkLabel(card, text="ATRIBUTOS", font=ctk.CTkFont(family=TITLE_FONT, size=13, weight="bold"),
                     text_color=TEXT).pack(pady=8)
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        for idx, (sigla, key) in enumerate(ATTRIBUTES):
            row, col = divmod(idx, 3)
            box = ctk.CTkFrame(grid, fg_color=PANEL_DARK, corner_radius=6, height=90)
            box.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            box.pack_propagate(False)
            grid.grid_columnconfigure(col, weight=1)
            grid.grid_rowconfigure(row, weight=1)
            data = self.sheet.get("atributos", {}).get(key, {"valor": 10, "mod": 0})
            ctk.CTkLabel(box, text=sigla, font=ctk.CTkFont(size=10, weight="bold"), text_color="#666666").pack(pady=(8, 2))
            ctk.CTkLabel(box, text=fmt_bonus(data.get("mod", 0)), font=ctk.CTkFont(size=20, weight="bold"),
                         text_color=TEXT).pack(pady=2)
            ctk.CTkLabel(box, text=str(data.get("valor", 10)), font=ctk.CTkFont(size=11),
                         text_color=TEXT_MUTED).pack(pady=(2, 8))

    def _build_tabs(self, parent):
        container = self._card(parent, fill=tk.BOTH, expand=True)
        content = ctk.CTkFrame(container, fg_color="transparent")
        self.main_tabs = TabBar(container, content, self._get_color, main=True)
        self.main_tabs.header.pack(fill=tk.X, side=tk.TOP)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        def section(name):
            view = ctk.CTkFrame(content, fg_color="transparent")
            sub_content = ctk.CTkFrame(view, fg_color="transparent")
            bar = TabBar(view, sub_content, self._get_color)
            bar.header.pack(fill=tk.X, pady=(0, 10))
            sub_content.pack(fill=tk.BOTH, expand=True)
            self.main_tabs.add(name, view, on_switch=lambda: bar.switch())
            return bar, sub_content

        # Testes
        self.sub_testes, area = section("Testes")
        pericias = ctk.CTkScrollableFrame(area, fg_color=PANEL_DARK)
        self.sub_testes.add("Perícias", pericias)
        for name, data in self.sheet.get("pericias", {}).items():
            self._proficiency_row(pericias, name.upper(), data, height=30, dot_size=14, bonus_size=11, pady=2)
        resist = ctk.CTkScrollableFrame(area, fg_color=PANEL_DARK)
        self.sub_testes.add("Resistências", resist)
        for name, data in self.sheet.get("resistencia", {}).items():
            self._proficiency_row(resist, f"TESTE DE RESISTÊNCIA DE {name.upper()}", data,
                                  height=35, dot_size=16, bonus_size=12, pady=3)

        # Detalhes
        self.sub_detalhes, area = section("Detalhes")
        caract = ctk.CTkScrollableFrame(area, fg_color=PANEL_DARK)
        self.sub_detalhes.add("Características", caract)
        for feat in self.sheet.get("caracteristicas", []):
            row = ctk.CTkFrame(caract, fg_color=PANEL)
            row.pack(fill=tk.X, pady=4, padx=5)
            ctk.CTkLabel(row, text=str(feat.get("nome", "Habilidade")).upper(), font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=TEXT).pack(anchor=tk.W, padx=12, pady=(6, 2))
            ctk.CTkLabel(row, text=feat.get("detalhes", ""), font=ctk.CTkFont(size=11), text_color=TEXT_MUTED,
                         wraplength=450, justify=tk.LEFT).pack(anchor=tk.W, padx=12, pady=(0, 6))
        outros = ctk.CTkScrollableFrame(area, fg_color=PANEL_DARK)
        self.sub_detalhes.add("Outros", outros)
        for title, key, top in (("IDIOMAS", "idiomas", 10), ("PROFICIÊNCIAS", "proficiencias", 15)):
            ctk.CTkLabel(outros, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=TEXT_MUTED).pack(anchor=tk.W, padx=10, pady=(top, 5))
            for text in self.sheet.get(key, []):
                row = ctk.CTkFrame(outros, fg_color=PANEL, height=26)
                row.pack(fill=tk.X, pady=2, padx=5)
                ctk.CTkLabel(row, text=str(text), font=ctk.CTkFont(size=11), text_color=TEXT).pack(side=tk.LEFT, padx=15)

        # Ações
        self.sub_acoes, area = section("Ações")
        self.attacks_view = ctk.CTkFrame(area, fg_color="transparent")
        self.sub_acoes.add("Ataques", self.attacks_view)
        self._populate_attacks()
        self.spells_view = ctk.CTkFrame(area, fg_color="transparent")
        self.sub_acoes.add("Magias", self.spells_view)
        self._populate_spells()

        # Inventário
        inv = ctk.CTkFrame(content, fg_color="transparent")
        self.main_tabs.add("Inventário", inv)
        add_row = ctk.CTkFrame(inv, fg_color="transparent")
        add_row.pack(fill=tk.X, pady=(0, 10))
        self.item_entry = ctk.CTkEntry(add_row, placeholder_text="Adicionar item ao inventário...",
                                       fg_color=INPUT, border_color=BORDER)
        self.item_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.item_entry.bind("<Return>", lambda *_: (self._add_item(), self._defocus()))
        ctk.CTkButton(add_row, text="Adicionar", fg_color=BUTTON, hover_color=BUTTON_HOVER, width=80,
                      command=self._add_item).pack(side=tk.RIGHT)
        self.inv_scroll = ctk.CTkScrollableFrame(inv, fg_color=PANEL_DARK)
        self.inv_scroll.pack(fill=tk.BOTH, expand=True)
        self._populate_inventory()

        # Extra
        self.sub_extra, area = section("Extra")
        self.extra_views = {}
        extra = self.sheet.get("extra", {})
        if not extra:
            empty = ctk.CTkFrame(area, fg_color="transparent")
            self.sub_extra.add("Nada aqui", empty)
            ctk.CTkLabel(empty, text="Esta ficha não tem recursos extras.", text_color=TEXT_FAINT).pack(pady=20)
        for key in extra:
            view = ctk.CTkFrame(area, fg_color="transparent")
            self.extra_views[key] = view
            self.sub_extra.add(EXTRA_NAMES.get(key, key.replace("_", " ").title()), view)
            self._populate_extra(key)

    def _proficiency_row(self, parent, label, data, height, dot_size, bonus_size, pady):
        row = ctk.CTkFrame(parent, fg_color=PANEL, height=height)
        row.pack(fill=tk.X, pady=pady, padx=5)
        prof = bool(data.get("proficiente", False))
        dot = ctk.CTkLabel(row, text="●" if prof else "○", font=ctk.CTkFont(size=dot_size),
                           text_color=self.color if prof else "#444444")
        dot.pack(side=tk.LEFT, padx=10)
        if prof:
            self.color_widgets.append(dot)
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT).pack(side=tk.LEFT)
        ctk.CTkLabel(row, text=fmt_bonus(data.get("bonus", 0)), font=ctk.CTkFont(size=bonus_size, weight="bold"),
                     text_color=TEXT_MUTED).pack(side=tk.RIGHT, padx=15)

    @staticmethod
    def _clear(frame):
        for child in frame.winfo_children():
            child.destroy()

    def _prune_color_widgets(self):
        self.color_widgets = [w for w in self.color_widgets if w.winfo_exists()]

    def _add_row_controls(self, parent, first_placeholder, second_placeholder, on_add):
        """Linha com dois campos + botão Adicionar (Enter também adiciona)."""
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(0, 10))
        first = text_entry(ctrl, first_placeholder)
        first.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        second = text_entry(ctrl, second_placeholder)
        second.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        button = ctk.CTkButton(ctrl, text="Adicionar", fg_color=BUTTON, hover_color=BUTTON_HOVER, width=80, height=26,
                               font=ctk.CTkFont(size=11), command=lambda: on_add(first, second))
        button.pack(side=tk.RIGHT, padx=(5, 0))
        first.bind("<Return>", lambda *_: button.invoke())
        second.bind("<Return>", lambda *_: button.invoke())
        return first, second, button

    def _editable_pair_row(self, parent, item, on_save, on_remove):
        """Linha com nome (na cor da ficha) e descrição editáveis no lugar."""
        row = ctk.CTkFrame(parent, fg_color=PANEL)
        row.pack(fill=tk.X, pady=4, padx=5)
        box = ctk.CTkFrame(row, fg_color="transparent")
        box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=4)
        name = ctk.CTkEntry(box, fg_color="transparent", border_width=0, text_color=self.color,
                            font=ctk.CTkFont(size=12, weight="bold"), height=22)
        name.insert(0, str(item.get("nome", "")).upper())
        name.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(2, 0))
        self.color_widgets.append(name)
        desc = ctk.CTkEntry(box, fg_color="transparent", border_width=0, text_color=TEXT_MUTED,
                            font=ctk.CTkFont(size=11), height=20)
        desc.insert(0, str(item.get("descricao", "")))
        desc.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(0, 2))
        self._bind_save((name, desc), lambda: on_save(name.get(), desc.get()))
        small_button(row, "X", on_remove, width=24, danger=True, height=20).pack(side=tk.RIGHT, padx=10, pady=10)

    # ================================================================= HP
    def _render_hp(self):
        combate = self.sheet.get("combate", {})
        hp, hp_max = combate.get("hp_atual", 0), combate.get("hp_max", 0)
        self.hp_label.configure(text=f"{hp} / {hp_max}")
        self.hp_bar.set(hp / max(1, hp_max))

    def _set_hp(self, value):
        combate = self.sheet.setdefault("combate", {})
        value = max(0, min(int(value), combate.get("hp_max", 0)))
        if value == combate.get("hp_atual"):
            return
        combate["hp_atual"] = value
        self._render_hp()
        self._changed()

    def _adjust_hp(self, delta):
        self._set_hp(self.sheet.get("combate", {}).get("hp_atual", 0) + delta)

    def _set_hp_from_input(self):
        text = self.hp_input.get().strip()
        try:
            value = int(text)
        except ValueError:
            return
        self.hp_input.delete(0, tk.END)
        self._set_hp(value)

    # ================================================================= Inventário
    def _populate_inventory(self):
        self._clear(self.inv_scroll)
        for idx, item in enumerate(self.sheet.get("inventario", [])):
            row = ctk.CTkFrame(self.inv_scroll, fg_color=PANEL, height=32)
            row.pack(fill=tk.X, pady=2, padx=5)
            entry = ctk.CTkEntry(row, fg_color="transparent", border_width=0, text_color=TEXT, font=ctk.CTkFont(size=12))
            entry.insert(0, item)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
            self._bind_save((entry,), lambda i=idx, ent=entry: self._edit_item(i, ent.get()))
            small_button(row, "X", lambda i=idx: self._remove_item(i), width=24, danger=True,
                         height=20).pack(side=tk.RIGHT, padx=5, pady=5)

    def _edit_item(self, idx, text):
        items = self.sheet.get("inventario", [])
        text = text.strip()
        if text and idx < len(items) and items[idx] != text:
            items[idx] = text
            self._changed()

    def _add_item(self):
        text = self.item_entry.get().strip()
        if text:
            self.sheet.setdefault("inventario", []).append(text)
            self.item_entry.delete(0, tk.END)
            self._populate_inventory()
            self._changed()

    def _remove_item(self, idx):
        items = self.sheet.get("inventario", [])
        if idx < len(items):
            items.pop(idx)
            self._populate_inventory()
            self._changed()

    # ================================================================= Ataques
    def _populate_attacks(self):
        self._clear(self.attacks_view)
        self._prune_color_widgets()
        self._add_row_controls(self.attacks_view, "Nome do novo ataque...",
                               "Descrição (ex: Bônus: +5 | Dano: 2d6+3)...", self._add_attack)
        scroll = ctk.CTkScrollableFrame(self.attacks_view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for idx, attack in enumerate(self.sheet.get("ataques", [])):
            self._editable_pair_row(scroll, attack,
                                    on_save=lambda n, d, i=idx: self._edit_named("ataques", i, n, d),
                                    on_remove=lambda i=idx: self._remove_named("ataques", i))

    def _add_attack(self, name_entry, desc_entry):
        name = name_entry.get().strip()
        if not name:
            return
        self.sheet.setdefault("ataques", []).append({"nome": name, "descricao": desc_entry.get().strip()})
        self._populate_attacks()
        self._changed()

    def _named_list(self, kind):
        if kind == "magias":
            return self.sheet.setdefault("magias", {}).setdefault("lista", [])
        return self.sheet.setdefault(kind, [])

    def _edit_named(self, kind, idx, name, desc):
        items = self._named_list(kind)
        name, desc = name.strip(), desc.strip()
        if idx < len(items) and name and (items[idx].get("nome", "").upper() != name.upper()
                                          or items[idx].get("descricao", "") != desc):
            items[idx]["nome"] = name
            items[idx]["descricao"] = desc
            self._changed()

    def _remove_named(self, kind, idx):
        items = self._named_list(kind)
        if idx < len(items):
            items.pop(idx)
            (self._populate_spells if kind == "magias" else self._populate_attacks)()
            self._changed()

    # ================================================================= Magias
    def _populate_spells(self):
        view = self.spells_view
        self._clear(view)
        self._prune_color_widgets()
        magias = self.sheet.setdefault("magias", {})

        info = ctk.CTkFrame(view, fg_color=PANEL)
        info.pack(fill=tk.X, pady=(5, 10), padx=5)
        text = (f"CLASSE: {(magias.get('classe_conjurador') or 'Nenhuma').upper()}  |  "
                f"CD: {magias.get('cd_salvamento', 8)}  |  BÔNUS: {fmt_bonus(magias.get('bonus_ataque', 0))}")
        ctk.CTkLabel(info, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_DIM).pack(pady=8, padx=10)

        ctk.CTkLabel(view, text="ESPAÇOS DE MAGIA", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor=tk.W, padx=10, pady=(5, 2))
        top = ctk.CTkFrame(view, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 4), padx=5)
        bottom = ctk.CTkFrame(view, fg_color="transparent")
        bottom.pack(fill=tk.X, pady=(0, 10), padx=5)
        slots = magias.setdefault("slots", {})
        for lvl in range(1, 10):
            slot = slots.setdefault(str(lvl), {"atual": 0, "max": 0})
            box = ctk.CTkFrame(top if lvl <= 5 else bottom, fg_color=PANEL, width=70, height=52)
            box.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            box.pack_propagate(False)
            ctk.CTkLabel(box, text=f"SLOT {lvl}", font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=TEXT_MUTED).pack(pady=(4, 0))
            vals = ctk.CTkFrame(box, fg_color="transparent")
            vals.pack(pady=(0, 4))
            current = self._slot_entry(vals, slot.get("atual", 0))
            ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=1)
            maximum = self._slot_entry(vals, slot.get("max", 0))
            self._bind_save((current, maximum),
                            lambda l=lvl, a=current, m=maximum: self._edit_slot(l, a.get(), m.get()))

        ctk.CTkLabel(view, text="LISTA DE TRUQUES E MAGIAS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor=tk.W, padx=10, pady=(5, 2))
        self._add_row_controls(view, "Nome da nova magia...", "Descrição/efeito da magia...", self._add_spell)
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for idx, spell in enumerate(magias.setdefault("lista", [])):
            self._editable_pair_row(scroll, spell,
                                    on_save=lambda n, d, i=idx: self._edit_named("magias", i, n, d),
                                    on_remove=lambda i=idx: self._remove_named("magias", i))

    @staticmethod
    def _slot_entry(parent, value):
        entry = ctk.CTkEntry(parent, width=24, height=18, fg_color=INPUT, border_color=BORDER,
                             font=ctk.CTkFont(size=10), justify="center")
        entry.insert(0, str(value))
        entry.pack(side=tk.LEFT, padx=1)
        return entry

    def _edit_slot(self, lvl, current, maximum):
        try:
            maximum = max(0, int(maximum))
            current = max(0, min(int(current), maximum))
        except ValueError:
            return
        slots = self.sheet.setdefault("magias", {}).setdefault("slots", {})
        new = {"atual": current, "max": maximum}
        if slots.get(str(lvl)) == new:
            return
        slots[str(lvl)] = new
        self._changed()
        self.after_idle(self._populate_spells)  # depois do FocusOut terminar

    def _add_spell(self, name_entry, desc_entry):
        name = name_entry.get().strip()
        if not name:
            return
        self._named_list("magias").append({"nome": name, "descricao": desc_entry.get().strip()})
        self._populate_spells()
        self._changed()

    # ================================================================= Extra
    def _extra_items(self, key):
        category = self.sheet.get("extra", {}).get(key, {})
        if isinstance(category, list):
            return category
        if isinstance(category, dict):
            return category.setdefault("lista", [])
        return []

    def _populate_extra(self, key):
        view = self.extra_views.get(key)
        if view is None:
            return
        self._clear(view)
        self._prune_color_widgets()
        category = self.sheet.get("extra", {}).get(key, {})

        if key == "cartas_destino" and isinstance(category, dict):
            self._populate_cards(view, key, category)
            return

        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for idx, item in enumerate(self._extra_items(key)):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=4, padx=5)
            if not isinstance(item, dict):
                ctk.CTkLabel(row, text=str(item), font=ctk.CTkFont(size=12), text_color=TEXT).pack(anchor=tk.W, padx=12, pady=8)
                continue
            title = ctk.CTkLabel(row, text=str(item.get("nome", "")).upper(), font=ctk.CTkFont(size=12, weight="bold"),
                                 text_color=self.color)
            title.pack(anchor=tk.W, padx=12, pady=(6, 2))
            self.color_widgets.append(title)
            if item.get("valor_atual") is not None and item.get("valor_maximo") is not None:
                vals = ctk.CTkFrame(row, fg_color="transparent")
                vals.pack(anchor=tk.W, padx=12, pady=2)
                ctk.CTkLabel(vals, text="Valor: ", font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(side=tk.LEFT)
                entry = ctk.CTkEntry(vals, width=35, height=20, fg_color=INPUT, border_color=BORDER, font=ctk.CTkFont(size=10))
                entry.insert(0, str(item.get("valor_atual")))
                entry.pack(side=tk.LEFT, padx=3)
                self._bind_save((entry,), lambda i=idx, ent=entry: self._edit_extra_value(key, i, ent.get()))
                ctk.CTkLabel(vals, text=f"/ {item.get('valor_maximo')}", font=ctk.CTkFont(size=11),
                             text_color=TEXT_DIM).pack(side=tk.LEFT, padx=3)
            details = item.get("efeito", item.get("detalhes", ""))
            ctk.CTkLabel(row, text=details, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, wraplength=450,
                         justify=tk.LEFT).pack(anchor=tk.W, padx=12, pady=(2, 6))

    def _edit_extra_value(self, key, idx, value):
        items = self._extra_items(key)
        value = value.strip()
        if idx < len(items) and isinstance(items[idx], dict) and str(items[idx].get("valor_atual")) != value:
            items[idx]["valor_atual"] = value
            self._changed()

    def _populate_cards(self, view, key, category):
        maximum = category.get("maximo", 3)
        cards = category.setdefault("lista", [])
        full = len(cards) >= maximum

        ctrl = ctk.CTkFrame(view, fg_color="transparent")
        ctrl.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(ctrl, text=f"CARTAS: {len(cards)} / {maximum}", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).pack(side=tk.LEFT, padx=(5, 15))
        name = text_entry(ctrl, "Nome da carta...")
        name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        effect = text_entry(ctrl, "Efeito/detalhes...")
        effect.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        button = ctk.CTkButton(ctrl, text="Adicionar", fg_color=BUTTON, hover_color=BUTTON_HOVER, width=80, height=26,
                               font=ctk.CTkFont(size=11), command=lambda: self._add_card(key, name, effect))
        button.pack(side=tk.RIGHT, padx=(5, 0))
        if full:
            button.configure(state="disabled", fg_color="#1a1a1a", text_color=TEXT_FAINT)
            name.configure(state="disabled")
            effect.configure(state="disabled")
        else:
            name.bind("<Return>", lambda *_: button.invoke())
            effect.bind("<Return>", lambda *_: button.invoke())

        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for idx, card in enumerate(cards):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=4, padx=5)
            box = ctk.CTkFrame(row, fg_color="transparent")
            box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=6)
            title = ctk.CTkLabel(box, text=str(card.get("nome", "")).upper(), font=ctk.CTkFont(size=12, weight="bold"),
                                 text_color=self.color)
            title.pack(anchor=tk.W)
            self.color_widgets.append(title)
            ctk.CTkLabel(box, text=card.get("efeito", ""), font=ctk.CTkFont(size=11), text_color=TEXT_MUTED,
                         wraplength=400, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))
            small_button(row, "X", lambda i=idx: self._remove_card(key, i), width=24, danger=True,
                         height=20).pack(side=tk.RIGHT, padx=10, pady=10)

    def _add_card(self, key, name_entry, effect_entry):
        name = name_entry.get().strip()
        category = self.sheet.get("extra", {}).get(key, {})
        cards = category.setdefault("lista", [])
        if name and len(cards) < category.get("maximo", 3):
            cards.append({"nome": name, "efeito": effect_entry.get().strip()})
            self._populate_extra(key)
            self._changed()

    def _remove_card(self, key, idx):
        cards = self._extra_items(key)
        if idx < len(cards):
            cards.pop(idx)
            self._populate_extra(key)
            self._changed()
