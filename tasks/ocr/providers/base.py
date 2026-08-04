from __future__ import annotations

from typing import Any, Protocol, TypedDict


class OcrPageResult(TypedDict):
    page_number: int
    image_path: str
    texts: list[str]
    scores: list[float]


class OcrProvider(Protocol):
    provider_code: str

    def recognize(
        self,
        image_info: dict[str, Any],
    ) -> list[OcrPageResult]:
        """
        문서를 OCR 처리하고
        공통 페이지 결과를 반환한다.
        """