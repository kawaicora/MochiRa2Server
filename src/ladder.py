"""
MochiOnline 中心服务器 - 排行榜管理 (SQLite 版)
"""
import sqlite3
import time
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LadderEntry:
    """天梯排行榜条目"""
    player_id: int
    player_name: str
    wins: int = 0
    losses: int = 0
    points: int = 1000  # 初始积分
    kills: int = 0
    rank: int = 0
    rung: int = 0
    disconnects: int = 0
    win_streak: int = 0
    last_game_date: int = 0

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return self.wins / total


@dataclass
class HighscoreEntry:
    """高分榜条目"""
    player_id: int
    player_name: str
    wins: int = 0
    losses: int = 0
    points: int = 0
    rank: int = 0
    accomplishments: int = 0


class LadderManager:
    """天梯排行榜管理 - SQLite 存储"""

    def __init__(self, db_path: str = "mochi_online.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 天梯表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ladder (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                points INTEGER DEFAULT 1000,
                kills INTEGER DEFAULT 0,
                disconnects INTEGER DEFAULT 0,
                win_streak INTEGER DEFAULT 0,
                last_game_date INTEGER DEFAULT 0,
                updated_at INTEGER DEFAULT 0
            )
        ''')

        # 高分榜表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS highscore (
                player_id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                accomplishments INTEGER DEFAULT 0,
                updated_at INTEGER DEFAULT 0
            )
        ''')

        # 游戏记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_id INTEGER NOT NULL,
                loser_id INTEGER NOT NULL,
                winner_name TEXT NOT NULL,
                loser_name TEXT NOT NULL,
                winner_kills INTEGER DEFAULT 0,
                loser_kills INTEGER DEFAULT 0,
                played_at INTEGER DEFAULT 0
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ladder_points ON ladder(points DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ladder_name ON ladder(player_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_highscore_points ON highscore(points DESC)')

        conn.commit()
        conn.close()

    def _update_ranks(self):
        """更新排名"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 更新天梯排名
        cursor.execute('''
            UPDATE ladder SET rank = (
                SELECT COUNT(*) + 1 FROM ladder l2
                WHERE l2.points > ladder.points
                   OR (l2.points = ladder.points AND l2.wins > ladder.wins)
            )
        ''')

        # 更新高分榜排名
        cursor.execute('''
            UPDATE highscore SET rank = (
                SELECT COUNT(*) + 1 FROM highscore h2
                WHERE h2.points > highscore.points
            )
        ''')

        conn.commit()
        conn.close()

    def get_or_create(self, player_id: int, player_name: str) -> LadderEntry:
        """获取或创建玩家条目"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM ladder WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()

        if row is None:
            now = int(time.time())
            cursor.execute('''
                INSERT INTO ladder (player_id, player_name, updated_at)
                VALUES (?, ?, ?)
            ''', (player_id, player_name, now))
            conn.commit()
            row = cursor.execute('SELECT * FROM ladder WHERE player_id = ?', (player_id,)).fetchone()

        conn.close()

        return LadderEntry(
            player_id=row['player_id'],
            player_name=row['player_name'],
            wins=row['wins'],
            losses=row['losses'],
            points=row['points'],
            kills=row['kills'],
            disconnects=row['disconnects'],
            win_streak=row['win_streak'],
            last_game_date=row['last_game_date']
        )

    def record_game_result(self, winner_id: int, loser_id: int,
                           winner_name: str, loser_name: str,
                           winner_kills: int = 0, loser_kills: int = 0):
        """记录游戏结果"""
        # 确保两个玩家都存在
        self.get_or_create(winner_id, winner_name)
        self.get_or_create(loser_id, loser_name)

        now = int(time.time())
        conn = self._get_conn()
        cursor = conn.cursor()

        # 更新胜者
        cursor.execute('''
            UPDATE ladder
            SET wins = wins + 1,
                kills = kills + ?,
                win_streak = win_streak + 1,
                points = points + 25,
                last_game_date = ?,
                updated_at = ?
            WHERE player_id = ?
        ''', (winner_kills, now, now, winner_id))

        # 更新败者
        cursor.execute('''
            UPDATE ladder
            SET losses = losses + 1,
                kills = kills + ?,
                win_streak = 0,
                points = MAX(points - 20, 0),
                last_game_date = ?,
                updated_at = ?
            WHERE player_id = ?
        ''', (loser_kills, now, now, loser_id))

        # 记录游戏历史
        cursor.execute('''
            INSERT INTO game_history (winner_id, loser_id, winner_name, loser_name,
                                       winner_kills, loser_kills, played_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (winner_id, loser_id, winner_name, loser_name, winner_kills, loser_kills, now))

        conn.commit()
        conn.close()

        # 更新排名
        self._update_ranks()

    def record_disconnect(self, player_id: int, player_name: str):
        """记录断线"""
        self.get_or_create(player_id, player_name)

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE ladder SET disconnects = disconnects + 1, updated_at = ?
            WHERE player_id = ?
        ''', (int(time.time()), player_id))
        conn.commit()
        conn.close()

    def get_ladder_list(self, limit: int = 100, offset: int = 0) -> List[LadderEntry]:
        """获取天梯列表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM ladder
            ORDER BY points DESC, wins DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        entries = []
        for row in cursor.fetchall():
            entries.append(LadderEntry(
                player_id=row['player_id'],
                player_name=row['player_name'],
                wins=row['wins'],
                losses=row['losses'],
                points=row['points'],
                kills=row['kills'],
                disconnects=row['disconnects'],
                win_streak=row['win_streak'],
                last_game_date=row['last_game_date']
            ))

        conn.close()
        return entries

    def search_player(self, name: str) -> List[LadderEntry]:
        """搜索玩家"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM ladder
            WHERE player_name LIKE ?
            ORDER BY points DESC
            LIMIT 50
        ''', (f'%{name}%',))

        entries = []
        for row in cursor.fetchall():
            entries.append(LadderEntry(
                player_id=row['player_id'],
                player_name=row['player_name'],
                wins=row['wins'],
                losses=row['losses'],
                points=row['points'],
                kills=row['kills'],
                disconnects=row['disconnects'],
                win_streak=row['win_streak'],
                last_game_date=row['last_game_date']
            ))

        conn.close()
        return entries

    def get_player_stats(self, player_id: int) -> Optional[LadderEntry]:
        """获取玩家统计"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM ladder WHERE player_id = ?', (player_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return LadderEntry(
            player_id=row['player_id'],
            player_name=row['player_name'],
            wins=row['wins'],
            losses=row['losses'],
            points=row['points'],
            kills=row['kills'],
            disconnects=row['disconnects'],
            win_streak=row['win_streak'],
            last_game_date=row['last_game_date']
        )

    def get_total_count(self) -> int:
        """获取总玩家数"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM ladder')
        count = cursor.fetchone()['count']
        conn.close()
        return count


class HighscoreManager:
    """高分榜管理 - SQLite 存储"""

    def __init__(self, db_path: str = "mochi_online.db"):
        self.db_path = db_path

    def update_score(self, player_id: int, player_name: str, points: int):
        """更新分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 插入或更新
        cursor.execute('''
            INSERT INTO highscore (player_id, player_name, points, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                points = MAX(points, excluded.points),
                updated_at = excluded.updated_at
        ''', (player_id, player_name, points, int(time.time())))

        conn.commit()
        conn.close()

    def get_highscore_list(self, limit: int = 100) -> List[HighscoreEntry]:
        """获取高分榜列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM highscore
            ORDER BY points DESC
            LIMIT ?
        ''', (limit,))

        entries = []
        for row in cursor.fetchall():
            entries.append(HighscoreEntry(
                player_id=row['player_id'],
                player_name=row['player_name'],
                wins=row['wins'],
                losses=row['losses'],
                points=row['points'],
                accomplishments=row['accomplishments']
            ))

        conn.close()
        return entries
