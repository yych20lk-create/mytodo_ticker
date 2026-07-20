"""调用大模型 API 生成每日复盘 / 每日计划。"""
from __future__ import annotations

import logging
from typing import Literal, Optional

import requests

logger = logging.getLogger(__name__)

JobKind = Literal["review", "plan"]


class AIReviewService:
    """调用大模型 API。凭据取 active API profile；风格取 plan/review 各自配置。"""

    @classmethod
    def generate_summary(
        cls,
        prompt: str,
        *,
        kind: JobKind = "review",
    ) -> Optional[str]:
        from zentray.services.settings_manager import SettingsManager

        sm = SettingsManager()
        ai = sm.ai
        profile = ai.active_profile()
        if not profile or not profile.api_key:
            return None

        job = ai.plan if kind == "plan" else ai.review
        if not job.enabled:
            # 手动触发时仍允许调用（由上层决定）；此处仅无 key 时拒绝
            pass

        style = job.active_style()
        system_prompt = style.system_prompt
        if not system_prompt:
            system_prompt = (
                "你是一个效率教练。请根据用户待办情况输出 Markdown。"
            )

        headers = {
            "Authorization": f"Bearer {profile.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": profile.model or "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }

        try:
            base = (profile.base_url or "https://api.openai.com/v1").rstrip("/")
            url = f"{base}/chat/completions"
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("AI API Error (%s): %s", kind, e)
            return None
