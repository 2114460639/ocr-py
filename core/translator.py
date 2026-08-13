# -*- coding: utf-8 -*-
"""翻译引擎封装：Qwen2.5-1.5B-Instruct + OpenVINO NPU 加速。

U7265 桌面版带 NPU（~13 TOPS），1.5B 模型 INT8 量化后可在 NPU 上跑，
推理约 15-30 tok/s，适合本地实时翻译。

使用 optimum-intel 的 OVModelForCausalLM 加载 OpenVINO IR 模型。
首次使用需把 HF 权重导出为 OpenVINO IR（见 README 步骤）。
"""
from __future__ import annotations

import threading
from typing import Optional

from config import TranslatorConfig, to_abs
from utils.helpers import translation_direction


# 翻译提示词模板：要求模型只输出译文，不带解释
_PROMPT_ZH2EN = (
    "You are a professional translator. Translate the following Chinese text "
    "to English. Output ONLY the translation, no explanations, keep the original "
    "line structure.\n\nChinese:\n{text}\n\nEnglish:"
)

_PROMPT_EN2ZH = (
    "你是一名专业翻译。将下面的英文翻译为中文。只输出译文，不要解释，"
    "保持原文换行结构。\n\n英文：\n{text}\n\n中文："
)


class TranslatorEngine:
    """Qwen2.5-1.5B 翻译引擎，OpenVINO NPU 加速，线程安全懒加载。"""

    _instance: Optional["TranslatorEngine"] = None
    _lock = threading.Lock()

    def __init__(self, cfg: TranslatorConfig):
        self._cfg = cfg
        self._model = None
        self._tokenizer = None

    @classmethod
    def instance(cls, cfg: TranslatorConfig) -> "TranslatorEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(cfg)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _resolve_device(self) -> str:
        """根据配置设备 + 实际可用设备，自动选择推理设备。

        优先级：配置的 NPU → 若不可用回退 GPU → 再回退 CPU。
        这样在带 NPU 的 265 上自动用 NPU，在开发机上自动用 GPU。
        """
        wanted = self._cfg.device.upper()
        try:
            try:
                from openvino import Core
            except ImportError:
                from openvino.runtime import Core
            available = [d.upper() for d in Core().available_devices]
        except Exception:
            available = ["CPU"]  # 查询失败，保守用 CPU

        if wanted in available:
            return wanted
        # 回退链：NPU → GPU → CPU
        for fallback in ("NPU", "GPU", "CPU"):
            if fallback in available:
                return fallback
        return "CPU"

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        model_dir = to_abs(self._cfg.model_dir)
        if not model_dir.exists():
            raise FileNotFoundError(
                f"翻译模型目录不存在: {model_dir}\n"
                "请先用 optimum-cli 将 Qwen2.5-1.5B-Instruct 导出为 OpenVINO IR。"
            )

        # 延迟导入，避免未安装依赖时整个程序无法启动
        from optimum.intel import OVModelForCausalLM
        from transformers import AutoTokenizer

        device = self._resolve_device()
        self._last_device = device  # 记录实际使用的设备，供上层展示

        # 模型编译缓存目录：放在模型目录下的 model_cache，后续启动跳过图编译
        cache_dir = (to_abs(self._cfg.model_dir) / "model_cache" / device).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)

        ov_config = {
            # 图编译缓存（device NPU/GPU/CPU 分开存放，避免冲突）
            "CACHE_DIR": str(cache_dir),
            # 减少首次推理的 warm-up 阶段性能波动
            "PERFORMANCE_HINT": "LATENCY",
        }
        # GPU 模式启用 FP16 推断，速度 ~2x
        if device == "GPU":
            ov_config["INFERENCE_PRECISION_HINT"] = "f16"

        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = OVModelForCausalLM.from_pretrained(
            str(model_dir),
            device=device,              # 自动选择 NPU/GPU/CPU
            compile=self._cfg.use_compile,
            ov_config=ov_config,
        )

    def translate(self, text: str, src: Optional[str] = None,
                  dst: Optional[str] = None) -> str:
        """翻译文本。src/dst 为空时自动判断方向。

        Args:
            text: 待翻译文本
            src: 源语言 'zh'/'en'，None 则自动判断
            dst: 目标语言，None 则自动判断
        Returns:
            译文字符串。
        """
        if not text or not text.strip():
            return ""
        if src is None or dst is None:
            src, dst = translation_direction(text)

        self._ensure_loaded()  # 先加载模型和 tokenizer，再构建 prompt
        prompt = self._build_prompt(text, src, dst)
        return self._generate(prompt)

    def _build_prompt(self, text: str, src: str, dst: str) -> str:
        """构建对话提示词。"""
        if src == "zh" and dst == "en":
            user = _PROMPT_ZH2EN.format(text=text)
        else:
            user = _PROMPT_EN2ZH.format(text=text)
        # Qwen chat 模板
        messages = [
            {"role": "system", "content": "You are a helpful translation assistant."},
            {"role": "user", "content": user},
        ]
        return self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    def _generate(self, prompt: str) -> str:
        """调用模型生成译文。"""
        self._ensure_loaded()
        inputs = self._tokenizer(prompt, return_tensors="pt")
        # OpenVINO 模型接受 numpy/list，去掉 pt 张量 device
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=self._cfg.max_new_tokens,
            temperature=self._cfg.temperature,
            do_sample=self._cfg.temperature > 0,
            repetition_penalty=1.05,
        )
        # 只取新生成的部分
        input_len = inputs["input_ids"].shape[-1]
        new_tokens = outputs[0][input_len:]
        result = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        return result.strip()
