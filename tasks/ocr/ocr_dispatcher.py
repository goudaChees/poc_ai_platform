from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tasks.ocr.providers.base import (
    OcrProvider,
)


HTTP_RUNTIME_PROVIDERS = {
    "PADDLE",
    "TESSERACT",
    "EASYOCR",
    # "UPSTAGE",
}


SUPPORTED_OCR_PROVIDERS = (
    HTTP_RUNTIME_PROVIDERS
)


HTTP_RUNTIME_OPTION_KEYS = {
    "base_url",
    "ocr_path",
    "file_field",
    "connect_timeout_seconds",
    "timeout_seconds",
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
        in HTTP_RUNTIME_PROVIDERS
    ):
        return (
            _create_http_runtime_provider(
                provider_code=(
                    normalized_provider_code
                ),
                options=(
                    selected_options
                ),
            )
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


def _create_http_runtime_provider(
    *,
    provider_code: str,
    options: Mapping[str, Any],
) -> OcrProvider:
    unsupported_options = sorted(
        set(
            options.keys()
        )
        - HTTP_RUNTIME_OPTION_KEYS
    )

    if unsupported_options:
        raise ValueError(
            "HTTP OCR Runtime에서 "
            "지원하지 않는 옵션입니다: "
            + ", ".join(
                unsupported_options
            )
        )

    base_url = (
        _require_string_option(
            options=options,
            key="base_url",
        )
    )

    ocr_path = (
        _read_string_option(
            options=options,
            key="ocr_path",
            default="/ocr",
        )
    )

    file_field = (
        _read_string_option(
            options=options,
            key="file_field",
            default="file",
        )
    )

    connect_timeout_seconds = (
        _read_positive_int_option(
            options=options,
            key=(
                "connect_timeout_seconds"
            ),
            default=10,
        )
    )

    timeout_seconds = (
        _read_positive_int_option(
            options=options,
            key="timeout_seconds",
            default=300,
        )
    )

    print(
        "==== HTTP OCR RUNTIME DISPATCH ====",
        flush=True,
    )

    print(
        "provider: "
        f"{provider_code}",
        flush=True,
    )

    print(
        "base_url: "
        f"{base_url}",
        flush=True,
    )

    from tasks.ocr.providers.http_runtime_adapter import (
        HttpOcrRuntimeAdapter,
    )

    return HttpOcrRuntimeAdapter(
        base_url=base_url,
        ocr_path=ocr_path,
        file_field=file_field,
        connect_timeout_seconds=(
            connect_timeout_seconds
        ),
        timeout_seconds=(
            timeout_seconds
        ),
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
        provider_code
        .strip()
        .upper()
    )

    if not normalized_provider_code:
        raise ValueError(
            "OCR Provider code가 "
            "비어 있습니다."
        )

    return normalized_provider_code


def _require_string_option(
    *,
    options: Mapping[str, Any],
    key: str,
) -> str:
    raw_value = options.get(
        key
    )

    if not isinstance(
        raw_value,
        str,
    ):
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션은 "
            "문자열이어야 합니다."
        )

    value = raw_value.strip()

    if not value:
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션이 "
            "비어 있습니다."
        )

    return value


def _read_string_option(
    *,
    options: Mapping[str, Any],
    key: str,
    default: str,
) -> str:
    raw_value = options.get(
        key,
        default,
    )

    if not isinstance(
        raw_value,
        str,
    ):
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션은 "
            "문자열이어야 합니다."
        )

    value = raw_value.strip()

    if not value:
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션이 "
            "비어 있습니다."
        )

    return value


def _read_positive_int_option(
    *,
    options: Mapping[str, Any],
    key: str,
    default: int,
) -> int:
    raw_value = options.get(
        key,
        default,
    )

    if isinstance(
        raw_value,
        bool,
    ):
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션은 "
            "1 이상의 정수여야 합니다."
        )

    try:
        value = int(
            raw_value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션은 "
            "1 이상의 정수여야 합니다."
        ) from error

    if value < 1:
        raise ValueError(
            "HTTP OCR Runtime "
            f"{key} 옵션은 "
            "1 이상이어야 합니다."
        )

    return value