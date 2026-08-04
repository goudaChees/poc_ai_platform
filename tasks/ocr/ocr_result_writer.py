from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tasks.common.constants import (
    OCR_MEDIA_ROOT,
)
from tasks.ocr.providers.base import (
    OcrPageResult,
)


def write_ocr_result(
    *,
    document_id: int,
    execution_id: int,
    provider_code: str,
    results: list[OcrPageResult],
) -> dict[str, Any]:
    if document_id < 1:
        raise ValueError(
            "document_id는 "
            "1 이상이어야 합니다."
        )

    if execution_id < 1:
        raise ValueError(
            "execution_id는 "
            "1 이상이어야 합니다."
        )

    normalized_provider_code = (
        provider_code.strip().upper()
    )

    if not normalized_provider_code:
        raise ValueError(
            "OCR Provider code가 "
            "비어 있습니다."
        )

    if not isinstance(
        results,
        list,
    ) or not results:
        raise ValueError(
            "저장할 OCR 결과가 없습니다."
        )

    normalized_results = [
        _normalize_page_result(
            page_result
        )
        for page_result in results
    ]

    result_dir = (
        Path(
            OCR_MEDIA_ROOT
        )
        / "ocr_results"
        / str(
            document_id
        )
    )

    result_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_file = (
        result_dir
        / "result.json"
    )

    temporary_result_file = (
        result_dir
        / "result.json.tmp"
    )

    result_relative_path = (
        Path(
            "ocr_results"
        )
        / str(
            document_id
        )
        / "result.json"
    )

    result_payload = {
        "document_id": document_id,
        "execution_id": execution_id,
        "provider": (
            normalized_provider_code
        ),
        "results": (
            normalized_results
        ),
    }

    with temporary_result_file.open(
        "w",
        encoding="utf-8",
    ) as result_json_file:
        json.dump(
            result_payload,
            result_json_file,
            ensure_ascii=False,
            indent=2,
        )

        result_json_file.flush()

        os.fsync(
            result_json_file.fileno()
        )

    os.replace(
        temporary_result_file,
        result_file,
    )

    print(
        "==== OCR RESULT SAVED ====",
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
        f"result_file: {result_file}",
        flush=True,
    )
    print(
        "result_relative_path: "
        f"{result_relative_path.as_posix()}",
        flush=True,
    )

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "result_path": (
            result_relative_path.as_posix()
        ),
    }


def _normalize_page_result(
    page_result: OcrPageResult,
) -> dict[str, Any]:
    if not isinstance(
        page_result,
        dict,
    ):
        raise ValueError(
            "OCR 페이지 결과는 "
            "객체여야 합니다."
        )

    required_fields = {
        "page_number",
        "image_path",
        "texts",
        "scores",
    }

    missing_fields = sorted(
        required_fields
        - set(
            page_result.keys()
        )
    )

    if missing_fields:
        raise ValueError(
            "OCR 페이지 결과 필수 값이 "
            "없습니다: "
            + ", ".join(
                missing_fields
            )
        )

    page_number = int(
        page_result[
            "page_number"
        ]
    )

    if page_number < 1:
        raise ValueError(
            "OCR page_number는 "
            "1 이상이어야 합니다."
        )

    image_path = str(
        page_result[
            "image_path"
        ]
    ).strip()

    if not image_path:
        raise ValueError(
            "OCR image_path가 "
            "비어 있습니다."
        )

    raw_texts = page_result[
        "texts"
    ]

    if not isinstance(
        raw_texts,
        list,
    ):
        raise ValueError(
            "OCR texts는 "
            "목록이어야 합니다."
        )

    texts = [
        str(text)
        for text in raw_texts
        if str(text).strip()
    ]

    raw_scores = page_result[
        "scores"
    ]

    if not isinstance(
        raw_scores,
        list,
    ):
        raise ValueError(
            "OCR scores는 "
            "목록이어야 합니다."
        )

    try:
        scores = [
            float(score)
            for score in raw_scores
        ]

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "OCR scores에 숫자가 아닌 "
            "값이 있습니다."
        ) from error

    return {
        "page_number": page_number,
        "image_path": image_path,
        "texts": texts,
        "scores": scores,
    }