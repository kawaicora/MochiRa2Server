# MochiOnline Server

MochiOnline 中心服务器 - CS 模式联机代理

## 功能

- 接收客户端 TCP 连接
- 维护玩家地址表（PlayerID -> Connection 映射）
- 转发游戏 UDP 数据包
- 心跳检测、断线重连
- 支持 Docker 部署
- **排行榜功能** - 天梯、高分榜、玩家搜索
- **游戏结果记录** - 自动记录胜负、积分、击杀
- **SQLite 数据库** - 数据持久化，支持查询和统计

## 架构

```
┌─────────────┐     TCP      ┌─────────────┐     TCP      ┌─────────────┐
│   Client A   │ ──────────→ │   Server    │ ──────────→ │   Client B   │
│  (玩家 A)    │ ←────────── │  (中心)     │ ←────────── │  (玩家 B)    │
└─────────────┘             └─────────────┘             └─────────────┘
```

## 项目结构

```
mochi-online-server/
├── src/
│   ├── __init__.py            # 包初始化
│   ├── __main__.py            # 主程序入口
│   ├── protocol.py             # 协议定义
│   ├── connection.py            # 连接管理
│   └── ladder.py                # 排行榜管理 (SQLite)
├── data/                        # 数据目录（数据库文件）
│   └── mochi_online.db          # SQLite 数据库
├── logs/                        # 日志目录
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 镜像配置
├── docker-compose.yml          # Docker Compose 配置
└── README.md                    # 说明文档
```

## 本地运行

```bash
# 直接运行
python -m src

# 或者使用 docker-compose
docker-compose up -d
```

## Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| PORT | 39247 | 监听端口 |
| MAX_PLAYERS | 8 | 最大玩家数 |
| HEARTBEAT_INTERVAL | 3.0s | 心跳间隔 |
| HEARTBEAT_TIMEOUT | 10.0s | 心跳超时 |

## 协议

详见 `src/protocol.py`

### 数据包格式

```
┌──────────┬──────────┬────────┬────────┬──────────┐
│  Magic   │ Version  │  Type  │ Length │ Reserved │
│  (2字节)  │  (1字节)  │ (1字节)│ (2字节) │  (2字节) │
└──────────┴──────────┴────────┴────────┴──────────┘
```

### 数据包类型

| 类型 | 值 | 说明 |
|------|-----|------|
| Hello | 0x01 | 客户端握手 |
| Welcome | 0x02 | 服务器回复 |
| PlayerJoin | 0x03 | 新玩家加入 |
| PlayerLeave | 0x04 | 玩家离开 |
| UdpData | 0x10 | UDP 数据转发 |
| LadderRequest | 0x30 | 请求天梯列表 |
| LadderResponse | 0x31 | 天梯列表响应 |
| LadderSearch | 0x32 | 搜索玩家 |
| GameResult | 0x34 | 游戏结果上报 |
| HighscoreRequest | 0x36 | 请求高分榜 |
| Heartbeat | 0x20 | 心跳包 |
| HeartbeatAck | 0x21 | 心跳确认 |
| Disconnect | 0x22 | 主动断开 |
| Error | 0xFF | 错误 |
