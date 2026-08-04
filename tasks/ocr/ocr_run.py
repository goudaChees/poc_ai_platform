from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from tasks.ocr.ocr_dispatcher import create_ocr_provider
from tasks.ocr.ocr_result_writer import write_ocr_result

def run_ocr(
    image_info: dict[str, Any],
    provider_code: str = "PADDLE",
    provider_options: (
        Mapping[str, Any]
        | None
    ) = None,
) -> dict[str, Any]:
    required_fields = {
        "document_id",
        "execution_id",
    }

    missing_fields = sorted(
        required_fields
        - set(
            image_info.keys()
        )
    )

    if missing_fields:
        raise ValueError(
            "OCR 실행 필수 값이 없습니다: "
            + ", ".join(
                missing_fields
            )
        )

    document_id = int(
        image_info[
            "document_id"
        ]
    )

    execution_id = int(
        image_info[
            "execution_id"
        ]
    )

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

    selected_provider_options = dict(
        provider_options
        or {}
    )

    print(
        "==== OCR PROVIDER DISPATCH ====",
        flush=True,
    )
    print(
        f"document_id: {document_id}",
        flush=True,
    )
    print(
        f"execution_id: {execution_id}",
        flush=True,
    )
    print(
        "provider: "
        f"{normalized_provider_code}",
        flush=True,
    )
    print(
        "provider_options: "
        f"{selected_provider_options}",
        flush=True,
    )

    provider = create_ocr_provider(
        provider_code=(
            normalized_provider_code
        ),
        provider_options=(
            selected_provider_options
        ),
    )

    results = provider.recognize(
        image_info
    )

    return write_ocr_result(
        document_id=document_id,
        execution_id=execution_id,
        provider_code=(
            normalized_provider_code
        ),
        results=results,
    )