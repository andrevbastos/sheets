"""Janela do jogador: login no mestre e ficha sincronizada.

Uso: uv run player.py
"""
import json
import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from src.net import client as net
from src.net.client import DNDClient
from src.net.protocol import DEFAULT_PORT
from src.sheet_io import SYSTEMS
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, ERROR, OK, PANEL, TEXT, TEXT_DIM, TITLE_FONT, WARN,
                           UiDispatcher, allow_ctrl_c, bring_to_front, install_click_defocus)
from src.ui.dice_window import DiceWindow
from src.ui.systems import make_sheet_view

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".player-prefs.json")


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


def parse_address(text: str):
    """'192.168.0.10' ou '192.168.0.10:5001' -> (host, porta)."""
    host, _, port = text.strip().rpartition(":") if ":" in text else (text.strip(), "", "")
    try:
        return host, int(port) if port else DEFAULT_PORT
    except ValueError:
        return text.strip(), DEFAULT_PORT


class PlayerApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Fichas - Jogador")
        self.root.configure(fg_color=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        install_click_defocus(self.root)
        allow_ctrl_c(self.root, self.on_close)
        bring_to_front(self.root)

        self.ui = UiDispatcher(self.root)
        self.client: DNDClient | None = None
        self.view = None
        self.screen = None
        self.rolls = []
        self.dice_window = None
        self.show_login()

    # ================================================================= telas
    def _swap_screen(self):
        if self.screen is not None:
            self.screen.destroy()
        self.view = None
        self.screen = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        self.screen.pack(fill=tk.BOTH, expand=True)
        return self.screen

    def show_login(self, message="", color=TEXT_DIM):
        self.root.title("Fichas - Jogador")
        self.root.minsize(400, 340)
        self.root.geometry("420x360")
        screen = self._swap_screen()
        prefs = load_prefs()

        ctk.CTkLabel(screen, text="FICHAS DE RPG", font=ctk.CTkFont(family=TITLE_FONT, size=20, weight="bold"),
                     text_color=TEXT).pack(pady=(30, 20))
        self.ip_entry = ctk.CTkEntry(screen, placeholder_text="Endereço do mestre (ex: 192.168.0.10)", width=280,
                                     fg_color=PANEL, border_color=BORDER)
        self.ip_entry.insert(0, prefs.get("address", "127.0.0.1"))
        self.ip_entry.pack(pady=8)
        self.name_entry = ctk.CTkEntry(screen, placeholder_text="Nome do personagem", width=280,
                                       fg_color=PANEL, border_color=BORDER)
        if prefs.get("name"):
            self.name_entry.insert(0, prefs["name"])
        self.name_entry.pack(pady=8)
        self.lbl_login_status = ctk.CTkLabel(screen, text=message, font=ctk.CTkFont(size=11), text_color=color,
                                             wraplength=340)
        self.lbl_login_status.pack(pady=5)
        self.btn_connect = ctk.CTkButton(screen, text="CONECTAR", font=ctk.CTkFont(size=12, weight="bold"), width=280,
                                         fg_color=BUTTON, hover_color=BUTTON_HOVER, command=self.toggle_connection)
        self.btn_connect.pack(pady=(10, 20))
        for entry in (self.ip_entry, self.name_entry):
            entry.bind("<Return>", lambda e: self.toggle_connection())

    def show_sheet(self, sheet):
        screen = self._swap_screen()
        self.root.title(f"Fichas - {sheet.get('nome', self.client.name)}")
        self.root.minsize(1050, 700)
        self.root.geometry("1100x760")

        self.status_bar = ctk.CTkFrame(screen, fg_color=PANEL, corner_radius=0, height=28)
        self.status_bar.pack(fill=tk.X)
        self.lbl_conn = ctk.CTkLabel(self.status_bar, text="", font=ctk.CTkFont(size=11))
        self.lbl_conn.pack(side=tk.LEFT, padx=12, pady=3)
        ctk.CTkButton(self.status_bar, text="Desconectar", width=90, height=22, fg_color=BUTTON,
                      hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=10),
                      command=self.disconnect).pack(side=tk.RIGHT, padx=8, pady=3)
        ctk.CTkButton(self.status_bar, text="Dados", width=90, height=22, fg_color=BUTTON,
                      hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=11, weight="bold"),
                      command=self.open_dice).pack(side=tk.RIGHT, padx=0, pady=3)
        self._set_conn_label(net.ONLINE)

        body = ctk.CTkFrame(screen, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.view = make_sheet_view(body, sheet, on_change=self.client.send_update, on_roll=self.roll_from_sheet)
        self.view.pack(fill=tk.BOTH, expand=True)

    def _set_conn_label(self, state):
        if self.view is None and not hasattr(self, "lbl_conn"):
            return
        texts = {
            net.ONLINE: ("● Conectado ao mestre", OK),
            net.RECONNECTING: ("● Sem conexão. Tentando reconectar... (suas edições serão enviadas quando voltar)", WARN),
            net.WAITING: ("● Conectado, aguardando o mestre...", WARN),
        }
        text, color = texts.get(state, ("● Desconectado", ERROR))
        try:
            self.lbl_conn.configure(text=text, text_color=color)
        except tk.TclError:
            pass

    # ================================================================= conexão
    def toggle_connection(self):
        if self.client is not None:  # botão virou "Cancelar"
            self.disconnect()
            return
        host, port = parse_address(self.ip_entry.get())
        name = self.name_entry.get().strip()
        if not host or not name:
            self.lbl_login_status.configure(text="Endereço e nome são obrigatórios.", text_color=ERROR)
            return
        save_prefs({"address": self.ip_entry.get().strip(), "name": name})

        self.client = DNDClient(host, name, port=port)
        client = self.client
        self.client.on_status = lambda state, msg: self.ui.post(self.on_status, client, state, msg)
        self.client.on_sheet = lambda sheet: self.ui.post(self.on_sheet, client, sheet)
        self.client.on_roll = lambda roll: self.ui.post(self.on_roll, client, roll)
        self.client.on_history = lambda rolls: self.ui.post(self.on_history, client, rolls)
        self.lbl_login_status.configure(text="Conectando...", text_color=TEXT_DIM)
        self.btn_connect.configure(text="CANCELAR")
        for entry in (self.ip_entry, self.name_entry):
            entry.configure(state="disabled")
        self.client.start()

    def on_status(self, client, state, msg):
        if client is not self.client:
            return  # evento atrasado de uma conexão antiga
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.set_enabled(state in (net.ONLINE, net.WAITING))
        if state == net.CLOSED:
            was_in_sheet = self.view is not None
            self.client = None
            self._close_dice()
            if was_in_sheet and msg:
                messagebox.showwarning("Conexão encerrada", msg)
            self.show_login(msg, ERROR if msg else TEXT_DIM)
            return
        if self.view is not None:
            self._set_conn_label(state)
        elif state == net.WAITING:
            system = SYSTEMS.get(client.system, (None,))[0]
            session = f" à sessão de {system}" if system else ""
            self.lbl_login_status.configure(text=f"Conectado{session}!\nAguardando o mestre escolher sua ficha...",
                                            text_color=WARN)
        elif state == net.RECONNECTING:
            self.lbl_login_status.configure(text="Conexão caiu. Tentando de novo...", text_color=WARN)

    def on_sheet(self, client, sheet):
        if client is not self.client:
            return
        if self.view is None:
            self.show_sheet(sheet)
        else:
            self.view.set_sheet(sheet)

    # ================================================================= dados
    def open_dice(self):
        if self.client is None:
            return
        if self.dice_window is None or not self.dice_window.winfo_exists():
            self.dice_window = DiceWindow(self.root, self.client.name, on_roll=self.client.send_roll)
            self.dice_window.set_history(self.rolls)
        self.dice_window.show()

    def roll_from_sheet(self, req):
        """Botão de rolar na ficha: abre a janela de dados (se precisar) e rola."""
        self.open_dice()
        if self.dice_window is not None:
            self.dice_window.roll_request(req)

    def on_roll(self, client, roll):
        if client is not self.client:
            return
        self.rolls = (self.rolls + [roll])[-50:]
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.add_roll(roll)

    def on_history(self, client, rolls):
        if client is not self.client:
            return
        self.rolls = list(rolls)[-50:]
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.set_history(self.rolls)

    def _close_dice(self):
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.destroy()
        self.dice_window = None
        self.rolls = []

    def disconnect(self):
        client, self.client = self.client, None
        if client:
            client.close()
        self._close_dice()
        self.show_login()

    def on_close(self):
        if self.client:
            self.client.close()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    PlayerApp().run()
