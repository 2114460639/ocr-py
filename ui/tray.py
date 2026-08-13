# -*- coding: utf-8 -*-
"""系统托盘：最小化后从托盘恢复，提供快捷菜单。"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


def _make_icon() -> QIcon:
    """生成一个简单的程序图标（无外部资源依赖）。"""
    pix = QPixmap(32, 32)
    pix.fill(QColor(0, 120, 215))
    p = QPainter(pix)
    p.setPen(QColor(255, 255, 255))
    p.setFont(QFont("Arial", 14, QFont.Bold))
    p.drawText(pix.rect(), 0x84, "T")  # AlignCenter
    p.end()
    return QIcon(pix)


class SystemTray(QSystemTrayIcon):
    """系统托盘图标。与 main.py 交互用的 Signal：
    - request_show_window: 要求显示主窗
    - request_quit:        要求退出程序
    """

    request_show_window = Signal()
    request_quit = Signal()

    def __init__(self, parent=None):
        super().__init__(_make_icon(), parent)
        self.setToolTip("OCR 翻译工具")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()

        act_show = QAction("显示主窗口", menu)
        act_show.triggered.connect(self.request_show_window.emit)
        menu.addAction(act_show)

        menu.addSeparator()

        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.request_quit.emit)
        menu.addAction(act_quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason) -> None:
        # 单击托盘图标显示主窗
        if reason == QSystemTrayIcon.Trigger:
            self.request_show_window.emit()
