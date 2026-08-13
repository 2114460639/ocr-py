# -*- coding: utf-8 -*-
"""环境自检：检查依赖安装情况、版本、OpenVINO NPU 可用性。"""
import importlib.util
import sys

# (模块名, 导入名, 用途)
DEPS = [
    ("PySide6", "PySide6", "GUI 框架"),
    ("rapidocr", "rapidocr", "OCR 推理（PP-OCRv6 内置）"),
    ("onnxruntime", "onnxruntime", "ONNX 运行时"),
    ("openvino", "openvino", "OpenVINO 推理（NPU 加速）"),
    ("optimum.intel", "optimum.intel", "HF→OpenVINO 模型加载"),
    ("transformers", "transformers", "Tokenizer/模型"),
    ("torch", "torch", "模型权重加载"),
    ("accelerate", "accelerate", "模型加载加速"),
    ("mss", "mss", "截图"),
    ("PIL", "PIL", "图像处理"),
    ("numpy", "numpy", "数值计算"),
]


def get_version(mod_name: str) -> str:
    try:
        mod = __import__(mod_name)
        for attr in ("__version__", "version", "VERSION"):
            v = getattr(mod, attr, None)
            if isinstance(v, str):
                return v
        return "?"
    except Exception as e:
        return f"ERR:{e}"


def main() -> int:
    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")
    print("-" * 60)
    missing = []
    for disp, imp, desc in DEPS:
        try:
            spec = importlib.util.find_spec(imp)
        except ModuleNotFoundError:
            spec = None
        if spec is None:
            print(f"[缺失] {disp:<26}  {desc}")
            missing.append(disp)
        else:
            ver = get_version(imp)
            print(f"[  OK] {disp:<26} {ver:<12} {desc}")
    print("-" * 60)

    # OpenVINO 可用设备检查
    if not importlib.util.find_spec("openvino"):
        print("OpenVINO 未安装，跳过设备检查")
    else:
        print("OpenVINO 推理设备:")
        try:
            # OpenVINO 新版(2024+)推荐 from openvino import Core
            try:
                from openvino import Core
            except ImportError:
                from openvino.runtime import Core
            core = Core()
            devices = core.available_devices
            for d in devices:
                print(f"  - {d}")
            if "NPU" in devices:
                print("  >>> NPU 可用，翻译模型可走 NPU 加速")
            else:
                print("  !!! 未检测到 NPU（需 Intel Core Ultra + 驱动 + OpenVINO>=2024.2）")
        except Exception as e:
            print(f"  设备查询失败: {e}")

    print("-" * 60)
    if missing:
        print(f"缺失 {len(missing)} 个依赖：{', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return 1
    print("所有依赖已安装")
    return 0


if __name__ == "__main__":
    sys.exit(main())
