"""
MochiOnline 中心服务器 - 连接管理
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class ConnectionState(Enum):
    HANDSHAKING = 0
    CONNECTED = 1
    DISCONNECTED = 2


@dataclass
class PlayerConnection:
    player_id: int
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    player_name: str = ""
    game_udp_port: int = 0
    state: ConnectionState = ConnectionState.HANDSHAKING
    last_heartbeat: float = field(default_factory=time.time)

    def update_heartbeat(self):
        self.last_heartbeat = time.time()

    def is_timeout(self, timeout: float = 10.0) -> bool:
        return time.time() - self.last_heartbeat > timeout

    async def close(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass


class ConnectionTable:
    def __init__(self, max_players: int = 8):
        self.max_players = max_players
        self._connections: Dict[int, PlayerConnection] = {}
        self._next_player_id: int = 1
        self._lock = asyncio.Lock()

    async def add(self, reader, writer) -> Optional[PlayerConnection]:
        async with self._lock:
            if len(self._connections) >= self.max_players:
                return None
            pid = self._next_player_id
            self._next_player_id += 1
            conn = PlayerConnection(player_id=pid, reader=reader, writer=writer)
            self._connections[pid] = conn
            return conn

    async def remove(self, player_id: int):
        async with self._lock:
            if player_id in self._connections:
                await self._connections[player_id].close()
                del self._connections[player_id]

    def get(self, player_id: int) -> Optional[PlayerConnection]:
        return self._connections.get(player_id)

    def all(self) -> Dict[int, PlayerConnection]:
        return self._connections.copy()

    def count(self) -> int:
        return len(self._connections)

    async def cleanup_timeout(self, timeout: float = 10.0) -> list:
        timed_out = []
        async with self._lock:
            for pid, conn in list(self._connections.items()):
                if conn.is_timeout(timeout):
                    timed_out.append(pid)
                    await conn.close()
                    del self._connections[pid]
        return timed_out

    async def broadcast(self, data: bytes, exclude_pid: int = None):
        for pid, conn in self._connections.items():
            if exclude_pid is not None and pid == exclude_pid:
                continue
            if conn.state != ConnectionState.CONNECTED:
                continue
            try:
                conn.writer.write(data)
                await conn.writer.drain()
            except Exception:
                await self.remove(pid)
