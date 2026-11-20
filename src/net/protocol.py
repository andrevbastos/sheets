"""Protocolo de mensagens: JSON com prefixo de 4 bytes (tamanho, big-endian).

Toda mensagem é um dict com a chave "type":
    cliente -> servidor: login {name}, update {sheet}, ping
    servidor -> cliente: welcome {assigned}, sheet {sheet}, error {msg}, kicked {msg}, ping
"""
import json
import socket
import struct
import threading

PROTOCOL_VERSION = 2
DEFAULT_PORT = 5000
HEARTBEAT_INTERVAL = 5.0   # segundos entre pings
HEARTBEAT_TIMEOUT = 15.0   # sem receber nada por este tempo = conexão morta
MAX_MESSAGE_SIZE = 16 * 1024 * 1024

_HEADER = struct.Struct(">I")


class ConnectionClosed(Exception):
    """O outro lado fechou a conexão (ou ela caiu)."""


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Lê exatamente `size` bytes; levanta ConnectionClosed se o socket fechar no meio."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionClosed()
        data.extend(chunk)
    return bytes(data)


def send_msg(sock: socket.socket, data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    sock.sendall(_HEADER.pack(len(payload)) + payload)


def recv_msg(sock: socket.socket) -> dict:
    """Lê uma mensagem. Levanta ConnectionClosed, socket.timeout ou ValueError."""
    (length,) = _HEADER.unpack(recv_exact(sock, _HEADER.size))
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"Mensagem grande demais ({length} bytes)")
    message = json.loads(recv_exact(sock, length).decode("utf-8"))
    if not isinstance(message, dict) or "type" not in message:
        raise ValueError("Mensagem sem 'type'")
    return message


class Connection:
    """Socket com envio protegido por lock e heartbeat em segundo plano."""

    def __init__(self, sock: socket.socket, heartbeat_interval=HEARTBEAT_INTERVAL,
                 heartbeat_timeout=HEARTBEAT_TIMEOUT):
        self.sock = sock
        self.heartbeat_interval = heartbeat_interval
        self.sock.settimeout(heartbeat_timeout)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._send_lock = threading.Lock()
        self._closed = threading.Event()
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def send(self, data: dict) -> bool:
        """Envia; devolve False (e fecha) se a conexão estiver quebrada."""
        if self.closed:
            return False
        try:
            with self._send_lock:
                send_msg(self.sock, data)
            return True
        except OSError:
            self.close()
            return False

    def recv(self) -> dict:
        """Recebe a próxima mensagem que não seja ping. Timeout de heartbeat vira ConnectionClosed."""
        while True:
            try:
                message = recv_msg(self.sock)
            except (socket.timeout, OSError, ValueError) as exc:
                self.close()
                raise ConnectionClosed() from exc
            except ConnectionClosed:
                self.close()
                raise
            if message.get("type") != "ping":
                return message

    def _heartbeat_loop(self):
        while not self._closed.wait(self.heartbeat_interval):
            if not self.send({"type": "ping"}):
                break

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
