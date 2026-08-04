from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from paddleocr import PaddleOCR

from tasks.ocr.providers.base import (
    OcrPageResult,
)


_PADDLE_ENGINES: dict[
    str,
    PaddleOCR,
] = {}


class PaddleOcrProvider:
    provider_code = "PADDLE"

    def __init__(
        self,
        options: Mapping[str, Any] | None = None,
    ) -> None:
        selected_options = dict(
            options
            or {}
        )

        unsupported_options = sorted(
            set(selected_options.keys())
            - {
                "lang",
            }
        )

        if unsupported_options:
            raise ValueError(
                "Paddle OCR Provider에서 "
                "지원하지 않는 옵션입니다: "
                + ", ".join(
                    unsupported_options
                )
            )

        self.lang = str(
            selected_options.get(
                "lang"
            )
            or "korean"
        ).strip()

        if not self.lang:
            raise ValueError(
                "Paddle OCR lang 옵션이 "
                "비어 있습니다."
            )

    def recognize(
        self,
        image_info: dict[str, Any],
    ) -> list[OcrPageResult]:
        image_files = image_info.get(
            "image_files"
        )

        if not isinstance(
            image_files,
            list,
        ) or not image_files:
            raise ValueError(
                "Paddle OCR을 실행할 "
                "이미지가 없습니다."
            )

        execution_id = image_info.get(
            "execution_id"
        )

        ocr_engine = _get_ocr_engine(
            lang=self.lang
        )

        results: list[
            OcrPageResult
        ] = []

        for page_number, raw_image_path in enumerate(
            image_files,
            start=1,
        ):
            image_path = str(
                raw_image_path
            )

            if not os.path.isfile(
                image_path
            ):
                raise FileNotFoundError(
                    "OCR 이미지 파일을 "
                    "찾을 수 없습니다: "
                    f"{image_path}"
                )

            print(
                "================================",
                flush=True,
            )
            print(
                "PADDLE OCR START: "
                f"{image_path}",
                flush=True,
            )
            print(
                f"page_number: {page_number}",
                flush=True,
            )
            print(
                f"execution_id: {execution_id}",
                flush=True,
            )
            print(
                "================================",
                flush=True,
            )

            prediction = ocr_engine.predict(
                image_path
            )

            if not prediction:
                raise RuntimeError(
                    "PaddleOCR 결과가 없습니다: "
                    f"{image_path}"
                )

            ocr_data = prediction[0]

            raw_texts = ocr_data.get(
                "rec_texts",
                [],
            )

            try:
                texts = [
                    str(text)
                    for text in list(
                        raw_texts
                    )
                    if str(text).strip()
                ]

            except TypeError as error:
                raise ValueError(
                    "PaddleOCR rec_texts 결과를 "
                    "목록으로 변환할 수 없습니다."
                ) from error

            raw_scores = ocr_data.get(
                "rec_scores",
                [],
            )

            try:
                scores = [
                    float(score)
                    for score in list(
                        raw_scores
                    )
                ]

            except (
                TypeError,
                ValueError,
            ) as error:
                raise ValueError(
                    "PaddleOCR rec_scores 결과를 "
                    "숫자 목록으로 변환할 수 "
                    "없습니다."
                ) from error

            results.append(
                {
                    "page_number": (
                        page_number
                    ),
                    "image_path": (
                        image_path
                    ),
                    "texts": texts,
                    "scores": scores,
                }
            )

            print(
                "==============================",
                flush=True,
            )
            print(
                "PADDLE OCR END: "
                f"{image_path}",
                flush=True,
            )
            print(
                f"text_count: {len(texts)}",
                flush=True,
            )
            print(
                "==============================",
                flush=True,
            )

        return results


def _get_ocr_engine(
    *,
    lang: str,
) -> PaddleOCR:
    existing_engine = (
        _PADDLE_ENGINES.get(
            lang
        )
    )

    if existing_engine is not None:
        return existing_engine

    print(
        "==== LOAD PADDLE OCR MODEL ====",
        flush=True,
    )
    print(
        f"lang: {lang}",
        flush=True,
    )

    created_engine = PaddleOCR(
        lang=lang
    )

    _PADDLE_ENGINES[lang] = (
        created_engine
    )

    print(
        "==== PADDLE OCR READY ====",
        flush=True,
    )

    return created_engine