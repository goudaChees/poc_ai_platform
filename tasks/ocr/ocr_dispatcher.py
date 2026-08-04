from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tasks.ocr.providers.base import (
    OcrProvider,
)


SUPPORTED_OCR_PROVIDERS = {
    "PADDLE",
    "UPSTAGE",
}


def create_ocr_provider(
    *,
    provider_code: str,
    provider_options: (
        Mapping[str, Any]
        | None
    ) = None,
) -> OcrProvider:
    normalized_provider_code = (
        _normalize_provider_code(
            provider_code
        )
    )

    selected_options = dict(
        provider_options
        or {}
    )

    if (
        normalized_provider_code
        == "PADDLE"
    ):
        from tasks.ocr.providers.paddle_provider import (
            PaddleOcrProvider,
        )

        return PaddleOcrProvider(
            options=selected_options
        )

    if (
        normalized_provider_code
        == "UPSTAGE"
    ):
        from tasks.ocr.providers.upstage_provider import (
            UpstageOcrProvider,
        )

        return UpstageOcrProvider(
            options=selected_options
        )

    raise ValueError(
        "지원하지 않는 OCR Provider입니다: "
        f"{normalized_provider_code}. "
        "지원 Provider: "
        + ", ".join(
            sorted(
                SUPPORTED_OCR_PROVIDERS
            )
        )
    )


def _normalize_provider_code(
    provider_code: Any,
) -> str:
    if not isinstance(
        provider_code,
        str,
    ):
        raise ValueError(
            "OCR Provider code는 "
            "문자열이어야 합니다."
        )

    normalized_provider_code = (
        provider_code.strip().upper()
    )

    if not normalized_provider_code:
        raise ValueError(
            "OCR Provider code가 "
            "비어 있습니다."
        )

    return normalized_provider_code