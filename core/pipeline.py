# -*- coding: utf-8 -*-
"""串接模块：截图 → OCR → 翻译 的完整流水线。

所有异步结果通过 Qt Signal 发回主线程，**绝不直接在后台线程操作 UI 对象**——
这是避免 "QObject: Cannot create children for a parent that is in a different thread" 闪退的关键。
"""
from __future__ import annotations

import threading
import traceback
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Signal

from config import AppConfig
from core.ocr import OCREngine
from core.translator import TranslatorEngine


class Pipeline(QObject):
    """OCR → 翻译流水线，线程化执行，结果用 Signal 回主线程。"""

    ocr_ok = Signal(str)
    ocr_err = Signal(str)
    translate_ok = Signal(str)
    translate_err = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self._cfg = cfg
        self._ocr = OCREngine.instance(cfg.ocr)
        self._translator = TranslatorEngine.instance(cfg.translator)
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def _set_busy(self, v: bool) -> None:
        self._running = v
        self.busy_changed.emit(v)

    # ---------- OCR ----------
    def run_ocr(self, img: np.ndarray) -> None:
        """异步识别图像，完成后发出 ocr_ok / ocr_err。"""
        if self._lock.acquire(blocking=False):
            self._set_busy(True)
            threading.Thread(target=self._ocr_worker, args=(img,), daemon=True).start()
        else:
            self.ocr_err.emit("上一个任务仍在执行")

    def _ocr_worker(self, img: np.ndarray) -> None:
        try:
            text = self._ocr.recognize(img)
            self.ocr_ok.emit(text if text else "")
        except Exception:
            self.ocr_err.emit(traceback.format_exc(limit=2))
        finally:
            if not self._running_translate_pending:
                self._set_busy(False)
                self._lock.release()

    # ---------- 翻译 ----------
    def run_translate(self, text: str) -> None:
        """异步翻译文本，完成后发出 translate_ok / translate_err。"""
        if not text or not text.strip():
            self.translate_ok.emit("")
            return
        if self._lock.acquire(blocking=False):
            self._set_busy(True)
            threading.Thread(target=self._trans_worker, args=(text,), daemon=True).start()
        else:
            self.translate_err.emit("上一个任务仍在执行")

    def _trans_worker(self, text: str) -> None:
        try:
            result = self._translator.translate(text)
            self.translate_ok.emit(result if result else "")
        except Exception:
            self.translate_err.emit(traceback.format_exc(limit=2))
        finally:
            self._set_busy(False)
            self._lock.release()

    # ---------- 一条龙：OCR → 翻译 ----------
    _running_translate_pending = False

    def run_ocr_and_translate(self, img: np.ndarray) -> None:
        """截图 → 识别 → 翻译。"""
        if self._lock.acquire(blocking=False):
            self._set_busy(True)
            self._running_translate_pending = True
            threading.Thread(target=self._pipe_worker, args=(img,), daemon=True).start()
        else:
            self.ocr_err.emit("上一个任务仍在执行")

    def _pipe_worker(self, img: np.ndarray) -> None:
        try:
            text = self._ocr.recognize(img)
            if not text:
                self.ocr_ok.emit("")
                self.translate_ok.emit("")
                return
            self.ocr_ok.emit(text)
            try:
                result = self._translator.translate(text)
                self.translate_ok.emit(result if result else "")
            except Exception:
                self.translate_err.emit(traceback.format_exc(limit=2))
        except Exception:
            self.ocr_err.emit(traceback.format_exc(limit=2))
        finally:
            self._running_translate_pending = False
            self._set_busy(False)
            self._lock.release()

    # ---------- 预热 ----------
    def prewarm_translator(self) -> None:
        """后台预热翻译模型（加载 + 1 次 dummy 推理），避免首屏 20s。"""
        threading.Thread(target=self._prewarm_worker, daemon=True).start()

    def _prewarm_worker(self) -> None:
        try:
            # 首次 _ensure_loaded + 模型图编译会触发编译缓存写入
            # 跑 1 个小 token 推理，把图编译完成
            result = self._translator.translate("Hi")
            # 预热完成不弹 UI，默默占内存
        except Exception:
            # 预热失败不影响主流程
            pass
