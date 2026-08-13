# -*- coding: utf-8 -*-
"""区域截图模块：全屏覆盖 + 拖拽选区，Esc 取消。

使用 QScreen.grabWindow 抓取全屏作为背景，QPainter 绘制选区框。
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QGuiApplication, QImage
from PySide6.QtWidgets import QWidget


class ScreenshotOverlay(QWidget):
    """全屏截图覆盖层，拖拽选择区域后回调返回 numpy 图像。"""

    captured = Signal(np.ndarray)   # 选区图像 (H,W,3 RGB)
    canceled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setCursor(Qt.CrossCursor)
        self._start = QPoint()
        self._end = QPoint()
        self._dragging = False
        self._bg: Optional[QPixmap] = None

    def start(self) -> None:
        """显示覆盖层并抓取全屏背景。"""
        screen = QGuiApplication.primaryScreen()
        geom = screen.geometry()
        self._bg = screen.grabWindow(0)  # 抓全屏
        self.setGeometry(geom)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    # ---- 鼠标事件 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            rect = QRect(self._start, self._end).normalized()
            self.hide()
            if rect.width() > 4 and rect.height() > 4:
                try:
                    # 从背景截取选区并转换为 numpy（RGB）
                    img = self._bg.copy(rect).toImage().convertToFormat(
                        QImage.Format.Format_RGB888
                    )
                    arr = _qimage_to_numpy(img)
                    self.captured.emit(arr)
                except Exception as e:
                    self.canceled.emit()
            else:
                self.canceled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.canceled.emit()

    # ---- 绘制 ----
    def paintEvent(self, event):
        painter = QPainter(self)
        # 绘制全屏背景
        if self._bg:
            painter.drawPixmap(0, 0, self._bg)
        # 选区外区域半透明遮罩
        if self._dragging:
            rect = QRect(self._start, self._end).normalized()
            mask = QColor(0, 0, 0, 120)
            painter.fillRect(self.rect(), mask)
            # 选区内透出原图
            painter.drawPixmap(rect.topLeft(), self._bg, rect)
            # 边框
            pen = QPen(QColor(0, 174, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            # 尺寸提示
            size_text = f"{rect.width()} x {rect.height()}"
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.topLeft() + QPoint(4, -6), size_text)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.end()


def _qimage_to_numpy(qimage: QImage) -> np.ndarray:
    """QImage(Format_RGB888) 转 numpy 数组 (H,W,3 uint8)。

    不使用 bits() 的 memoryview（新版 PySide6 不兼容 setsize），
    而是用 bits().tobytes() 拿到安全的 bytes 切片。
    """
    assert qimage.format() == QImage.Format.Format_RGB888, (
        "请先 convertToFormat(Format_RGB888)"
    )
    w, h = qimage.width(), qimage.height()
    # bits() 返回的是 memoryview，直接 tobytes 可避免 setsize 问题
    ptr_bytes = bytes(qimage.bits())
    # RGB888 每个像素 3 字节，连续存储
    needed = w * h * 3
    if len(ptr_bytes) < needed:
        # bytesPerLine 有 padding 时，按 stride 取
        row_bytes = qimage.bytesPerLine()
        buf = np.frombuffer(ptr_bytes, dtype=np.uint8)
        buf = buf[: h * row_bytes].reshape(h, row_bytes)
        return buf[:, : w * 3].reshape(h, w, 3).copy()
    return np.frombuffer(ptr_bytes, dtype=np.uint8, count=needed).reshape(h, w, 3).copy()
