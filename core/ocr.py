# -*- coding: utf-8 -*-
"""OCR 引擎封装：基于 RapidOCR v3（PP-OCRv6，ONNX Runtime CPU）。

PP-OCRv6 模型已打包在 rapidocr wheel 内，pip 安装后即可使用，无需额外下载——
适合目标机器的白名单网络环境。中英文混排识别效果优于 v4/v5。
OCR 模型较小且动态 shape 多，走 CPU 最稳定快速。
"""
from __future__ import annotations

import threading
from typing import Optional

import numpy as np

from config import OCRConfig
from utils.helpers import clean_text


class OCREngine:
    """RapidOCR v3 单例封装，线程安全懒加载。"""

    _instance: Optional["OCREngine"] = None
    _lock = threading.Lock()

    def __init__(self, cfg: OCRConfig):
        self._cfg = cfg
        self._ocr = None  # 延迟初始化，避免未使用时也加载模型

    @classmethod
    def instance(cls, cfg: OCRConfig) -> "OCREngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(cfg)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置实例。"""
        with cls._lock:
            cls._instance = None

    def _ensure_loaded(self) -> None:
        if self._ocr is not None:
            return
        # 延迟导入，避免未安装依赖时整个程序无法启动
        from rapidocr import RapidOCR

        # v3 用 params 字典配置，模型走 wheel 内置 PP-OCRv6 默认值
        self._ocr = RapidOCR(params={
            "Global.log_level": "warning",
            "EngineConfig.onnxruntime.intra_op_num_threads": self._cfg.num_threads,
        })

    def recognize(self, img: np.ndarray | "Image.Image") -> str:
        """识别图像文本，返回清洗后的多行文本。

        Args:
            img: numpy 数组(H,W,3 BGR) 或 PIL.Image
        Returns:
            识别文本，无文本时返回空串。
        """
        self._ensure_loaded()
        # 接受 PIL.Image 输入，转为 BGR numpy
        if hasattr(img, "convert"):
            arr = np.array(img.convert("RGB"))[:, :, ::-1]  # RGB->BGR
        else:
            arr = img

        result = self._ocr(arr)
        txts = getattr(result, "txts", None)
        if not txts:
            return ""
        lines = [t for t in txts if t]
        return clean_text("\n".join(lines))

    def recognize_file(self, path: str) -> str:
        """识别图片文件。"""
        from PIL import Image

        with Image.open(path) as im:
            return self.recognize(im)
