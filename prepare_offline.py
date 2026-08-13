# -*- coding: utf-8 -*-
"""开发机专用：准备离线翻译模型。

OCR 模型（PP-OCRv6）已打包在 rapidocr wheel 内，目标机器 pip 安装即用，
无需额外准备。本脚本负责从 ModelScope 下载 Qwen2.5-1.5B 权重并导出为
OpenVINO IR，之后把整个 python_version/ 目录拷贝到目标机器即可。

用法（开发机）：
    py -3.12 prepare_offline.py
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS_DIR = ROOT / "models" / "translator" / "Qwen2.5-1.5B-Instruct-openvino"
# ModelScope 下载的原始 HF 权重缓存目录
QWEN_CACHE = ROOT / "models" / "_hf_cache"

QWEN_MS_ID = "Qwen/Qwen2.5-1.5B-Instruct"


def _banner(msg: str) -> None:
    print(f"\n{'=' * 56}\n {msg}\n{'=' * 56}")


def download_qwen() -> Path:
    """从 ModelScope 下载 Qwen2.5-1.5B-Instruct 权重到本地，返回模型目录。"""
    from modelscope import snapshot_download

    QWEN_CACHE.mkdir(parents=True, exist_ok=True)
    print(f"[下载] {QWEN_MS_ID} （ModelScope，约 3GB）...")
    model_dir = snapshot_download(
        QWEN_MS_ID,
        cache_dir=str(QWEN_CACHE),
    )
    print(f"       已下载到: {model_dir}")
    return Path(model_dir)


def export_qwen(model_dir: Path) -> None:
    """用 optimum-cli 把本地 Qwen 权重导出为 OpenVINO IR（INT8 量化）。

    INT8 体积约 1.5GB，NPU/GPU/CPU 均可运行。
    """
    if TRANS_DIR.exists() and (TRANS_DIR / "openvino_model.xml").exists():
        print(f"[跳过] 翻译模型已导出: {TRANS_DIR}")
        return

    print(f"[导出] {model_dir} -> OpenVINO IR (INT8)")
    cmd = [
        sys.executable, "-m", "optimum.commands.optimum_cli",
        "export", "openvino",
        "-m", str(model_dir),
        "--task", "text-generation-with-past",
        "--weight-format", "int8",
        str(TRANS_DIR),
    ]
    print("       命令:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def verify_ocr() -> None:
    """用一张合成图快速验证 OCR（PP-OCRv6 内置模型）可用。"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from core.ocr import OCREngine
    from config import AppConfig

    img = Image.new("RGB", (520, 80), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32)
    except Exception:
        font = ImageFont.load_default()
    d.text((10, 20), "你好世界 Hello 2025", fill="black", font=font)

    eng = OCREngine.instance(AppConfig().ocr)
    text = eng.recognize(img)
    print(f"[验证] OCR 结果: {text!r}")
    if "你好世界" in text and "Hello" in text:
        print("       OCR OK")
    else:
        print("       !!! OCR 结果异常，请检查")


def verify_translator() -> None:
    """验证翻译模型可加载并推理。"""
    from core.translator import TranslatorEngine
    from config import AppConfig

    eng = TranslatorEngine.instance(AppConfig().translator)
    dev = eng._resolve_device()
    print(f"[验证] 翻译设备: {dev}")
    out = eng.translate("你好，世界")
    print(f"[验证] 翻译结果: {out!r}")
    if out:
        print("       翻译 OK")


def main() -> int:
    _banner("步骤 1/4：验证 OCR（PP-OCRv6 内置）")
    try:
        verify_ocr()
    except Exception as e:
        print(f"[警告] OCR 验证失败: {e}")

    _banner("步骤 2/4：从 ModelScope 下载 Qwen2.5-1.5B")
    try:
        model_dir = download_qwen()
    except Exception as e:
        print(f"[错误] 下载失败: {e}")
        return 1

    _banner("步骤 3/4：导出 Qwen2.5-1.5B -> OpenVINO IR")
    try:
        export_qwen(model_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 导出失败: {e}")
        print("可手动运行:")
        print(f"  optimum-cli export openvino -m {model_dir} "
              f"--task text-generation-with-past --weight-format int8 {TRANS_DIR}")
        return 1

    _banner("步骤 4/4：验证翻译模型")
    try:
        verify_translator()
    except Exception as e:
        print(f"[警告] 翻译验证失败: {e}")

    _banner("完成！")
    print(f"翻译模型: {TRANS_DIR}")
    print("OCR 模型: 随 rapidocr wheel 内置，无需单独拷贝")
    print("\n现在把整个 python_version/ 目录拷贝到目标机器，运行 install.bat 即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
