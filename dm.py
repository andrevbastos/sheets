"""Janela do mestre: servidor + lista de jogadores + ficha selecionada.

Uso: uv run dm.py [--port 5000]
"""
import argparse
import json
import os
import socket
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.net.protocol import DEFAULT_PORT
from src.net.server import DM_NAME, DNDServer
from src.ui.dice_window import DiceWindow
from src.sheet_io import SYSTEMS, create_new_sheet, load_sheet, save_sheet
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, ERROR, OK, PANEL, PANEL_DARK, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, WARN, UiDispatcher, allow_ctrl_c, bring_to_front,
                           install_click_defocus)
from src.ui.systems import life, make_sheet_view

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dm-prefs.json")


@dataclass
class Entry:
    """Um item da barra lateral: jogador da rede ou ficha aberta localmente."""
    key: str
    label: str
    is_player: bool
    filepath: str | None = None
    sheet: dict | None = None
    online: bool = False


def local_ip() -> str:
    """IP desta máquina na rede local (o que os jogadores digitam). Não envia nenhum pacote."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def load_prefs() -> dict:
    try:
        with open(PREFS_PATH, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def save_prefs(prefs: dict):
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as file:
            json.dump(prefs, file)
    except OSError:
        pass


class DMApp:
    def __init__(self, port=DEFAULT_PORT, system=None):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Fichas - Mestre")
        self.root.configure(fg_color=BG)
        self.closed = False
        self.server = None
        self._ctrl_c = allow_ctrl_c(self.root, self.on_close)
        bring_to_front(self.root)

        self.entries: dict[str, Entry] = {}
        self.selected: str | None = None
        self.view = None

        # O mestre define o sistema da sessão; todas as fichas seguem ele.
        self.system = system if system in SYSTEMS else self._pick_system()
        if self.system is None:
            self.closed = True
            self.root.destroy()
            return
        save_prefs({**load_prefs(), "system": self.system})
        self.system_label = SYSTEMS[self.system][0]
        self.root.title(f"Fichas - Mestre ({self.system_label})")
        self.root.geometry("1350x780")
        self.root.minsize(1200, 700)

        self.server = DNDServer(port=port, system=self.system)
        ui = UiDispatcher(self.root)
        self.server.on_connect = ui.wrap(self.on_player_connect)
        self.server.on_disconnect = ui.wrap(self.on_player_disconnect)
        self.server.on_update = ui.wrap(self.on_player_update)
        self.server.on_error = ui.wrap(self.on_server_error)
        self.server.on_roll = ui.wrap(self.on_roll)
        self.rolls = []
        self.dice_window = None

        self._build_ui()
        install_click_defocus(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            self.server.start()
            self.lbl_address.configure(text=f"Endereço para os jogadores:\n{local_ip()}:{self.server.port}")
        except OSError as exc:
            messagebox.showerror("Erro de servidor",
                                 f"Não foi possível abrir o servidor na porta {port}:\n{exc}\n\n"
                                 "Você ainda pode abrir fichas locais.")
            self.lbl_address.configure(text="Servidor desligado", text_color=ERROR)

    # ================================================================= interface
    def _pick_system(self):
        """Tela inicial: o mestre escolhe o sistema da sessão. Devolve a chave ou None (janela fechada)."""
        self.root.geometry("460x300")
        self.root.resizable(False, False)
        choice = tk.StringVar(value="")
        last = load_prefs().get("system")

        frame = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        frame.pack(fill=tk.BOTH, expand=True)
        ctk.CTkLabel(frame, text="NOVA SESSÃO", font=ctk.CTkFont(family=TITLE_FONT, size=20, weight="bold"),
                     text_color="#ffffff").pack(pady=(34, 6))
        ctk.CTkLabel(frame, text="Qual sistema vai ser usado nesta sessão?", text_color=TEXT_DIM).pack(pady=(0, 18))
        for key, (label, _) in SYSTEMS.items():
            ctk.CTkButton(frame, text=label, width=300, height=40, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=BUTTON_HOVER if key == last else BUTTON, hover_color="#4a4a4a",
                          border_width=1 if key == last else 0, border_color=TEXT_MUTED,
                          command=lambda k=key: choice.set(k)).pack(pady=6)

        self.root.protocol("WM_DELETE_WINDOW", lambda: choice.set("__closed__"))
        self._ctrl_c["handler"] = lambda: choice.set("__closed__")
        # O CTk nasce escondido e só aparece no mainloop(); aqui ainda não chegamos nele.
        self.root.deiconify()
        self.root.wait_variable(choice)
        self._ctrl_c["handler"] = self.on_close
        frame.destroy()
        self.root.resizable(True, True)
        return None if choice.get() == "__closed__" else choice.get()

    def _build_ui(self):
        sidebar = ctk.CTkFrame(self.root, width=280, fg_color=PANEL, corner_radius=0)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text=self.system_label.upper(), font=ctk.CTkFont(family=TITLE_FONT, size=14, weight="bold"),
                     text_color="#ffffff").pack(pady=(20, 4))
        self.lbl_address = ctk.CTkLabel(sidebar, text="Iniciando servidor...", font=ctk.CTkFont(size=11),
                                        text_color=TEXT_DIM, justify=tk.CENTER)
        self.lbl_address.pack(pady=(0, 10))

        buttons = ctk.CTkFrame(sidebar, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10)
        for text, command in (("Abrir ficha", self.open_local_sheet), ("Nova ficha", self.create_sheet)):
            ctk.CTkButton(buttons, text=text, fg_color=BUTTON, hover_color=BUTTON_HOVER, height=28,
                          command=command).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ctk.CTkButton(sidebar, text="Dados", fg_color=BUTTON, hover_color=BUTTON_HOVER, height=30,
                      font=ctk.CTkFont(size=13, weight="bold"), command=self.open_dice).pack(fill=tk.X, padx=13, pady=(8, 0))

        self.list_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        self.lbl_status = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(size=10), text_color=ERROR,
                                       wraplength=250, justify=tk.LEFT)
        self.lbl_status.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.detail = ctk.CTkFrame(self.root, fg_color="transparent")
        self.detail.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.refresh_sidebar()
        self.show_selected()

    def refresh_sidebar(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.entries:
            ctk.CTkLabel(self.list_frame, text="Nenhum jogador conectado.\nAbra uma ficha ou espere os jogadores.",
                         font=ctk.CTkFont(size=11, slant="italic"), text_color=TEXT_FAINT).pack(pady=20)
            return
        players = sorted((e for e in self.entries.values() if e.is_player), key=lambda e: e.label.lower())
        local = sorted((e for e in self.entries.values() if not e.is_player), key=lambda e: e.label.lower())
        for entry in players + local:
            self._sidebar_card(entry)

    def _sidebar_card(self, entry: Entry):
        selected = entry.key == self.selected
        color = entry.sheet.get("cor", "#ffffff") if entry.sheet else "#888888"
        card = ctk.CTkFrame(self.list_frame, fg_color="#222222" if selected else PANEL_DARK, corner_radius=8,
                            border_width=2 if selected else 1, border_color=color if selected and entry.sheet else BORDER,
                            height=74)
        card.pack(fill=tk.X, pady=5)
        card.pack_propagate(False)
        widgets = [card]

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=10, pady=(8, 0))
        widgets.append(top)
        if entry.is_player:
            dot = ctk.CTkLabel(top, text="●", font=ctk.CTkFont(size=12), text_color=OK if entry.online else TEXT_FAINT)
            dot.pack(side=tk.LEFT, padx=(0, 6))
            widgets.append(dot)
        name = ctk.CTkLabel(top, text=entry.label.upper(), font=ctk.CTkFont(size=12, weight="bold"),
                            text_color=color if entry.sheet else TEXT_MUTED)
        name.pack(side=tk.LEFT)
        widgets.append(name)
        if not entry.online:
            ctk.CTkButton(top, text="×", width=20, height=18, fg_color="transparent", hover_color="#a83232",
                          text_color=TEXT_MUTED, command=lambda k=entry.key: self.remove_entry(k)).pack(side=tk.RIGHT)

        if entry.sheet:
            label, hp, hp_max = life(entry.sheet)
            ratio = hp / max(1, hp_max)
            bar = ctk.CTkProgressBar(card, fg_color=BUTTON, progress_color=OK if ratio > 0.3 else ERROR, height=5)
            bar.pack(fill=tk.X, padx=10, pady=(6, 2))
            bar.set(ratio)
            widgets.append(bar)
            if entry.is_player:
                status = f"{label}: {hp} / {hp_max}" + ("" if entry.online else "  ·  desconectado")
            else:
                status = f"{label}: {hp} / {hp_max}  ·  ficha local"
        else:
            status = "Sem ficha (clique para escolher)"
        lbl = ctk.CTkLabel(card, text=status, font=ctk.CTkFont(size=10), text_color=TEXT_DIM if entry.sheet else WARN)
        lbl.pack(anchor=tk.W, padx=10, pady=(1, 4))
        widgets.append(lbl)

        for widget in widgets:
            widget.bind("<Button-1>", lambda e, k=entry.key: self.select(k))

    def show_selected(self):
        for child in self.detail.winfo_children():
            child.destroy()
        self.view = None
        entry = self.entries.get(self.selected)
        if not entry or not entry.sheet:
            ctk.CTkLabel(self.detail, text="Selecione uma ficha na lista ao lado", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=TEXT_FAINT).pack(expand=True)
            return
        self.view = make_sheet_view(self.detail, entry.sheet, on_change=lambda s, k=entry.key: self.on_dm_edit(k, s))
        self.view.pack(fill=tk.BOTH, expand=True)

    # ================================================================= ações do mestre
    def select(self, key):
        entry = self.entries.get(key)
        if not entry:
            return
        if entry.is_player and not entry.sheet:
            if not self.assign_sheet_to(entry):
                return
        self.selected = key
        self.refresh_sidebar()
        self.show_selected()

    def assign_sheet_to(self, entry: Entry) -> bool:
        path = filedialog.askopenfilename(title=f"Escolher ficha para {entry.label}",
                                          filetypes=[("Fichas JSON", "*.json")], initialdir=self._sheets_dir())
        if not path:
            return False
        sheet = self._load(path)
        if sheet is None:
            return False
        entry.filepath, entry.sheet = path, sheet
        self.server.assign_sheet(entry.label, path, sheet)
        return True

    def open_local_sheet(self):
        path = filedialog.askopenfilename(title="Abrir ficha", filetypes=[("Fichas JSON", "*.json")],
                                          initialdir=self._sheets_dir())
        if path:
            self._add_local(path)

    def create_sheet(self):
        dialog = ctk.CTkInputDialog(title="Nova ficha", text=f"Nome do personagem ({self.system_label}):")
        name = (dialog.get_input() or "").strip()
        if not name:
            return
        path = filedialog.asksaveasfilename(title="Salvar ficha nova", defaultextension=".json",
                                            initialdir=self._sheets_dir(), initialfile=f"{name}.json",
                                            filetypes=[("Fichas JSON", "*.json")])
        if not path:
            return
        try:
            create_new_sheet(name, self.system, path)
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível criar a ficha:\n{exc}")
            return
        self._add_local(path)

    def _add_local(self, path):
        sheet = self._load(path)
        if sheet is None:
            return
        key = "local:" + os.path.normcase(os.path.abspath(path))
        self.entries[key] = Entry(key=key, label=sheet.get("nome", os.path.basename(path)), is_player=False,
                                  filepath=path, sheet=sheet)
        self.selected = key
        self.refresh_sidebar()
        self.show_selected()

    def remove_entry(self, key):
        entry = self.entries.pop(key, None)
        if entry and entry.is_player:
            self.server.forget(entry.label)
        if self.selected == key:
            self.selected = None
            self.show_selected()
        self.refresh_sidebar()

    def on_dm_edit(self, key, sheet):
        entry = self.entries.get(key)
        if not entry:
            return
        entry.sheet = sheet
        if entry.is_player:
            self.server.update_from_dm(entry.label, sheet)
        else:
            try:
                save_sheet(sheet, entry.filepath)
            except OSError as exc:
                self.on_server_error(None, f"Falha ao salvar {entry.filepath}: {exc}")
        self.refresh_sidebar()

    # ================================================================= dados
    def open_dice(self):
        if self.dice_window is None or not self.dice_window.winfo_exists():
            self.dice_window = DiceWindow(
                self.root, DM_NAME, allow_private=True,
                on_roll=lambda req: bool(self.server.roll_as_dm(req, private=req.get("private", False))))
            self.dice_window.set_history(self.rolls)
        self.dice_window.show()

    def on_roll(self, result):
        self.rolls = (self.rolls + [result])[-50:]
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.add_roll(result)

    # ================================================================= eventos da rede
    def on_player_connect(self, name, addr):
        entry = self.entries.get(name)
        if entry is None:
            entry = Entry(key=name, label=name, is_player=True)
            self.entries[name] = entry
        entry.online = True
        if entry.sheet is None:
            entry.sheet = self.server.get_sheet(name)
        self.refresh_sidebar()

    def on_player_disconnect(self, name):
        entry = self.entries.get(name)
        if not entry:
            return
        if entry.sheet is None:
            # Nunca recebeu ficha: some da lista
            del self.entries[name]
            if self.selected == name:
                self.selected = None
                self.show_selected()
        else:
            # Mantém na lista como desconectado; volta sozinho com a mesma ficha
            entry.online = False
        self.refresh_sidebar()

    def on_player_update(self, name, sheet):
        entry = self.entries.get(name)
        if not entry:
            return
        entry.sheet = sheet
        if self.selected == name and self.view is not None:
            self.view.set_sheet(sheet)
        self.refresh_sidebar()

    def on_server_error(self, name, msg):
        self.lbl_status.configure(text=f"{name + ': ' if name else ''}{msg}")
        self.root.after(8000, lambda: self.lbl_status.configure(text=""))

    # ================================================================= utilidades
    def _load(self, path):
        """Carrega uma ficha e garante que ela é do sistema da sessão."""
        try:
            sheet = load_sheet(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Erro ao abrir ficha", f"Não foi possível ler {os.path.basename(path)}:\n{exc}")
            return None
        system = sheet.get("sistema")
        if system != self.system:
            other = SYSTEMS.get(system, (system or "desconhecido",))[0]
            messagebox.showerror("Sistema diferente",
                                 f"{os.path.basename(path)} é uma ficha de {other}, "
                                 f"mas esta sessão é de {self.system_label}.")
            return None
        return sheet

    @staticmethod
    def _sheets_dir():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets")

    def on_close(self):
        if self.server:
            self.server.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        if not self.closed:
            self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Janela do mestre")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sistema", choices=list(SYSTEMS),
                        help="sistema da sessão (sem isso, o app pergunta ao abrir)")
    args = parser.parse_args()
    DMApp(port=args.port, system=args.sistema).run()
