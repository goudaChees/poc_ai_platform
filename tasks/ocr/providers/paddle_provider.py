from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import requests

from tasks.ocr.providers.base import (
    OcrPageResult,
)


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

        self.ocr_url = (
            os.getenv(
                "PADDLE_OCR_URL",
                "http://ocr-paddle:8000",
            )
            .rstrip("/")
        )

        self.timeout = int(
            os.getenv(
                "PADDLE_OCR_TIMEOUT",
                "120",
            )
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
                "PADDLE OCR HTTP START: "
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
                f"ocr_url: {self.ocr_url}",
                flush=True,
            )
            print(
                "================================",
                flush=True,
            )

            try:
                with open(
                    image_path,
                    "rb",
                ) as image_file:
                    response = requests.post(
                        f"{self.ocr_url}/ocr",
                        files={
                            "file": (
                                os.path.basename(
                                    image_path
                                ),
                                image_file,
                                "application/octet-stream",
                            )
                        },
                        data={
                            "lang": self.lang,
                        },
                        timeout=self.timeout,
                    )

            except requests.RequestException as error:
                raise RuntimeError(
                    "Paddle OCR 서비스 호출에 "
                    "실패했습니다: "
                    f"{error}"
                ) from error

            if not response.ok:
                raise RuntimeError(
                    "Paddle OCR 서비스가 "
                    "오류를 반환했습니다: "
                    f"status={response.status_code}, "
                    f"body={response.text}"
                )

            try:
                response_data = (
                    response.json()
                )

            except ValueError as error:
                raise RuntimeError(
                    "Paddle OCR 서비스 응답을 "
                    "JSON으로 해석할 수 없습니다."
                ) from error

            raw_texts = response_data.get(
                "texts",
                [],
            )

            if not isinstance(
                raw_texts,
                list,
            ):
                raise ValueError(
                    "Paddle OCR texts 응답이 "
                    "목록이 아닙니다."
                )

            texts = [
                str(text)
                for text in raw_texts
                if str(text).strip()
            ]

            raw_scores = response_data.get(
                "scores",
                [],
            )

            if not isinstance(
                raw_scores,
                list,
            ):
                raise ValueError(
                    "Paddle OCR scores 응답이 "
                    "목록이 아닙니다."
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
                    "Paddle OCR scores 응답을 "
                    "숫자 목록으로 변환할 수 없습니다."
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
                "PADDLE OCR HTTP END: "
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