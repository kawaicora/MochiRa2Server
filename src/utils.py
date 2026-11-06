"""
MochiOnline 中心服务器 - 工具函数
"""


def hexdump(data: bytes, width: int = 16, base: int = 0) -> str:
    """
    格式化打印 hex 数据，左边是 16 进制，右边是 ASCII 文本
    无法识别的字符用 . 表示
    
    格式：
    00000000  48 65 6C 6C 6F 20 57 6F  72 6C 64 21 00 00 00 00  |Hello World!....|
    
    Args:
        data: 要打印的字节数据
        width: 每行显示的字节数
        base: 起始偏移地址
    
    Returns:
        格式化后的字符串
    """
    lines = []
    for i in range(0, len(data), width):
        # 偏移地址
        offset = base + i
        line = f"{offset:08X}  "
        
        # 16 进制部分
        hex_part = []
        for j in range(width):
            if i + j < len(data):
                hex_part.append(f"{data[i + j]:02X}")
            else:
                hex_part.append("  ")
            
            # 每 8 字节加一个空格分隔
            if j == 7:
                hex_part.append(" ")
        
        line += " ".join(hex_part)
        
        # ASCII 文本部分
        ascii_part = []
        for j in range(width):
            if i + j < len(data):
                b = data[i + j]
                # 可打印 ASCII 字符（32-126）
                if 32 <= b <= 126:
                    ascii_part.append(chr(b))
                else:
                    ascii_part.append(".")
            else:
                ascii_part.append(" ")
        
        line += f"  |{''.join(ascii_part)}|"
        
        lines.append(line)
    
    return "\n".join(lines)


def print_hexdump(data: bytes, title: str = "", width: int = 16, base: int = 0) -> None:
    """
    打印 hex dump 数据
    
    Args:
        data: 要打印的字节数据
        title: 标题
        width: 每行显示的字节数
        base: 起始偏移地址
    """
    if title:
        print(f"\n=== {title} ===")
    print(hexdump(data, width, base))
