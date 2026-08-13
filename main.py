# -*- coding: utf-8 -*-
"""入口：组装 GUI + 截图 + 流水线 + 全局热键 + 系统托盘。

关键设计：
- 所有后台线程结果都通过 Pipeline 的 Qt Signal 回主线程，绝不直接操作 UI，
  从而避免 "QObject: Cannot create children for a parent that is in a different thread"。
- 全局热键用 pynput 后台线程监听，用 QMetaObject.invokeMethod 切回主线程触发截图。
- 关闭按钮 hide() 到托盘，托盘右键提供「退出」。
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QMetaObject, QObject, Qt as _Qt, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox

from config import AppConfig, load_config
from core.pipeline import Pipeline
from ui.main_window import MainWindow
from ui.screenshot import ScreenshotOverlay
from ui.tray import SystemTray


# ---------- 热键解析 ----------
def _parse_hotkey(spec: str):
    """把 "alt+q" 解析为 (set of pynput modifiers, key_char)。"""
    mod_map = {
        "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt", "option": "alt",
        "shift": "shift",
        "cmd": "cmd", "win": "cmd", "super": "cmd",
    }
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    mods = set()
    char = None
    for p in parts:
        if p in mod_map:
            mods.add(mod_map[p])
        else:
            if len(p) == 1:
                char = p
            else:
                # 功能键（f1 等）暂不处理
                raise ValueError(f"不支持的按键: {p}")
    if not char:
        raise ValueError("热键格式错误，缺少字母键，如 'alt+q'")
    return mods, char


class HotkeyBridge(QObject):
    """pynput 热键回调桥：后台线程 invoke 到主线程。"""

    def __init__(self, trigger_fn):
        super().__init__()
        self._trigger = trigger_fn

    @Slot()
    def _do_trigger(self):
        try:
            self._trigger()
        except Exception:
            traceback.print_exc()

    def schedule(self):
        # QueuedConnection：跨线程安全地执行
        QMetaObject.invokeMethod(self, "_do_trigger", _Qt.ConnectionType.QueuedConnection)


def _start_global_hotkey(cfg: AppConfig, bridge: HotkeyBridge) -> tuple[object, str]:
    """启动 pynput 全局热键监听（Listener 手动匹配，比 GlobalHotKeys 更稳）。

    Returns:
        (listener_object_or_None, status_message)
    """
    try:
        from pynput import keyboard
    except Exception as e:
        return None, f"热键不可用：pynput 未安装 ({e})"

    try:
        mods, char = _parse_hotkey(cfg.screenshot_hotkey)
    except Exception as e:
        print(f"[热键] 解析失败: {e}，使用默认 alt+q")
        try:
            mods, char = _parse_hotkey("alt+q")
        except Exception as e2:
            return None, f"热键解析失败: {e2}"

    # 用 Listener 手动匹配，兼容性更好
    pressed_mods: set = set()
    target_char_lower = char.lower()
    fired_on_this_combo = {"flag": False}  # 用可变对象闭包

    def _mod_from_key(k):
        if k == keyboard.Key.ctrl_l or k == keyboard.Key.ctrl_r:
            return "ctrl"
        if k == keyboard.Key.alt_l or k == keyboard.Key.alt_r:
            return "alt"
        if k == keyboard.Key.shift_l or k == keyboard.Key.shift_r:
            return "shift"
        if k == keyboard.Key.cmd_l or k == keyboard.Key.cmd_r:
            return "cmd"
        return None

    def _on_press(key):
        try:
            m = _mod_from_key(key)
            if m is not None:
                pressed_mods.add(m)
                fired_on_this_combo["flag"] = False
                return
            # 字母键 / 数字键：通过 char 比较
            try:
                k_char = key.char.lower()
            except AttributeError:
                return
            if (k_char == target_char_lower
                    and pressed_mods >= mods
                    and not fired_on_this_combo["flag"]):
                fired_on_this_combo["flag"] = True
                try:
                    bridge.schedule()
                except Exception:
                    import traceback
                    traceback.print_exc()
        except Exception:
            import traceback
            traceback.print_exc()

    def _on_release(key):
        try:
            m = _mod_from_key(key)
            if m is not None:
                pressed_mods.discard(m)
                fired_on_this_combo["flag"] = False
                return
            # 释放字母键，重置触发标记（允许再次按下重新触发）
            try:
                k_char = key.char.lower()
                if k_char == target_char_lower:
                    fired_on_this_combo["flag"] = False
            except AttributeError:
                pass
        except Exception:
            import traceback
            traceback.print_exc()

    try:
        listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
        listener.daemon = True
        listener.start()
        combo_hint = "+".join(sorted(mods) + [char])
        print(f"[热键] 已注册全局热键: {combo_hint}")
        return listener, f"热键就绪: {combo_hint}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"热键注册失败: {e}"


class App:
    """应用总控。"""

    def __init__(self, qapp: QApplication, cfg: AppConfig):
        self.qapp = qapp
        self.cfg = cfg
        self.pipeline = Pipeline(cfg)

        self.window = MainWindow(cfg)
        self.overlay = ScreenshotOverlay()
        self.tray = SystemTray()

        # 信号：流水线
        self.pipeline.ocr_ok.connect(self._on_ocr_ok)
        self.pipeline.ocr_err.connect(self._on_ocr_err)
        self.pipeline.translate_ok.connect(self._on_trans_ok)
        self.pipeline.translate_err.connect(self._on_trans_err)
        self.pipeline.busy_changed.connect(self.window.set_busy)

        # 信号：主窗
        self.window.request_screenshot.connect(self._request_screenshot)
        self.window.request_translate.connect(self.pipeline.run_translate)

        # 信号：截图
        self.overlay.captured.connect(self._on_captured)
        self.overlay.canceled.connect(self._on_screenshot_canceled)

        # 信号：托盘
        self.tray.request_show_window.connect(self._show_window)
        self.tray.request_quit.connect(self._quit)

        self._hotkey_obj = None

    # ---------- 启动 ----------
    def start(self):
        self.window.show()
        self.tray.show()
        # 全局热键（先启动，状态栏里会显示热键是否就绪）
        self._hotkey_bridge = HotkeyBridge(self._request_screenshot)
        self._hotkey_obj, hk_msg = _start_global_hotkey(self.cfg, self._hotkey_bridge)
        # 后台启动翻译模型预热（避免首屏 20s）
        if self.cfg.translator.prewarm:
            self.window.set_status(f"后台预热翻译模型中… | {hk_msg}")
            self.pipeline.prewarm_translator()
        else:
            self.window.set_status(f"就绪 | {hk_msg}")

    # ---------- 槽 ----------
    def _request_screenshot(self):
        if self.pipeline.is_running:
            self.window.set_status("上次任务仍在执行，请稍候…")
            return
        # 截图前先隐藏主窗（不触发「关闭→托盘」逻辑），避免被截入画面
        self.window.hideForScreenshot()
        # 延时 150ms 让窗口真正隐藏再抓屏
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._safe_start_overlay)

    def _safe_start_overlay(self):
        """启动覆盖层；任何异常都恢复主窗，避免"消失"。"""
        try:
            self.overlay.start()
        except Exception as e:
            traceback.print_exc()
            self.window.showAfterScreenshot()
            self.window.set_status(f"截图启动失败: {e}")

    def _on_screenshot_canceled(self):
        """用户取消截图（ESC / 选区过小）→ 必须恢复主窗显示。"""
        self.window.showAfterScreenshot()
        self.window.set_status("已取消截图")

    def _on_captured(self, img):
        self.window.showAfterScreenshot()
        self.window.set_status("识别中…")
        self.pipeline.run_ocr_and_translate(img)

    def _on_ocr_ok(self, text: str):
        self.window.set_source(text)
        if not text:
            self.window.showAfterScreenshot()
            self.window.set_status("未识别到文字")
        else:
            self.window.set_status("OCR 完成，翻译中…")

    def _on_ocr_err(self, err: str):
        self.window.set_status(f"OCR 错误: {err}")
        self.window.showAfterScreenshot()

    def _on_trans_ok(self, text: str):
        self.window.set_translation(text)
        self.window.set_status("完成")
        self.window.showAfterScreenshot()

    def _on_trans_err(self, err: str):
        self.window.set_status(f"翻译错误: {err}")
        self.window.showAfterScreenshot()

    def _show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _quit(self):
        try:
            if self._hotkey_obj is not None:
                self._hotkey_obj.stop()
        except Exception:
            pass
        self.tray.hide()
        self.qapp.quit()


def main() -> int:
    # 全局兜底异常钩子：任何未捕获异常都不闪退，弹信息框
    def _excepthook(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb, limit=5))
            QMessageBox.critical(None, "运行错误",
                                 f"发生未预期的错误：\n\n{msg}\n"
                                 "程序可继续运行，或重启以恢复。")
        except Exception:
            pass

    sys.excepthook = _excepthook

    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)  # 关闭主窗不退出（到托盘）
    qapp.setApplicationName("OCR 翻译工具")

    cfg = load_config()
    app = App(qapp, cfg)
    app.start()

    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
