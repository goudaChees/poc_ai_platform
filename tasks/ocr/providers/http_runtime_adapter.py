from __future__ import annotations

import mimetypes
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests

from tasks.ocr.providers.base import (
    OcrPageResult,
    OcrStandardBlock,
    OcrStandardImageInfo,
    OcrStandardResult,
)


class HttpOcrRuntimeAdapter:

    def __init__(
        self,
        *,
        base_url: str,
        ocr_path: str = "/ocr",
        file_field: str = "file",
        connect_timeout_seconds: int = 10,
        timeout_seconds: int = 300,
    ) -> None:
        self.base_url = (
            base_url
            .strip()
            .rstrip("/")
        )

        if not self.base_url:
            raise ValueError(
                "OCR Runtime base_url이 "
                "비어 있습니다."
            )

        normalized_ocr_path = (
            ocr_path.strip()
        )

        if not normalized_ocr_path:
            raise ValueError(
                "OCR Runtime ocr_path가 "
                "비어 있습니다."
            )

        if not normalized_ocr_path.startswith(
            "/"
        ):
            normalized_ocr_path = (
                "/"
                + normalized_ocr_path
            )

        self.ocr_path = (
            normalized_ocr_path
        )

        self.file_field = (
            file_field.strip()
        )

        if not self.file_field:
            raise ValueError(
                "OCR Runtime file_field가 "
                "비어 있습니다."
            )

        if connect_timeout_seconds < 1:
            raise ValueError(
                "connect_timeout_seconds는 "
                "1 이상이어야 합니다."
            )

        if timeout_seconds < 1:
            raise ValueError(
                "timeout_seconds는 "
                "1 이상이어야 합니다."
            )

        self.connect_timeout_seconds = (
            connect_timeout_seconds
        )

        self.timeout_seconds = (
            timeout_seconds
        )

    def recognize(
        self,
        image_info: dict[str, Any],
    ) -> list[OcrPageResult]:
        raw_image_files = image_info.get(
            "image_files"
        )

        if not isinstance(
            raw_image_files,
            list,
        ) or not raw_image_files:
            raise ValueError(
                "HTTP OCR Runtime 실행에 필요한 "
                "image_files가 없습니다."
            )

        results: list[
            OcrPageResult
        ] = []

        for (
            page_number,
            raw_image_path,
        ) in enumerate(
            raw_image_files,
            start=1,
        ):
            image_path = str(
                raw_image_path
            ).strip()

            if not image_path:
                raise ValueError(
                    "OCR 페이지 이미지 경로가 "
                    "비어 있습니다: "
                    f"page_number={page_number}"
                )

            standard_result = (
                self._recognize_image(
                    image_path=image_path,
                )
            )

            page_result = (
                _build_page_result(
                    standard_result=(
                        standard_result
                    ),
                    page_number=(
                        page_number
                    ),
                    image_path=(
                        image_path
                    ),
                )
            )

            results.append(
                page_result
            )

        return results
    

    def _recognize_image(
        self,
        *,
        image_path: str,
    ) -> OcrStandardResult:
        source_file = Path(
            image_path
        )

        if not source_file.is_file():
            raise FileNotFoundError(
                "OCR Runtime에 전달할 파일을 "
                "찾을 수 없습니다: "
                f"{source_file}"
            )

        mime_type = (
            mimetypes.guess_type(
                source_file.name
            )[0]
            or "application/octet-stream"
        )

        request_url = (
            self.base_url
            + self.ocr_path
        )

        print(
            "==== HTTP OCR RUNTIME START ====",
            flush=True,
        )

        print(
            f"request_url: {request_url}",
            flush=True,
        )

        print(
            f"source_file: {source_file}",
            flush=True,
        )

        try:
            with source_file.open(
                "rb"
            ) as file_object:
                response = requests.post(
                    request_url,
                    files={
                        self.file_field: (
                            source_file.name,
                            file_object,
                            mime_type,
                        )
                    },
                    timeout=(
                        self.connect_timeout_seconds,
                        self.timeout_seconds,
                    ),
                )

        except requests.RequestException as error:
            raise RuntimeError(
                "OCR Runtime 호출에 "
                "실패했습니다: "
                f"{error}"
            ) from error

        if not response.ok:
            response_body = (
                response.text
                or ""
            )[:2000]

            raise RuntimeError(
                "OCR Runtime이 오류를 "
                "반환했습니다: "
                f"status={response.status_code}, "
                f"body={response_body}"
            )

        try:
            response_payload = (
                response.json()
            )

        except ValueError as error:
            raise ValueError(
                "OCR Runtime 응답이 "
                "JSON 형식이 아닙니다."
            ) from error

        result = (
            _normalize_ocr_standard_result(
                response_payload
            )
        )

        print(
            "==== HTTP OCR RUNTIME SUCCESS ====",
            flush=True,
        )

        print(
            "engine_key: "
            f"{result['engine_key']}",
            flush=True,
        )

        print(
            "version: "
            f"{result['version']}",
            flush=True,
        )

        print(
            "device: "
            f"{result['device']}",
            flush=True,
        )

        print(
            "block_count: "
            f"{len(result['blocks'])}",
            flush=True,
        )

        return result
    


