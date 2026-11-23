"""Janela separada de rolagem de dados (mestre e jogador).

Quem usa passa `on_roll(pedido) -> bool`: envia o pedido (o servidor do mestre rola) e devolve
False se não deu para enviar. Os resultados chegam depois por `add_roll()` / `set_history()`.
Fechar a janela só a esconde; o histórico continua.
"""
import tkinter as tk

import customtkinter as ctk

from src import dice
from src.sheet_io import to_int
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, ERROR, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM,
                           TEXT_FAINT, TEXT_MUTED, TITLE_FONT, WARN)

MODE_LABELS = {"Normal": dice.NORMAL, "Vantagem": dice.VANTAGEM, "Desvantagem": dice.DESVANTAGEM}
DM_COLOR = "#d4af37"
CRIT_COLORS = {dice.CRIT_SUCCESS: "#2ecc71", dice.CRIT_FAIL: ERROR}
MAX_LINES = 50


class DiceWindow(ctk.CTkToplevel):
    def __init__(self, master, me: str, on_roll, allow_private=False):
        super().__init__(master)
        self.me = me
        self.on_roll = on_roll
        self.title(f"Dados - {me}")
        self.geometry("440x620")
        self.minsize(400, 520)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)  # fechar só esconde
        self.lines = []
        self._build(allow_private)
        self.bind("<Return>", lambda *_: self.roll())

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    # ================================================================= interface
    def _build(self, allow_private):
        ctk.CTkLabel(self, text="ROLAR DADOS", font=ctk.CTkFont(family=TITLE_FONT, size=16, weight="bold"),
                     text_color=TEXT).pack(pady=(14, 8))

        form = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        form.pack(fill=tk.X, padx=14)

        self.die = ctk.CTkSegmentedButton(form, values=[f"d{s}" for s in dice.DICE], height=32,
                                          font=ctk.CTkFont(size=12, weight="bold"))
        self.die.set("d20")
        self.die.pack(fill=tk.X, padx=10, pady=(10, 8))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill=tk.X, padx=10)
        self.qty = self._number(row, "QUANTIDADE", "1")
        self.bonus = self._number(row, "BÔNUS", "0")

        self.mode = ctk.CTkSegmentedButton(form, values=list(MODE_LABELS), height=28,
                                           command=lambda _v: self._update_extra())
        self.mode.set("Normal")
        self.mode.pack(fill=tk.X, padx=10, pady=(10, 4))
        extra_row = ctk.CTkFrame(form, fg_color="transparent")
        extra_row.pack(fill=tk.X, padx=10)
        self.extra_label = ctk.CTkLabel(extra_row, text="DADOS EXTRAS", font=ctk.CTkFont(size=9, weight="bold"),
                                        text_color=TEXT_MUTED)
        self.extra_label.pack(side=tk.LEFT)
        self.extra = ctk.CTkEntry(extra_row, width=50, height=26, justify="center", fg_color=INPUT, border_color=BORDER)
        self.extra.insert(0, "1")
        self.extra.pack(side=tk.LEFT, padx=8)
        self.extra_hint = ctk.CTkLabel(extra_row, text="", font=ctk.CTkFont(size=9), text_color=TEXT_FAINT)
        self.extra_hint.pack(side=tk.LEFT)

        bottom = ctk.CTkFrame(form, fg_color="transparent")
        bottom.pack(fill=tk.X, padx=10, pady=(12, 12))
        self.private = None
        if allow_private:
            self.private = ctk.CTkCheckBox(bottom, text="Privada", font=ctk.CTkFont(size=12), checkbox_width=18,
                                           checkbox_height=18, fg_color=DM_COLOR, hover_color="#b8962e")
            self.private.pack(side=tk.LEFT)
        self.btn_roll = ctk.CTkButton(bottom, text="ROLAR", height=34, width=160, fg_color=BUTTON,
                                      hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=14, weight="bold"),
                                      command=self.roll)
        self.btn_roll.pack(side=tk.RIGHT)
        self._update_extra()

        # Último resultado em destaque
        self.last = ctk.CTkFrame(self, fg_color=PANEL_DARK, corner_radius=10, border_width=2, border_color=PANEL_DARK)
        self.last.pack(fill=tk.X, padx=14, pady=10)
        last = self.last
        self.lbl_total = ctk.CTkLabel(last, text="–", font=ctk.CTkFont(size=40, weight="bold"), text_color=TEXT)
        self.lbl_total.pack(pady=(8, 0))
        self.lbl_crit = ctk.CTkLabel(last, text="", font=ctk.CTkFont(size=13, weight="bold"), height=0)
        self.lbl_crit.pack()
        self.lbl_detail = ctk.CTkLabel(last, text="Nenhuma rolagem ainda", font=ctk.CTkFont(size=11),
                                       text_color=TEXT_DIM, wraplength=380)
        self.lbl_detail.pack(pady=(0, 8))

        ctk.CTkLabel(self, text="HISTÓRICO DA MESA", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor=tk.W, padx=16)
        self.history = ctk.CTkScrollableFrame(self, fg_color=PANEL_DARK)
        self.history.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 14))

    def _number(self, parent, caption, value):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        ctk.CTkLabel(box, text=caption, font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_MUTED).pack(anchor=tk.W)
        entry = ctk.CTkEntry(box, height=28, justify="center", fg_color=INPUT, border_color=BORDER,
                             font=ctk.CTkFont(size=13, weight="bold"))
        entry.insert(0, value)
        entry.pack(fill=tk.X)
        return entry

    def _update_extra(self):
        """Sem vantagem/desvantagem, o campo de dados extras fica cinza e não parece editável."""
        mode = MODE_LABELS[self.mode.get()]
        active = mode != dice.NORMAL
        self.extra.configure(state="normal" if active else "disabled",
                             fg_color=INPUT if active else PANEL,
                             border_color=BORDER if active else PANEL,
                             text_color=TEXT if active else TEXT_FAINT)
        self.extra._entry.configure(cursor="xterm" if active else "arrow")  # cursor do campo interno do CTk
        self.extra_label.configure(text_color=TEXT_MUTED if active else TEXT_FAINT)
        hints = {dice.NORMAL: "", dice.VANTAGEM: "rola a mais e fica com o maior",
                 dice.DESVANTAGEM: "rola a mais e fica com o menor"}
        self.extra_hint.configure(text=hints[mode])

    # ================================================================= ações
    def request(self) -> dict:
        return {
            "sides": int(self.die.get()[1:]),
            "qty": to_int(self.qty.get(), 1),
            "mode": MODE_LABELS[self.mode.get()],
            "extra": to_int(self.extra.get(), 1),
            "bonus": to_int(self.bonus.get(), 0),
            "private": bool(self.private and self.private.get()),
        }

    def roll(self, req=None):
        try:
            req = dice.clean_request(req or self.request())
        except ValueError as exc:
            self._notice(str(exc), ERROR)
            return
        if not self.on_roll(req):
            self._notice("Sem conexão com o mestre. Tente de novo quando reconectar.", WARN)

    def roll_request(self, req: dict):
        """Rolagem pedida pela ficha (botão de perícia, ataque, dano...). Mostra o pedido no formulário e rola.

        A marcação de Privada do mestre vale também para estas rolagens.
        """
        if req.get("sides") in dice.DICE:  # d2/d3 não têm botão: rola mesmo assim
            self.die.set(f"d{req['sides']}")
        for entry, value in ((self.qty, req.get("qty", 1)), (self.bonus, req.get("bonus", 0))):
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        mode = req.get("mode", dice.NORMAL)
        self.mode.set(next(label for label, m in MODE_LABELS.items() if m == mode))
        self.extra.configure(state="normal")
        self.extra.delete(0, tk.END)
        self.extra.insert(0, str(req.get("extra") or 1))
        self._update_extra()
        self.roll({**req, "private": bool(self.private and self.private.get())})

    def set_enabled(self, enabled: bool):
        self.btn_roll.configure(state="normal" if enabled else "disabled")

    def _notice(self, text, color):
        self.lbl_total.configure(text="!", text_color=color)
        self.lbl_crit.configure(text="")
        self.last.configure(border_color=PANEL_DARK)
        self.lbl_detail.configure(text=text, text_color=color)

    # ================================================================= resultados
    def set_history(self, rolls):
        for child in self.history.winfo_children():
            child.destroy()
        self.lines = []
        for r in rolls[-MAX_LINES:]:
            self._add_line(r)

    def add_roll(self, r: dict):
        self._add_line(r)
        mine = r.get("who") == self.me
        if mine and not r.get("hidden"):
            crit = dice.critical(r)
            color = CRIT_COLORS.get(crit, TEXT)
            self.lbl_total.configure(text=str(r["total"]), text_color=color)
            self.lbl_crit.configure(text=dice.CRIT_TEXT.get(crit, ""), text_color=color)
            self.last.configure(border_color=color if crit else PANEL_DARK)
            self.lbl_detail.configure(text=dice.describe(r), text_color=TEXT_DIM)

    def _add_line(self, r: dict):
        mine = r.get("who") == self.me
        crit = dice.critical(r)
        color = CRIT_COLORS.get(crit) or (DM_COLOR if r.get("who") == "Mestre" else (TEXT if mine else TEXT_DIM))
        line = ctk.CTkFrame(self.history, fg_color=PANEL if mine else "transparent", corner_radius=6,
                            border_width=2 if crit else 0, border_color=color)
        top = self.lines[0] if self.lines else None
        if top is not None and top.winfo_exists():
            line.pack(fill=tk.X, pady=2, padx=2, before=top)  # mais recente em cima
        else:
            line.pack(fill=tk.X, pady=2, padx=2)
        text = dice.describe(r)
        total = "?" if r.get("hidden") else str(r["total"])  # privada do mestre: igual às outras, com "?"
        ctk.CTkLabel(line, text=total, width=40, font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=color).pack(side=tk.LEFT, padx=(6, 4))
        ctk.CTkLabel(line, text=text, font=ctk.CTkFont(size=11, weight="bold" if crit else "normal"),
                     text_color=color, wraplength=320, justify=tk.LEFT, anchor="w").pack(side=tk.LEFT, fill=tk.X,
                                                                                       padx=4, pady=4)
        self.lines.insert(0, line)
        while len(self.lines) > MAX_LINES:
            self.lines.pop().destroy()
