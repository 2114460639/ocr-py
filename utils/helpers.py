# -*- coding: utf-8 -*-
"""通用工具函数：中英方向判断、文本清洗、内存清理。"""
from __future__ import annotations

import ctypes
import unicodedata
from typing import Tuple


def detect_language(text: str) -> str:
    """判断文本主要语言：含 CJK 字符则视为中文，否则英文。
    返回 'zh' 或 'en'。"""
    if not text:
        return "zh"
    cjk_count = 0
    for ch in text:
        if _is_cjk(ch):
            cjk_count += 1
    # CJK 字符占比超过 15% 视为中文
    return "zh" if cjk_count / max(len(text), 1) > 0.15 else "en"


def translation_direction(text: str) -> Tuple[str, str]:
    """根据原文自动决定翻译方向，返回 (src, dst)。"""
    return ("zh", "en") if detect_language(text) == "zh" else ("en", "zh")


def _is_cjk(ch: str) -> bool:
    """判断字符是否属于 CJK 统一汉字区。"""
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF      # CJK 基本汉字
        or 0x3400 <= code <= 0x4DBF   # 扩展 A
        or 0xF900 <= code <= 0xFAFF   # 兼容汉字
        or 0x3040 <= code <= 0x30FF   # 日文假名（保守处理）
    )


def clean_text(text: str) -> str:
    """清洗 OCR 结果：去多余空白，合并断行。"""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # 中英混排时按换行保留结构，但去除行内多余空格
    return "\n".join(lines)


def trim_memory() -> None:
    """尝试释放进程工作集内存（Windows）。"""
    try:
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
    except Exception:
        pass
