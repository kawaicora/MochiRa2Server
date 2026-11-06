"""
MochiOnline 中心服务器 - 主程序
"""
import asyncio
import logging
import os
import socket

from .protocol import (
    PacketType, unpack_header, hexdump, HEADER_SIZE,
    unpack_hello, pack_welcome, unpack_udp_data,
    pack_heartbeat_ack, pack_player_join, pack_player_leave, pack_error,
    pack_udp_data,
)
from .connection import ConnectionTable, ConnectionState

HOST = "0.0.0.0"
PORT = 36211
MAX_PLAYERS = 8
HEARTBEAT_INTERVAL = 3.0
HEARTBEAT_TIMEOUT = 10.0

# DEBUG 开关：设置环境变量 MOCHI_DEBUG=1 打印数据包 hexdump
DEBUG = os.environ.get("MOCHI_DEBUG", "0") == "1"

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("MochiOnline")


def debug_dump(data: bytes):
    """仅在 DEBUG 模式下打印 hexdump"""
    if DEBUG:
        for line in hexdump(data).split('\n'):
            log.debug(line)


class Server:
    def __init__(self):
        self.table = ConnectionTable(MAX_PLAYERS)
        self.server = None
        self.running = False

    async def start(self, host=HOST, port=PORT):
        self.running = True
        asyncio.create_task(self._cleanup_loop())
        self.server = await asyncio.start_server(self._handle, host=host, port=port)
        addr = self.server.sockets[0].getsockname()
        log.info(f"MochiOnline Server: {addr[0]}:{addr[1]}")
        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        self.running = False
        for pid in list(self.table.all().keys()):
            await self.table.remove(pid)
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _cleanup_loop(self):
        while self.running:
            try:
                timed_out = await self.table.cleanup_timeout(HEARTBEAT_TIMEOUT)
                for pid in timed_out:
                    log.warning(f"Player {pid} timeout, dropped")
                    await self.table.broadcast(pack_player_leave(pid))
            except Exception as e:
                log.error(f"cleanup error: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _handle(self, reader, writer):
        addr = writer.get_extra_info('peername')
        log.info(f"New connection: {addr}")

        # Disable Nagle: clients send small join/ack packets then a large
        # options packet immediately after. Nagle would hold the large packet
        # until the small one is ACKed, delaying options by 40-200ms.
        try:
            sock = writer.get_extra_info('socket')
            if sock is not None:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as e:
            log.warning(f"setsockopt TCP_NODELAY failed: {e}")

        conn = await self.table.add(reader, writer)
        if not conn:
            writer.write(pack_error("Server full"))
            await writer.drain()
            writer.close()
            return

        try:
            while self.running:
                hdr = await reader.readexactly(HEADER_SIZE)
                ptype, length, _, from_id, to_id, payload_len = unpack_header(hdr)
                body = await reader.readexactly(length) if length > 0 else b''

                full_pkt = hdr + body
                type_name = PacketType(ptype).name
                log.debug(f"[RECV] {type_name} ({len(body)} bytes) from {addr}")
                debug_dump(full_pkt)

                if ptype == PacketType.Hello:
                    game_ver, udp_port, name = unpack_hello(body)
                    conn.player_name = name
                    conn.game_udp_port = udp_port
                    conn.state = ConnectionState.CONNECTED
                    log.info(f"Player {conn.player_id} joined: {name}")

                    welcome = pack_welcome(conn.player_id, MAX_PLAYERS, self.table.count())
                    writer.write(welcome)
                    await writer.drain()
                    log.debug(f"[SEND] Welcome to {addr}")
                    debug_dump(welcome)

                    join_notice = pack_player_join(conn.player_id, name)
                    await self.table.broadcast(join_notice, exclude_pid=conn.player_id)

                elif ptype == PacketType.UdpData:
                    from_id, to_id, payload = unpack_udp_data(body, from_id, to_id, payload_len)
                    conn.update_heartbeat()

                    if to_id == 0xFFFFFFFF:
                        pkt = pack_udp_data(0, from_id, to_id, payload)
                        log.debug(f"[SEND] Broadcast UdpData ({len(payload)} bytes) from {from_id}")
                        debug_dump(pkt)
                        await self.table.broadcast(pkt, exclude_pid=from_id)
                    else:
                        target = self.table.get(to_id)
                        if target and target.state == ConnectionState.CONNECTED:
                            pkt = pack_udp_data(0, from_id, to_id, payload)
                            target.writer.write(pkt)
                            await target.writer.drain()
                            log.debug(f"[SEND] UdpData ({len(payload)} bytes) {from_id} -> {to_id}")
                            debug_dump(pkt)
                        else:
                            log.warning(f"Target player {to_id} not online")

                elif ptype == PacketType.Heartbeat:
                    conn.update_heartbeat()
                    ack = pack_heartbeat_ack()
                    writer.write(ack)
                    await writer.drain()

                elif ptype == PacketType.Disconnect:
                    log.info(f"Player {conn.player_id} disconnect")
                    break

        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            log.error(f"Error: {e}")
        finally:
            await self.table.remove(conn.player_id)
            leave_notice = pack_player_leave(conn.player_id)
            await self.table.broadcast(leave_notice)
            log.info(f"Player {conn.player_id} left")


async def main():
    srv = Server()
    try:
        await srv.start()
    except KeyboardInterrupt:
        pass
    finally:
        await srv.stop()


if __name__ == "__main__":
    asyncio.run(main())
