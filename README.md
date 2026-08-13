# ocr-py —— 离线 OCR 截图识别 + 中英互译（NPU/GPU/CPU 自动加速）

基于 PySide6 + RapidOCR + Qwen2.5-1.5B-Instruct OpenVINO 打造的**纯本地、100% 离线**桌面翻译工具。针对 Intel 酷睿 Ultra U7 系列（桌面版 无后缀，内置 NPU）做了**推理加速和编译缓存**，同时在无 NPU/GPU 的机器上自动回退到 CPU 推理。

> 开发目标：替代天若 OCR 的付费"截图翻译"插件，主打**离线使用**——不需要 DeepL / 百度 / 有道 / 谷歌 翻译 API，不需要网络，不需要任何 key。

---

## ✨ 功能特性

- **全屏任意区域截图识别**：按住左键拖拽选区，松开立即识别；按 `ESC` 取消（再也不需要鼠标右键等隐藏操作）
- **100% 离线翻译**：Qwen2.5-1.5B-Instruct 模型，OpenVINO IR 格式，支持 `NPU → GPU → CPU` 自动回退
- **中英文双向互译**：自动判断文本方向（中→英 / 英→中），可手动切换 `译入中文` / `译入英文` / `自动`
- **全局快捷键 Alt+Q**：任何时候按下立刻截图识别翻译（pynput 底层键盘钩子，兼容性更稳）
- **横向左右双栏 UI**：原文在左、译文在右，紧凑布局，按钮/输入框更窄，符合"紧凑偏好"
- **窗口全局置顶**：默认开启，随时切回；透明度可调
- **关闭按钮最小化到托盘**：不会误退出，托盘菜单提供「显示 / 截图识别 / 退出」
- **自动模型编译缓存**：首次为你的 NPU/GPU 编译推理图（2-3 分钟），后续启动加载 <10s
- **OpenVINO NPU 首推**：专为 U7 桌面 NPU 优化，推理速度比 CPU 快 4-8 倍

---

## 💻 适用环境

| 项目 | 最低要求 | 推荐 |
|---|---|---|
| CPU | 任意 64 位 x86 | Intel Core Ultra U7 265K / U7 265 / U7265（桌面无后缀，内置 NPU）|
| 内存 | 16 GB | **32 GB DDR5-6400**（翻译模型常驻 ~3 GB，NPU 编译缓存额外 ~1.5 GB）|
| 显卡 | 可选 | Intel Arc 核显 / 独显（GPU FP16 回退）|
| 系统 | Windows 10 x64 | Windows 11 x64 23H2+ |
| 磁盘 | 10 GB 可用空间 | NVMe SSD（编译缓存读写频繁）|
| 网络 | 完全可以断网使用 | 仅首次下载依赖/模型需要（白名单：`pypi.org` + `github.com`）|

---

## 🚀 快速开始（三选一）

### 方式 A：一键脚本（白名单网络电脑直接用）

```powershell
# 1. 克隆仓库
git clone https://github.com/2114460639/ocr-py.git
cd ocr-py

# 2. 一键建虚拟环境 + pip 安装依赖
.\install.ps1

# 3. 准备离线翻译模型（两种方法，见下方「📦 模型获取」章节）

# 4. 启动！
.\run.ps1
```

首次启动后后台会自动预热翻译模型（状态栏会显示"后台预热翻译模型中…"），预热完成前截图翻译也能正常用，只是第一次会等 15-30 秒。后续日常打开 <10s 进入可用状态。

### 方式 B：手动安装

```powershell
git clone https://github.com/2114460639/ocr-py.git
cd ocr-py
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python check_env.py          # 确认依赖 / RapidOCR / OpenVINO NPU 都 OK
```

### 方式 C：从 Release 下载预打包模型（免自己导出）

