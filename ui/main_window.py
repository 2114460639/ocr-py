# -*- coding: utf-8 -*-
"""主窗体：原文/译文双栏 + 紧凑布局 + 全局置顶（硬性要求）。

布局遵循用户偏好：紧凑、间距小、按钮和输入框窄。
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QCheckBox, QLabel, QStatusBar, QSizePolicy,
)

from config import AppConfig


class MainWindow(QWidget):
    """主窗体。"""

    request_screenshot = Signal()   # 请求截图
    request_translate = Signal(str) # 请求翻译（原文）
    toggle_on_top = Signal(bool)    # 切换置顶

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self._cfg = cfg
        self._programmaticallyHide = False  # True 时 hide() 是内部行为（如截图准备），不需要"关闭→托盘"语义
        self._build_ui()
        self._apply_window_flags()

    # ---- UI 构建 ----
    def _build_ui(self) -> None:
        self.setWindowTitle("OCR 翻译工具")
        self.resize(self._cfg.ui.width, self._cfg.ui.height)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)   # 紧凑外边距
        root.setSpacing(4)                    # 紧凑间距

        # 顶部按钮栏（紧凑、窄按钮）
        bar = QHBoxLayout()
        bar.setSpacing(4)
        self.btn_shot = QPushButton("截图识别")
        self.btn_shot.setFixedWidth(86)
        self.btn_shot.clicked.connect(self.request_screenshot.emit)

        self.btn_trans = QPushButton("翻译")
        self.btn_trans.setFixedWidth(60)
        self.btn_trans.clicked.connect(
            lambda: self.request_translate.emit(self.txt_src.toPlainText())
        )

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setFixedWidth(60)
        self.btn_clear.clicked.connect(self._on_clear)

        self.btn_copy = QPushButton("复制译文")
        self.btn_copy.setFixedWidth(86)
        self.btn_copy.clicked.connect(self._on_copy)

        self.chk_top = QCheckBox("置顶")
        self.chk_top.setChecked(self._cfg.ui.always_on_top)
        self.chk_top.toggled.connect(self._on_top_toggled)

        bar.addWidget(self.btn_shot)
        bar.addWidget(self.btn_trans)
        bar.addWidget(self.btn_clear)
        bar.addWidget(self.btn_copy)
        bar.addStretch(1)
        bar.addWidget(self.chk_top)
        root.addLayout(bar)

        # 中间：横向两栏（原文左 | 译文右）
        body = QHBoxLayout()
        body.setSpacing(4)   # 两栏间紧凑间距

        # --- 左栏：原文 ---
        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        lbl_src = QLabel("原文")
        lbl_src.setFixedHeight(14)
        left_col.addWidget(lbl_src)

        self.txt_src = QPlainTextEdit()
        self.txt_src.setPlaceholderText("截图识别或粘贴原文...")
        self._set_font(self.txt_src)
        self.txt_src.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_col.addWidget(self.txt_src, stretch=1)
        body.addLayout(left_col, stretch=1)

        # --- 右栏：译文 ---
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        lbl_dst = QLabel("译文")
        lbl_dst.setFixedHeight(14)
        right_col.addWidget(lbl_dst)

        self.txt_dst = QPlainTextEdit()
        self.txt_dst.setPlaceholderText("译文显示区...")
        self.txt_dst.setReadOnly(True)
        self._set_font(self.txt_dst)
        self.txt_dst.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_col.addWidget(self.txt_dst, stretch=1)
        body.addLayout(right_col, stretch=1)

        root.addLayout(body, stretch=1)

        # 状态栏
        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.status.showMessage("就绪")
        root.addWidget(self.status)

    def _set_font(self, edit: QPlainTextEdit) -> None:
        f = QFont("Microsoft YaHei", self._cfg.ui.font_size)
        edit.setFont(f)

    def _apply_window_flags(self) -> None:
        flags = Qt.Window | Qt.WindowStaysOnTopHint if self._cfg.ui.always_on_top \
            else Qt.Window
        self.setWindowFlags(flags)
        self.setWindowOpacity(self._cfg.ui.opacity)

    # ---- 对外接口 ----
    def set_source(self, text: str) -> None:
        self.txt_src.setPlainText(text)

    def append_source(self, text: str) -> None:
        self.txt_src.setPlainText(text)

    def set_translation(self, text: str) -> None:
        self.txt_dst.setPlainText(text)

    def set_status(self, msg: str) -> None:
        self.status.showMessage(msg)

    def set_busy(self, busy: bool) -> None:
        self.btn_shot.setEnabled(not busy)
        self.btn_trans.setEnabled(not busy)

    # ---- 内部槽 ----
    def _on_clear(self) -> None:
        self.txt_src.clear()
        self.txt_dst.clear()
        self.status.showMessage("已清空")

    def _on_copy(self) -> None:
        text = self.txt_dst.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.status.showMessage("译文已复制")

    def _on_top_toggled(self, checked: bool) -> None:
        self._cfg.ui.always_on_top = checked
        self._apply_window_flags()
        self.show()  # 重新应用 flags 需要重新显示
        self.toggle_on_top.emit(checked)

    # ---- 关闭事件：用户点 X → 最小化到托盘而非退出。
    #      编程式 hide() 不触发托盘行为（例如截图前先藏主窗）。
    def closeEvent(self, event):
        if self._programmaticallyHide:
            self._programmaticallyHide = False
            super().closeEvent(event)  # 正常接受关闭（hide），不做托盘逻辑
        else:
            # 用户点 X：最小化到托盘
            event.ignore()
            self.hide()

    def hideForScreenshot(self) -> None:
        """供外部调用：截图前先把自己藏一下，不触发关闭/托盘语义。"""
        self._programmaticallyHide = True
        self.hide()

    def showAfterScreenshot(self) -> None:
        """截图完成后恢复显示。"""
        self._programmaticallyHide = False
        self.show()
        self.raise_()
        self.activateWindow()
