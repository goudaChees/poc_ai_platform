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
        "schema_version",
        "status",
        "engine_key",
        "version",
        "device",
        "image",
        "text",
        "blocks",
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

    schema_version = str(
        page_result[
            "schema_version"
        ]
    ).strip()

    if schema_version != "1.0":
        raise ValueError(
            "지원하지 않는 OCR "
            "schema_version입니다: "
            f"{schema_version}"
        )

    status = str(
        page_result[
            "status"
        ]
    ).strip().upper()

    if status != "SUCCESS":
        raise ValueError(
            "OCR status가 "
            "SUCCESS가 아닙니다: "
            f"{status}"
        )

    engine_key = str(
        page_result[
            "engine_key"
        ]
    ).strip()

    if not engine_key:
        raise ValueError(
            "OCR engine_key가 "
            "비어 있습니다."
        )

    version = str(
        page_result[
            "version"
        ]
    ).strip()

    if not version:
        raise ValueError(
            "OCR version이 "
            "비어 있습니다."
        )

    device = str(
        page_result[
            "device"
        ]
    ).strip()

    if not device:
        raise ValueError(
            "OCR device가 "
            "비어 있습니다."
        )

    raw_image = page_result[
        "image"
    ]

    if not isinstance(
        raw_image,
        dict,
    ):
        raise ValueError(
            "OCR image는 "
            "객체여야 합니다."
        )

    try:
        width = int(
            raw_image[
                "width"
            ]
        )

        height = int(
            raw_image[
                "height"
            ]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "OCR image width/height가 "
            "올바르지 않습니다."
        ) from error

    if width < 1 or height < 1:
        raise ValueError(
            "OCR image width/height는 "
            "1 이상이어야 합니다."
        )

    raw_text = page_result[
        "text"
    ]

    if not isinstance(
        raw_text,
        str,
    ):
        raise ValueError(
            "OCR text는 "
            "문자열이어야 합니다."
        )

    raw_blocks = page_result[
        "blocks"
    ]

    if not isinstance(
        raw_blocks,
        list,
    ):
        raise ValueError(
            "OCR blocks는 "
            "목록이어야 합니다."
        )

    blocks: list[
        dict[str, Any]
    ] = []

    for raw_block in raw_blocks:
        if not isinstance(
            raw_block,
            dict,
        ):
            raise ValueError(
                "OCR block은 "
                "객체여야 합니다."
            )

        required_block_fields = {
            "index",
            "text",
            "confidence",
            "bbox",
            "page",
        }

        missing_block_fields = sorted(
            required_block_fields
            - set(
                raw_block.keys()
            )
        )

        if missing_block_fields:
            raise ValueError(
                "OCR block 필수 값이 "
                "없습니다: "
                + ", ".join(
                    missing_block_fields
                )
            )

        index = int(
            raw_block[
                "index"
            ]
        )

        if index < 0:
            raise ValueError(
                "OCR block index는 "
                "0 이상이어야 합니다."
            )

        block_text = str(
            raw_block[
                "text"
            ]
        ).strip()

        if not block_text:
            raise ValueError(
                "OCR block text가 "
                "비어 있습니다."
            )

        confidence = float(
            raw_block[
                "confidence"
            ]
        )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):
            raise ValueError(
                "OCR block confidence는 "
                "0 이상 1 이하여야 합니다."
            )

        raw_bbox = raw_block[
            "bbox"
        ]

        if (
            not isinstance(
                raw_bbox,
                list,
            )
            or len(
                raw_bbox
            ) != 4
        ):
            raise ValueError(
                "OCR block bbox는 "
                "4개 좌표 목록이어야 합니다."
            )

        try:
            bbox = [
                int(value)
                for value in raw_bbox
            ]

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "OCR block bbox 좌표는 "
                "정수여야 합니다."
            ) from error

        block_page = int(
            raw_block[
                "page"
            ]
        )

        if block_page < 1:
            raise ValueError(
                "OCR block page는 "
                "1 이상이어야 합니다."
            )
        
        # 페이지 provenance 규칙 확인용으로 넣어둠
        if block_page != page_number:
            raise ValueError(
                "OCR block page와 "
                "page_number가 다릅니다: "
                f"page_number={page_number}, "
                f"block_page={block_page}"
            )

        blocks.append(
            {
                "index": index,
                "text": block_text,
                "confidence": confidence,
                "bbox": bbox,
                "page": block_page,
            }
        )

    return {
        "page_number": page_number,
        "image_path": image_path,
        "schema_version": schema_version,
        "status": status,
        "engine_key": engine_key,
        "version": version,
        "device": device,
        "image": {
            "width": width,
            "height": height,
        },
        "text": raw_text,
        "blocks": blocks,
    }