在本仓库 [Releases](https://github.com/2114460639/ocr-py/releases/latest) 下载 `Qwen2.5-1.5B-Instruct-openvino.zip` 的所有分卷（zip.001、zip.002 ...）放到仓库 `models\translator\` 下，按下方「从分卷解压」的说明合并解压即可，跳过下一节。

---

## 📦 模型获取

### 翻译模型：Qwen2.5-1.5B-Instruct OpenVINO IR

仓库本身**不带大模型**（Git LFS 免费额度太小，GitHub Release 单文件最大 2GB，所以做了分卷打包）。你有三种获取方式：

#### 方案 1️⃣ 从 Releases 直接下载（最推荐，一次导出所有电脑通用）

到 https://github.com/2114460639/ocr-py/releases/tag/v1.0.0 下载 `Qwen2.5-1.5B-Instruct-openvino.zip.001` 以及所有后续分卷（通常是 2-3 个分卷）放到**同一个目录**，然后：

```powershell
# 进入放分卷 zip 的目录，合并解压（PowerShell 自带 7z4 的 cmdlet 或用 7-Zip）
# 方法 A：安装 7-Zip 后
7z x Qwen2.5-1.5B-Instruct-openvino.zip.001 -o"ocr-py\models\translator\"

# 方法 B：没有 7z，用 PowerShell + System.IO.Compression（不支持分卷，不推荐）
# → 请直接用 7-Zip，分卷 ZIP 只有它最稳
```

解压后目录结构应该是：
```
models/
  translator/
    Qwen2.5-1.5B-Instruct-openvino/
      ├── openvino_model.bin   (≈1.5 GB，核心权重)
      ├── openvino_model.xml
      ├── openvino_tokenizer.bin / .xml
      ├── openvino_detokenizer.bin / .xml
      ├── tokenizer.json / tokenizer_config.json
      ├── config.json / generation_config.json / openvino_config.json
      └── chat_template.jinja
```

#### 方案 2️⃣ 自己导出（有网的电脑一次性操作，可离线搬运）

```powershell
.\.venv\Scripts\Activate.ps1
python prepare_offline.py
```

脚本会自动：
1. 从 HuggingFace `Qwen/Qwen2.5-1.5B-Instruct` 下载 FP16 权重（≈3 GB）
2. 用 optimum-intel 导出 OpenVINO INT8 量化模型到 `models/translator/Qwen2.5-1.5B-Instruct-openvino/`
3. 导出模型 ≈ 1.6 GB，拷到任何同款 CPU/OS 的电脑上都能用（NPU/GPU/CPU 编译缓存在**首次推理时本地生成**）

#### 方案 3️⃣ 在线翻译？不，不支持

本项目**从设计上就不做在线翻译**。所有翻译在本地用 1.5B 模型推理做，不会发送任何内容到外网。

### OCR 模型：PP-OCRv6（无需下载！）

RapidOCR 的 PP-OCRv6 中英文模型直接打包在 PyPI wheel 里，`pip install rapidocr-onnxruntime` 就到位，纯本地 ONNX Runtime CPU 推理，**零配置**。

---

## ⌨️ 全局快捷键

| 组合键 | 功能 | 触发条件 |
|---|---|---|
| `Alt + Q` | **截图识别并翻译** | 任何程序前台时都可用，自动切入选区界面 |
| `ESC`（选区界面中）| 取消截图 | 选区拖拽过程中按 |

> 启动后看**左下角状态栏**里的提示，例如："就绪 | 热键就绪: alt+q"。如果写的是"热键注册失败: xxx"，说明 pynput 被 UAC 拦截了，用管理员权限重新开一个 PowerShell 执行 `.\run.ps1` 即可。

### 自定义快捷键

编辑 `config.json`（首次运行会自动生成，或从代码默认值 `config.py` 改）里的 `screenshot_hotkey`，支持的修饰键：`ctrl`、`alt`、`shift`、`cmd`，字母键大小写均可：

```json
{
  "screenshot_hotkey": "ctrl+shift+f"
}
```

---

## 🖥️ 界面说明

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [截图识别翻译] [清空] [复制译文]  方向: [自动 ▼]  全局置顶 [✓]          │
├──────────────────────────────────────┬──────────────────────────────────┤
│ 原文                                  │ 译文                              │
│ ┌──────────────────────────────────┐ │ ┌──────────────────────────────┐ │
│ │ ... 截图识别出的原文 / 手动粘贴  │ │ │ ... 翻译后的结果（只读）      │ │
│ │ ... 可继续编辑，按"翻译当前"重试 │ │ │                              │ │
│ └──────────────────────────────────┘ │ └──────────────────────────────┘ │
└──────────────────────────────────────┴──────────────────────────────────┘
  就绪 | 热键就绪: alt+q | NPU device OK
```

- 点「截图识别翻译」或按 `Alt+Q`：主窗口自动隐藏 → 全屏选区 → 松开鼠标 → 主窗恢复并显示 OCR + 翻译
- 方向：`自动`= 中文字符多就翻英文；英文字符多就翻中文。也可强制选「译入中文」或「译入英文」
- 全局置顶：默认开启，即使切浏览器/文档窗口都不被挡住
- 点窗口右上角 `×`：最小化到托盘（**不会退出程序**），要退出请用托盘右键菜单的「退出」

---

## 🔌 100% 离线确认

本项目**不包含**、也**不会在运行时触发**任何网络请求：

| 模块 | 实现方式 | 联网？|
|---|---|---|
| OCR | RapidOCR PP-OCRv6，模型内嵌 wheel | ❌ |
| 翻译 | Qwen2.5-1.5B-Instruct OpenVINO，IR 模型**从本地绝对路径加载** | ❌ |
| 全局热键 | pynput 键盘 hook，用户态 | ❌ |
| 截图 | PySide6 QScreen grabWindow，纯内存操作 | ❌ |
| GUI / 托盘 / 字体 | PySide6 本地渲染 | ❌ |

唯一需要联网的就是**安装依赖**和**首次导出/下载模型**，之后把 `ocr-py` 整个目录（包括 `.venv` 和 `models/`）拷到没网的电脑，`.\run.ps1` 就能直接用。

---

## 🐛 常见问题

### Q1：启动后首屏翻译特别慢（10-20s），后面越来越快？

正常。首次推理时 OpenVINO 会为你的具体 NPU/GPU/CPU 型号**编译一次推理图**，并把 blob 缓存到 `models/translator/Qwen2.5-1.5B-Instruct-openvino/model_cache/`（2-3 个大文件，≈3.4 GB）。后续启动会直接读缓存，加载 <10 秒，推理单条 <2 秒。

如果你换了 CPU/GPU，删掉 `model_cache/` 让它重新编译即可。

### Q2：热键按了没反应？

1. 看状态栏提示"热键就绪"还是"热键注册失败"。若失败，**以管理员身份打开 PowerShell 后再 `.\run.ps1`**。
2. 检查是否和其它软件快捷键冲突（如微信/QQ/截图工具/浏览器常用快捷键）。在 `config.json` 改成其他组合如 `ctrl+shift+q` 重启即可。

### Q3：选了 NPU，但日志里回退到 GPU/CPU，怎么确认 NPU 可用？

运行：
```powershell
.\.venv\Scripts\python.exe check_env.py
```
会逐项检查：`Intel® NPU 插件`、OpenVINO device 列表、是否能用 NPU 跑一个最小 1×1 tensor。NPU 插件没装的话直接报缺失链接。

### Q4：窗口尺寸 / 透明度 / 热键 改了代码不生效？

历史版本的 `config.json` 会**锁住**这些值。删除 `config.json` 重开一次，或在里面直接改（推荐）。代码侧用 `CONFIG_VERSION` 机制会在升级时自动迁移"典型旧默认值"，但用户手动改过的值会保留。

### Q5：可以把 .venv / models/ 也 git push 吗？

**别 push**，仓库的 `.gitignore` 已经全局忽略：
```
.venv/             3-4 GB pip 环境
models/            1.6 GB 翻译模型 + 3.4 GB 编译缓存（4.8GB 总共）
__pycache__/*.pyc  字节码
*.log              运行日志
config.json        个性化设置
```
模型请通过 GitHub Release 分卷或 HuggingFace 分发，不要用 git 直接提交。

---

## 📁 目录结构

```
ocr-py/
├── .gitignore                   # Python 通用 + 项目专用忽略
├── README.md                    # 本文件
├── main.py                      # 入口：组装 GUI / 截图 / 流水线 / 热键
├── config.py                    # AppConfig + CONFIG_VERSION 迁移
├── check_env.py                 # 环境检测（依赖 / RapidOCR / OpenVINO NPU）
├── prepare_offline.py           # 模型导出脚本：HF Qwen2.5-1.5B → OpenVINO IR
├── requirements.txt             # pip 依赖清单
├── install.ps1 / run.ps1 / .bat # 一键安装 / 启动脚本（PowerShell 优先）
├── core/
│   ├── ocr.py                   # RapidOCR PP-OCRv6 封装
│   ├── translator.py            # Qwen2.5-1.5B + OpenVINO，NPU→GPU→CPU 回退
│   └── pipeline.py              # OCR→翻译 异步流水线（QThread + 信号槽）
├── ui/
│   ├── main_window.py           # 横向左右双栏主窗 + 状态栏 + 置顶/托盘
│   ├── screenshot.py            # 全屏选区覆盖层 + ESC 取消
│   └── tray.py                  # 系统托盘图标 + 菜单
└── utils/
    └── helpers.py               # 文本清洗 / 中英语种判断 / 内存回收
```

---

## 📝 Changelog

### v1.0.0

- 首次发布
- PySide6 主窗横向布局
- RapidOCR PP-OCRv6 中英文 OCR
- Qwen2.5-1.5B-Instruct OpenVINO NPU/GPU/CPU 自动回退 + 编译缓存
- Alt+Q 全局截图翻译热键
- 关闭按钮最小化到托盘
- 配置版本迁移，尺寸/热键/编译缓存默认值自动吃到新版本

---

## 📜 License

MIT。Qwen2.5 模型遵循 [Qwen License](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/main/LICENSE)，OpenVINO 遵循 Apache-2.0，RapidOCR 遵循 Apache-2.0。
