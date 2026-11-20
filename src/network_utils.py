import struct
import json

def send_msg(sock, data: dict) -> None:
    """Codifica o dict em JSON, calcula o tamanho, envia o prefixo de 4 bytes e depois o payload."""
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    # Cabeçalho de 4 bytes contendo o tamanho (Big Endian)
    header = struct.pack('>I', len(payload))
    sock.sendall(header + payload)

def recv_msg(sock) -> dict:
    """Lê os 4 bytes do cabeçalho, depois lê exatamente o tamanho especificado do JSON."""
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack('>I', header)[0]
    
    # Lê o payload em pedaços até obter o tamanho total
    data = bytearray()
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data.extend(packet)
        
    return json.loads(data.decode('utf-8'))
