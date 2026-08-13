# -*- coding: utf-8 -*-
"""全局配置：读写 JSON，集中管理路径与运行参数。

配置版本迁移：
- 在 CONFIG_VERSION 内维护"代码侧当前版本"。
- 旧版 config.json 里 config_version 缺失或 < 当前版本时，执行迁移：
  对"典型的旧默认值"（历史上代码默认、用户大概率没改过的值）自动升级为新默认，
  用户手动改过的值（与旧默认不同）则保留不变。
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, asdict, field
from pathlib import Path

# 程序根目录
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
MODELS_DIR = APP_DIR / "models"

# 配置版本号：修改任何默认值（尺寸、热键、use_compile 等）时 +1，
# 并在 _apply_migrations 里加对应迁移规则。
CONFIG_VERSION = 2


@dataclass
class OCRConfig:
    """OCR 配置（PP-OCRv6，模型打包在 rapidocr wheel 内，无需下载）"""
    num_threads: int = 4


@dataclass
class TranslatorConfig:
    """翻译模型配置（Qwen2.5-1.5B + OpenVINO NPU）"""
    model_dir: str = "models/translator/Qwen2.5-1.5B-Instruct-openvino"
    device: str = "NPU"          # 首选设备，不可用时自动回退 NPU→GPU→CPU
    max_new_tokens: int = 512
    temperature: float = 0.3     # 翻译用低温度保证稳定
    use_compile: bool = True     # OpenVINO 编译缓存：首次慢 2-3 分钟，后续启动 <10s
    prewarm: bool = True         # 启动后后台自动预热翻译模型（避免首屏 20s）


@dataclass
class UIConfig:
    """界面配置"""
    always_on_top: bool = True   # 全局置顶（硬性要求）
    opacity: float = 0.98        # 窗口不透明度
    width: int = 820             # 横向布局：两栏并排，宽度加大
    height: int = 440            # 横向布局：高度适当缩小
    font_size: int = 11


@dataclass
class AppConfig:
    ocr: OCRConfig = field(default_factory=OCRConfig)
    translator: TranslatorConfig = field(default_factory=TranslatorConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    screenshot_hotkey: str = "alt+q"  # 全局截图翻译热键（pynput 后台监听）
    config_version: int = CONFIG_VERSION


def _apply_migrations(data: dict) -> tuple[dict, bool]:
    """把旧版 JSON 数据迁移到当前版本。

    Returns:
        (migrated_data, changed)
    """
    changed = False
    data_ver = data.get("config_version", 1)  # 历史版本无此字段，视为 v1

    # --- v1 → v2：横向布局新尺寸 + alt+q 热键 + use_compile=true ---
    if data_ver < 2:
        ui = data.get("ui", {})
        # 旧默认尺寸（520×360）→ 新默认（820×440）；用户若改过则保留
        if ui.get("width") == 520 and ui.get("height") == 360:
            ui["width"] = UIConfig.width
            ui["height"] = UIConfig.height
            data["ui"] = ui
            changed = True
        # 旧默认热键 ctrl+alt+f → 新默认 alt+q
        if data.get("screenshot_hotkey") == "ctrl+alt+f":
            data["screenshot_hotkey"] = AppConfig.__dataclass_fields__[
                "screenshot_hotkey"
            ].default
            changed = True
        # 旧默认 use_compile=false → 新默认 true（打开编译缓存提速）
        tr = data.get("translator", {})
        if tr.get("use_compile") is False:
            tr["use_compile"] = TranslatorConfig.__dataclass_fields__[
                "use_compile"
            ].default
            data["translator"] = tr
            changed = True

    data["config_version"] = CONFIG_VERSION
    return data, changed


def load_config() -> AppConfig:
    """从 JSON 加载配置，文件不存在或损坏则返回默认值。

    自动执行版本迁移；迁移后若字段变化会写回 config.json。
    """
    if not CONFIG_PATH.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        migrated, changed = _apply_migrations(data)
        if changed:
            # 迁移后写回磁盘，下次直接用新值
            try:
                save_config(AppConfig(
                    ocr=OCRConfig(**migrated.get("ocr", {})),
                    translator=TranslatorConfig(**migrated.get("translator", {})),
                    ui=UIConfig(**migrated.get("ui", {})),
                    screenshot_hotkey=migrated.get(
                        "screenshot_hotkey",
                        AppConfig.__dataclass_fields__["screenshot_hotkey"].default,
                    ),
                ))
            except Exception:
                pass  # 写失败不影响加载
        return AppConfig(
            ocr=OCRConfig(**migrated.get("ocr", {})),
            translator=TranslatorConfig(**migrated.get("translator", {})),
            ui=UIConfig(**migrated.get("ui", {})),
            screenshot_hotkey=migrated.get(
                "screenshot_hotkey",
                AppConfig.__dataclass_fields__["screenshot_hotkey"].default,
            ),
        )
    except Exception:
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    """保存配置到 JSON。"""
    data = asdict(cfg)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def to_abs(path: str) -> Path:
    """相对路径转绝对路径（基于程序根目录）。"""
    p = Path(path)
    if p.is_absolute():
        return p
    return (APP_DIR / p).resolve()
