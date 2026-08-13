from __future__ import annotations

from typing import Any, Protocol, TypedDict

class AiOcrStandardImage(TypedDict):
    width: int
    height: int

class AiOcrStandardBlock(TypedDict):
    index: int
    text: str
    confidence: float
    bbox: list[int]
    page: int

class AiOcrStandardResult(TypedDict):
    schema_version: str
    status: str
    engine_key: str
    version: str
    device: str
    image: AiOcrStandardImage
    text: str
    blocks: list[
        AiOcrStandardBlock
    ]



# 기존 내부 OCR 결과 모델.
# 표준 OCR 모델 전환이 완료될 때까지 유지한다.

class OcrPageResult(TypedDict):
    page_number: int
    image_path: str
    texts: list[str]
    scores: list[float]


class OcrProvider(Protocol):
    provider_code: str

    def recognize(
        self,
        image_info: dict[
            str,
            Any,
        ],
    ) -> list[
        OcrPageResult
    ]:
        """
        문서를 OCR 처리하고
        공통 페이지 결과를 반환한다.
        """



# class OcrPageResult(TypedDict):
#     page_number: int
#     image_path: str
#     texts: list[str]
#     scores: list[float]


# class OcrProvider(Protocol):
#     provider_code: str

#     def recognize(
#         self,
#         image_info: dict[str, Any],
#     ) -> list[OcrPageResult]:
#         """
#         문서를 OCR 처리하고
#         공통 페이지 결과를 반환한다.
#         """