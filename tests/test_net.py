import socket
import threading
import time

import pytest

from src.net import client as cl
from src.net.client import DNDClient
from src.net.protocol import Connection, ConnectionClosed, recv_msg, send_msg
from src.net.server import DNDServer
from src.sheet_io import load_sheet

HB = dict(heartbeat_interval=0.2, heartbeat_timeout=1.0)


def wait_for(predicate, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False


class Recorder:
    """Guarda os eventos dos callbacks para os testes conferirem."""

    def __init__(self):
        self.events = []
        self.lock = threading.Lock()

    def __call__(self, *args):
        with self.lock:
            self.events.append(args)

    def last(self):
        with self.lock:
            return self.events[-1] if self.events else None


@pytest.fixture
def server():
    srv = DNDServer(host="127.0.0.1", port=0, **HB)
    srv.on_connect, srv.on_disconnect, srv.on_update = Recorder(), Recorder(), Recorder()
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def sheet_file(tmp_path):
    path = tmp_path / "heroi.json"
    path.write_text(open("sheets/dnd-example.json", encoding="utf-8").read(), encoding="utf-8")
    return str(path)


def make_client(server, name="Heroi"):
    c = DNDClient("127.0.0.1", name, port=server.port, max_backoff=0.3, **HB)
    c.on_status, c.on_sheet = Recorder(), Recorder()
    c.start()
    return c


def test_protocolo_ida_e_volta_com_acentos():
    a, b = socket.socketpair()
    send_msg(a, {"type": "sheet", "sheet": {"nome": "Ação"}})
    assert recv_msg(b) == {"type": "sheet", "sheet": {"nome": "Ação"}}
    a.close()
    with pytest.raises(ConnectionClosed):
        recv_msg(b)


def test_fluxo_completo_login_ficha_update_override(server, sheet_file):
    c = make_client(server)
    assert wait_for(lambda: c.state == cl.WAITING)
    assert wait_for(lambda: server.on_connect.last() is not None)

    server.assign_sheet("Heroi", sheet_file, load_sheet(sheet_file))
    assert wait_for(lambda: c.state == cl.ONLINE)
    sheet = c.on_sheet.last()[0]
    assert sheet["nome"] == "Personagem de Exemplo"

    # jogador edita -> salva no disco do mestre
    sheet["combate"]["hp_atual"] = 3
    c.send_update(sheet)
    assert wait_for(lambda: load_sheet(sheet_file)["combate"]["hp_atual"] == 3)
    assert server.on_update.last()[1]["combate"]["hp_atual"] == 3

    # mestre edita -> jogador recebe
    sheet["combate"]["hp_atual"] = 9
    server.update_from_dm("Heroi", sheet)
    assert wait_for(lambda: c.on_sheet.last()[0]["combate"]["hp_atual"] == 9)
    c.close()


def test_desconectar_antes_da_ficha_avisa_o_mestre(server):
    c = make_client(server)
    assert wait_for(lambda: c.state == cl.WAITING)
    c.close()
    assert wait_for(lambda: server.on_disconnect.last() == ("Heroi",))
    assert not server.is_online("Heroi")


def test_reconectar_recebe_a_mesma_ficha_sem_o_mestre_escolher(server, sheet_file):
    server.assign_sheet("Heroi", sheet_file, load_sheet(sheet_file))
    c = make_client(server)
    assert wait_for(lambda: c.state == cl.ONLINE)
    c.close()
    assert wait_for(lambda: not server.is_online("Heroi"))

    c2 = make_client(server)
    assert wait_for(lambda: c2.state == cl.ONLINE)
    assert c2.on_sheet.last()[0]["nome"] == "Personagem de Exemplo"
    c2.close()


def test_mesmo_nome_substitui_conexao_antiga(server, sheet_file):
    server.assign_sheet("Heroi", sheet_file, load_sheet(sheet_file))
    c1 = make_client(server)
    assert wait_for(lambda: c1.state == cl.ONLINE)
    c2 = make_client(server)
    assert wait_for(lambda: c2.state == cl.ONLINE)
    assert wait_for(lambda: c1.state == cl.CLOSED)  # o antigo é avisado e não fica brigando
    assert server.is_online("Heroi")
    c2.close()


def test_servidor_derruba_jogador_que_parou_de_responder(server):
    """PC do jogador suspenso: nenhum byte chega mais. O servidor percebe pelo heartbeat."""
    raw = socket.create_connection(("127.0.0.1", server.port))
    send_msg(raw, {"type": "login", "name": "Dorminhoco", "version": 2})
    assert wait_for(lambda: server.is_online("Dorminhoco"))
    # não lê nem responde mais nada
    assert wait_for(lambda: not server.is_online("Dorminhoco"), timeout=4)
    raw.close()


def test_cliente_percebe_servidor_mudo_e_reconecta_com_edicoes_guardadas(sheet_file):
    """O bug da suspensão do lado do jogador: a conexão morre sem aviso.
    O cliente tem que perceber, reconectar e entregar o que foi editado no meio tempo."""
    # Servidor "fantasma": aceita, responde o login e depois fica mudo (simula a rede morta).
    ghost = socket.socket()
    ghost.bind(("127.0.0.1", 0))
    ghost.listen()
    port = ghost.getsockname()[1]
    held = []

    def ghost_accept():
        s, _ = ghost.accept()
        recv_msg(s)
        send_msg(s, {"type": "welcome", "assigned": True})
        send_msg(s, {"type": "sheet", "sheet": load_sheet(sheet_file)})
        held.append(s)  # nunca mais responde

    threading.Thread(target=ghost_accept, daemon=True).start()
    c = DNDClient("127.0.0.1", "Heroi", port=port, max_backoff=0.3, **HB)
    c.on_status, c.on_sheet = Recorder(), Recorder()
    c.start()
    assert wait_for(lambda: c.state == cl.ONLINE)

    assert wait_for(lambda: c.state == cl.RECONNECTING, timeout=4)
    edited = c.on_sheet.last()[0]
    edited["combate"]["hp_atual"] = 1
    c.send_update(edited)  # editado enquanto sem conexão

    # O servidor de verdade sobe na mesma porta; o cliente volta sozinho.
    ghost.close()
    real = DNDServer(host="127.0.0.1", port=port, **HB)
    real.start()
    real.assign_sheet("Heroi", sheet_file, load_sheet(sheet_file))
    try:
        assert wait_for(lambda: c.state == cl.ONLINE, timeout=6)
        assert wait_for(lambda: load_sheet(sheet_file)["combate"]["hp_atual"] == 1)
    finally:
        c.close()
        real.stop()
        for s in held:
            s.close()


def test_sessao_informa_o_sistema_e_recusa_ficha_de_outro(sheet_file, tmp_path):
    srv = DNDServer(host="127.0.0.1", port=0, system="ordem", **HB)
    srv.start()
    try:
        c = make_client(srv)
        assert wait_for(lambda: c.state == cl.WAITING)
        assert c.system == "ordem"
        with pytest.raises(ValueError):
            srv.assign_sheet("Heroi", sheet_file, load_sheet(sheet_file))  # ficha de D&D
        ordem_file = tmp_path / "o.json"
        ordem_file.write_text(open("sheets/ordem-example.json", encoding="utf-8").read(), encoding="utf-8")
        srv.assign_sheet("Heroi", str(ordem_file), load_sheet(str(ordem_file)))
        assert wait_for(lambda: c.state == cl.ONLINE)

        # jogador tenta mandar a ficha com outro sistema: ignorado
        hacked = c.on_sheet.last()[0]
        hacked["sistema"] = "dnd5e"
        c.send_update(hacked)
        time.sleep(0.5)
        assert load_sheet(str(ordem_file))["sistema"] == "ordem"
        c.close()
    finally:
        srv.stop()


def test_rolagens_vao_para_todos_e_privada_fica_escondida(server):
    a, b = make_client(server, "Ana"), make_client(server, "Beto")
    for c in (a, b):
        c.on_roll = Recorder()
    assert wait_for(lambda: a.state == cl.WAITING and b.state == cl.WAITING)
    dm_rolls = Recorder()
    server.on_roll = dm_rolls

    assert a.send_roll({"sides": 20, "bonus": 3, "private": True})  # jogador não consegue rolar privado
    assert wait_for(lambda: b.on_roll.last() is not None)
    roll = b.on_roll.last()[0]
    assert roll["who"] == "Ana" and not roll["private"] and 4 <= roll["total"] <= 23

    server.roll_as_dm({"sides": 6, "qty": 2}, private=True)
    assert wait_for(lambda: a.on_roll.last()[0].get("hidden"))
    assert "total" not in a.on_roll.last()[0]           # jogador não vê o resultado
    assert dm_rolls.last()[0]["total"] >= 2             # mestre vê

    # quem conecta depois recebe o histórico (com a privada escondida)
    c = DNDClient("127.0.0.1", "Caio", port=server.port, **HB)
    c.on_history = Recorder()
    c.start()
    assert wait_for(lambda: c.on_history.last() is not None)
    history = c.on_history.last()[0]
    assert [r["who"] for r in history] == ["Ana", "Mestre"] and "total" not in history[1]
    for x in (a, b, c):
        x.close()


def test_nome_mestre_e_reservado(server):
    c = make_client(server, "mestre")
    assert wait_for(lambda: c.state == cl.CLOSED)


def test_versao_diferente_e_recusada(server):
    raw = socket.create_connection(("127.0.0.1", server.port))
    send_msg(raw, {"type": "login", "name": "Velho", "version": 1})
    conn = Connection(raw, **HB)
    assert conn.recv()["type"] == "error"
    conn.close()
