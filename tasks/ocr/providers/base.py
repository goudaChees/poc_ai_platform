from __future__ import annotations

from typing import Any, Protocol, TypedDict

class OcrStandardImageInfo(TypedDict):
    width: int
    height: int

class OcrStandardBlock(TypedDict):
    index: int
    text: str
    confidence: float
    bbox: list[int]
    page: int

# 표준 공통 결과 
class OcrStandardResult(TypedDict):
    schema_version: str
    status: str
    engine_key: str
    version: str
    device: str
    image: OcrStandardImageInfo
    text: str
    blocks: list[
        OcrStandardBlock
    ]



# 기존 내부 OCR 결과 모델.
# 표준 OCR 모델 전환이 완료될 때까지 유지

class OcrPageResult(OcrStandardResult):
    page_number: int
    image_path: str



class OcrProvider(Protocol):
    def recognize(
        self,
        image_info: dict[str, Any,],
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