def _normalize_ocr_standard_result(
    response_payload: Any,
) -> OcrStandardResult:

    if not isinstance(
        response_payload,
        Mapping,
    ):
        raise ValueError(
            "ai_ocr_standard_v1 응답은 "
            "JSON 객체여야 합니다."
        )

    schema_version = str(
        response_payload.get(
            "schema_version"
        )
        or ""
    ).strip()

    if schema_version != "1.0":
        raise ValueError(
            "지원하지 않는 OCR schema_version입니다: "
            f"{schema_version}"
        )

    status = str(
        response_payload.get(
            "status"
        )
        or ""
    ).strip().upper()

    if status != "SUCCESS":
        raise RuntimeError(
            "OCR Runtime 처리 결과가 "
            "SUCCESS가 아닙니다: "
            f"{status}"
        )

    engine_key = _require_string(
        response_payload,
        "engine_key",
    )

    version = _require_string(
        response_payload,
        "version",
    )

    device = _require_string(
        response_payload,
        "device",
    )

    raw_image = response_payload.get(
        "image"
    )

    image = _normalize_image(
        raw_image
    )

    raw_text = response_payload.get(
        "text"
    )

    if not isinstance(
        raw_text,
        str,
    ):
        raise ValueError(
            "OCR text는 문자열이어야 합니다."
        )

    raw_blocks = response_payload.get(
        "blocks"
    )

    if not isinstance(
        raw_blocks,
        list,
    ):
        raise ValueError(
            "OCR blocks는 목록이어야 합니다."
        )

    blocks: list[
        OcrStandardBlock
    ] = []

    for raw_block in raw_blocks:
        blocks.append(
            _normalize_block(
                raw_block
            )
        )

    return {
        "schema_version": schema_version,
        "status": status,
        "engine_key": engine_key,
        "version": version,
        "device": device,
        "image": image,
        "text": raw_text,
        "blocks": blocks,
    }


def _normalize_image(
    raw_image: Any,
) -> OcrStandardImageInfo:

    if not isinstance(
        raw_image,
        Mapping,
    ):
        raise ValueError(
            "OCR image는 객체여야 합니다."
        )

    width = _require_positive_int(
        raw_image,
        "width",
    )

    height = _require_positive_int(
        raw_image,
        "height",
    )

    return {
        "width": width,
        "height": height,
    }


def _normalize_block(
    raw_block: Any,
) -> OcrStandardBlock:

    if not isinstance(
        raw_block,
        Mapping,
    ):
        raise ValueError(
            "OCR block은 객체여야 합니다."
        )

    index = _require_non_negative_int(
        raw_block,
        "index",
    )

    text = _require_string(
        raw_block,
        "text",
    )

    confidence = _require_confidence(
        raw_block.get(
            "confidence"
        )
    )

    raw_bbox = raw_block.get(
        "bbox"
    )

    if (
        not isinstance(
            raw_bbox,
            list,
        )
        or len(raw_bbox) != 4
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

    page = _require_positive_int(
        raw_block,
        "page",
    )

    return {
        "index": index,
        "text": text,
        "confidence": confidence,
        "bbox": bbox,
        "page": page,
    }


def _require_string(
    source: Mapping[str, Any],
    key: str,
) -> str:

    value = source.get(
        key
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ValueError(
            f"OCR {key}가 "
            "유효한 문자열이 아닙니다."
        )

    return value.strip()


def _require_positive_int(
    source: Mapping[str, Any],
    key: str,
) -> int:

    try:
        value = int(
            source.get(
                key
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"OCR {key}는 "
            "정수여야 합니다."
        ) from error

    if value < 1:
        raise ValueError(
            f"OCR {key}는 "
            "1 이상이어야 합니다."
        )

    return value


def _require_non_negative_int(
    source: Mapping[str, Any],
    key: str,
) -> int:

    try:
        value = int(
            source.get(
                key
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"OCR {key}는 "
            "정수여야 합니다."
        ) from error

    if value < 0:
        raise ValueError(
            f"OCR {key}는 "
            "0 이상이어야 합니다."
        )

    return value


def _require_confidence(
    raw_value: Any,
) -> float:

    try:
        confidence = float(
            raw_value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "OCR confidence는 "
            "숫자여야 합니다."
        ) from error

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "OCR confidence는 "
            "0 이상 1 이하여야 합니다."
        )

    return confidence

def _build_page_result(
    *,
    standard_result: OcrStandardResult,
    page_number: int,
    image_path: str,
) -> OcrPageResult:
    blocks: list[
        OcrStandardBlock
    ] = []

    for block in standard_result[
        "blocks"
    ]:
        blocks.append(
            {
                "index": block["index"],
                "text": block["text"],
                "confidence": (
                    block["confidence"]
                ),
                "bbox": block["bbox"],
                "page": page_number,
            }
        )

    return {
        "schema_version": (
            standard_result[
                "schema_version"
            ]
        ),
        "status": (
            standard_result["status"]
        ),
        "engine_key": (
            standard_result[
                "engine_key"
            ]
        ),
        "version": (
            standard_result["version"]
        ),
        "device": (
            standard_result["device"]
        ),
        "image": (
            standard_result["image"]
        ),
        "text": (
            standard_result["text"]
        ),
        "blocks": blocks,
        "page_number": page_number,
        "image_path": image_path,
    }