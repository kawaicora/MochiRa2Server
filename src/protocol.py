"""
MochiOnline 中心服务器 - 协议定义
"""
import struct
from enum import IntEnum

PROTOCOL_VERSION = 1
PACKET_MAGIC = 0x4D43  # "MC"

# Header: Magic(2) + Version(1) + Type(1) + Length(2) + fromPlayerId(4) + toPlayerId(4) + payloadLen(2) = 16 bytes
HEADER_FORMAT = '<HBBHIIH'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class PacketType(IntEnum):
    Hello = 0x01
    Welcome = 0x02
    PlayerJoin = 0x03
    PlayerLeave = 0x04
    UdpData = 0x10
    UdpBroadcast = 0x11
    Heartbeat = 0x20
    HeartbeatAck = 0x21
    Disconnect = 0x22
    Error = 0xFF


def pack_packet(packet_type: PacketType, data: bytes = b'', from_player_id: int = 0, to_player_id: int = 0, payload_len: int = 0) -> bytes:
    header = struct.pack(HEADER_FORMAT, PACKET_MAGIC, PROTOCOL_VERSION,
                         packet_type.value, len(data), from_player_id, to_player_id, payload_len)
    return header + data


def unpack_header(data: bytes):
    magic, version, ptype, length, from_player_id, to_player_id, payload_len = struct.unpack(HEADER_FORMAT, data)
    if magic != PACKET_MAGIC:
        raise ValueError(f"Invalid magic: {magic:04X}")
    return PacketType(ptype), length, version, from_player_id, to_player_id, payload_len


def pack_hello(game_version: int, game_udp_port: int, player_name: str) -> bytes:
    name_bytes = player_name.encode('utf-8')[:31]
    data = struct.pack('<IH', game_version, game_udp_port) + name_bytes + b'\x00'
    return pack_packet(PacketType.Hello, data)


def unpack_hello(data: bytes):
    game_version, game_udp_port = struct.unpack('<IH', data[:6])
    player_name = data[6:].split(b'\x00')[0].decode('utf-8')
    return game_version, game_udp_port, player_name


def pack_welcome(player_id: int, max_players: int, current_players: int) -> bytes:
    data = struct.pack('<III', player_id, max_players, current_players)
    return pack_packet(PacketType.Welcome, data)


def pack_udp_data(inner_type: int, from_player_id: int, to_player_id: int, payload: bytes) -> bytes:
    return pack_packet(PacketType.UdpData, payload, from_player_id=from_player_id, to_player_id=to_player_id, payload_len=len(payload))


def unpack_udp_data(data: bytes, from_player_id: int, to_player_id: int, payload_len: int) -> tuple:
    return from_player_id, to_player_id, data[:payload_len]


def pack_heartbeat_ack() -> bytes:
    return pack_packet(PacketType.HeartbeatAck)


def pack_player_join(player_id: int, player_name: str) -> bytes:
    name_bytes = player_name.encode('utf-8')[:31]
    data = struct.pack('<I', player_id) + name_bytes + b'\x00'
    return pack_packet(PacketType.PlayerJoin, data)


def pack_player_leave(player_id: int) -> bytes:
    return pack_packet(PacketType.PlayerLeave, struct.pack('<I', player_id))


def pack_error(msg: str) -> bytes:
    return pack_packet(PacketType.Error, msg.encode('utf-8'))


def hexdump(data: bytes, title: str = "") -> str:
    """Hex dump: left hex, right ASCII, aligned."""
    lines = []
    if title:
        lines.append(title)
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        # pad to 48 chars (16 bytes * 3 chars)
        hex_part = hex_part.ljust(48)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {hex_part}  |{ascii_part}|')
    return '\n'.join(lines)
