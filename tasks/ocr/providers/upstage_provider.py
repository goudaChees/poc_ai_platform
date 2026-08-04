from __future__ import annotations

import json
import mimetypes
import os
from collections import defaultdict
from collections.abc import Mapping
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests

from tasks.ocr.providers.base import (
    OcrPageResult,
)


DEFAULT_UPSTAGE_API_URL = (
    "https://api.upstage.ai"
    "/v1/document-digitization"
)

DEFAULT_UPSTAGE_MODEL = (
    "document-parse"
)

DEFAULT_UPSTAGE_OCR_MODE = (
    "force"
)

DEFAULT_REQUEST_TIMEOUT_SECONDS = 300

DEFAULT_OUTPUT_FORMATS = (
    "text",
    "html",
)


class UpstageOcrProvider:
    provider_code = "UPSTAGE"

    def __init__(
        self,
        options: Mapping[str, Any] | None = None,
    ) -> None:
        selected_options = dict(
            options
            or {}
        )

        supported_options = {
            "model",
            "ocr",
            "output_formats",
            "coordinates",
            "chart_recognition",
            "base64_encoding",
        }

        unsupported_options = sorted(
            set(selected_options.keys())
            - supported_options
        )

        if unsupported_options:
            raise ValueError(
                "Upstage OCR Provider에서 "
                "지원하지 않는 옵션입니다: "
                + ", ".join(
                    unsupported_options
                )
            )

        self.api_key = str(
            os.getenv(
                "UPSTAGE_API_KEY"
            )
            or ""
        ).strip()

        if not self.api_key:
            raise RuntimeError(
                "UPSTAGE_API_KEY "
                "환경변수가 없습니다."
            )

        self.api_url = str(
            os.getenv(
                "UPSTAGE_DOCUMENT_PARSE_URL"
            )
            or DEFAULT_UPSTAGE_API_URL
        ).strip()

        if not self.api_url:
            raise RuntimeError(
                "UPSTAGE_DOCUMENT_PARSE_URL이 "
                "비어 있습니다."
            )

        self.model = _read_string_option(
            selected_options,
            key="model",
            default=(
                os.getenv(
                    "UPSTAGE_DOCUMENT_PARSE_MODEL"
                )
                or DEFAULT_UPSTAGE_MODEL
            ),
        )

        self.ocr_mode = (
            _read_string_option(
                selected_options,
                key="ocr",
                default=(
                    DEFAULT_UPSTAGE_OCR_MODE
                ),
            )
        )

        self.output_formats = (
            _read_string_list_option(
                selected_options,
                key="output_formats",
                default=(
                    DEFAULT_OUTPUT_FORMATS
                ),
            )
        )

        self.coordinates = (
            _read_bool_option(
                selected_options,
                key="coordinates",
                default=True,
            )
        )

        self.chart_recognition = (
            _read_bool_option(
                selected_options,
                key="chart_recognition",
                default=False,
            )
        )

        self.base64_encoding = (
            _read_string_list_option(
                selected_options,
                key="base64_encoding",
                default=(),
            )
        )

        self.timeout_seconds = (
            _read_timeout_seconds()
        )

    def recognize(
        self,
        image_info: dict[str, Any],
    ) -> list[OcrPageResult]:
        source_file_path = str(
            image_info.get(
                "source_file_path"
            )
            or ""
        ).strip()

        if not source_file_path:
            raise ValueError(
                "Upstage OCR 실행에 필요한 "
                "source_file_path가 없습니다."
            )

        source_file = Path(
            source_file_path
        )

        if not source_file.is_file():
            raise FileNotFoundError(
                "Upstage OCR 원본 파일을 "
                "찾을 수 없습니다: "
                f"{source_file}"
            )

        request_data = {
            "model": self.model,
            "ocr": self.ocr_mode,
            "coordinates": (
                self.coordinates
            ),
            "chart_recognition": (
                self.chart_recognition
            ),
            "output_formats": json.dumps(
                list(
                    self.output_formats
                ),
                ensure_ascii=False,
            ),
            "base64_encoding": json.dumps(
                list(
                    self.base64_encoding
                ),
                ensure_ascii=False,
            ),
        }

        mime_type = (
            mimetypes.guess_type(
                source_file.name
            )[0]
            or "application/octet-stream"
        )

        print(
            "==== UPSTAGE DOCUMENT "
            "PARSE START ====",
            flush=True,
        )
        print(
            "source_file_path: "
            f"{source_file}",
            flush=True,
        )
        print(
            f"model: {self.model}",
            flush=True,
        )
        print(
            f"ocr: {self.ocr_mode}",
            flush=True,
        )
        print(
            "output_formats: "
            f"{list(self.output_formats)}",
            flush=True,
        )
        print(
            "coordinates: "
            f"{self.coordinates}",
            flush=True,
        )
        print(
            "chart_recognition: "
            f"{self.chart_recognition}",
            flush=True,
        )

        try:
            with source_file.open(
                "rb"
            ) as file_object:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": (
                            "Bearer "
                            f"{self.api_key}"
                        )
                    },
                    files={
                        "document": (
                            source_file.name,
                            file_object,
                            mime_type,
                        )
                    },
                    data=request_data,
                    timeout=(
                        self.timeout_seconds
                    ),
                )

        except requests.RequestException as error:
            raise RuntimeError(
                "Upstage Document Parse "
                "API 호출에 실패했습니다: "
                f"{error}"
            ) from error

        if not response.ok:
            response_body = (
                response.text
                or ""
            )[:2000]

            raise RuntimeError(
                "Upstage Document Parse API가 "
                "오류를 반환했습니다: "
                f"status={response.status_code}, "
                f"body={response_body}"
            )

        try:
            response_payload = (
                response.json()
            )

        except ValueError as error:
            raise ValueError(
                "Upstage Document Parse "
                "API 응답이 JSON 형식이 "
                "아닙니다."
            ) from error

        if not isinstance(
            response_payload,
            dict,
        ):
            raise ValueError(
                "Upstage Document Parse "
                "API 응답은 JSON 객체여야 "
                "합니다."
            )

        results = (
            _normalize_upstage_response(
                response_payload=(
                    response_payload
                ),
                source_file_path=(
                    str(source_file)
                ),
            )
        )

        print(
            "==== UPSTAGE DOCUMENT "
            "PARSE SUCCESS ====",
            flush=True,
        )
        print(
            "status_code: "
            f"{response.status_code}",
            flush=True,
        )
        print(
            "request_id: "
            f"{response_payload.get('request_id')}",
            flush=True,
        )
        print(
            f"page_count: {len(results)}",
            flush=True,
        )
        print(
            "text_count: "
            f"{sum(len(page['texts']) for page in results)}",
            flush=True,
        )

        return results


def _normalize_upstage_response(
    *,
    response_payload: dict[str, Any],
    source_file_path: str,
) -> list[OcrPageResult]:
    element_results = (
        _normalize_elements(
            response_payload=(
                response_payload
            ),
            source_file_path=(
                source_file_path
            ),
        )
    )

    if element_results:
        return element_results

    content = response_payload.get(
        "content"
    )

    text = _extract_content_text(
        content
    )

    if not text:
        raise RuntimeError(
            "Upstage Document Parse "
            "응답에서 인식 텍스트를 "
            "찾지 못했습니다."
        )

    return [
        {
            "page_number": 1,
            "image_path": (
                source_file_path
            ),
            "texts": [
                text
            ],
            "scores": [],
        }
    ]


def _normalize_elements(
    *,
    response_payload: dict[str, Any],
    source_file_path: str,
) -> list[OcrPageResult]:
    elements = response_payload.get(
        "elements"
    )

    if not isinstance(
        elements,
        list,
    ) or not elements:
        return []

    page_texts: dict[
        int,
        list[str],
    ] = defaultdict(
        list
    )

    valid_elements = [
        element
        for element in elements
        if isinstance(
            element,
            dict,
        )
    ]

    sorted_elements = sorted(
        valid_elements,
        key=_element_sort_key,
    )

    for element in sorted_elements:
        text = _extract_content_text(
            element.get(
                "content"
            )
        )

        if not text:
            continue

        page_number = (
            _normalize_page_number(
                element.get(
                    "page"
                )
            )
        )

        page_texts[
            page_number
        ].append(
            text
        )

    results: list[
        OcrPageResult
    ] = []

    for page_number in sorted(
        page_texts.keys()
    ):
        texts = page_texts[
            page_number
        ]

        if not texts:
            continue

        results.append(
            {
                "page_number": (
                    page_number
                ),
                "image_path": (
                    source_file_path
                ),
                "texts": texts,
                "scores": [],
            }
        )

    return results


def _element_sort_key(
    element: dict[str, Any],
) -> tuple[int, int]:
    page_number = (
        _normalize_page_number(
            element.get(
                "page"
            )
        )
    )

    raw_element_id = element.get(
        "id"
    )

    try:
        element_id = int(
            raw_element_id
        )

    except (
        TypeError,
        ValueError,
    ):
        element_id = 0

    return (
        page_number,
        element_id,
    )


def _normalize_page_number(
    raw_page_number: Any,
) -> int:
    try:
        page_number = int(
            raw_page_number
        )

    except (
        TypeError,
        ValueError,
    ):
        return 1

    if page_number < 1:
        return 1

    return page_number


def _extract_content_text(
    raw_content: Any,
) -> str:
    if not isinstance(
        raw_content,
        Mapping,
    ):
        return ""

    for content_key in (
        "text",
        "markdown",
    ):
        raw_value = raw_content.get(
            content_key
        )

        if (
            isinstance(
                raw_value,
                str,
            )
            and raw_value.strip()
        ):
            return _normalize_text(
                raw_value
            )

    raw_html = raw_content.get(
        "html"
    )

    if (
        isinstance(
            raw_html,
            str,
        )
        and raw_html.strip()
    ):
        return _html_to_text(
            raw_html
        )

    return ""


def _normalize_text(
    text: str,
) -> str:
    normalized_text = (
        text.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )
    )

    normalized_lines = [
        line.strip()
        for line in normalized_text.split(
            "\n"
        )
    ]

    return "\n".join(
        line
        for line in normalized_lines
        if line
    )


def _html_to_text(
    html_value: str,
) -> str:
    parser = _HtmlTextExtractor()

    parser.feed(
        html_value
    )

    parser.close()

    return _normalize_text(
        unescape(
            parser.get_text()
        )
    )


class _HtmlTextExtractor(
    HTMLParser
):
    _BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "caption",
        "div",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }

    def __init__(
        self,
    ) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self._parts: list[
            str
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        del attrs

        if tag.lower() in (
            self._BLOCK_TAGS
        ):
            self._parts.append(
                "\n"
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() in (
            self._BLOCK_TAGS
        ):
            self._parts.append(
                "\n"
            )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if data:
            self._parts.append(
                data
            )

    def get_text(
        self,
    ) -> str:
        return "".join(
            self._parts
        )


def _read_string_option(
    options: Mapping[str, Any],
    *,
    key: str,
    default: str,
) -> str:
    raw_value = options.get(
        key,
        default,
    )

    value = str(
        raw_value
    ).strip()

    if not value:
        raise ValueError(
            f"Upstage {key} 옵션이 "
            "비어 있습니다."
        )

    return value


def _read_bool_option(
    options: Mapping[str, Any],
    *,
    key: str,
    default: bool,
) -> bool:
    raw_value = options.get(
        key,
        default,
    )

    if isinstance(
        raw_value,
        bool,
    ):
        return raw_value

    if isinstance(
        raw_value,
        str,
    ):
        normalized_value = (
            raw_value.strip().lower()
        )

        if normalized_value in {
            "true",
            "1",
            "yes",
            "y",
        }:
            return True

        if normalized_value in {
            "false",
            "0",
            "no",
            "n",
        }:
            return False

    raise ValueError(
        f"Upstage {key} 옵션은 "
        "boolean이어야 합니다."
    )


def _read_string_list_option(
    options: Mapping[str, Any],
    *,
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    raw_value = options.get(
        key,
        default,
    )

    if isinstance(
        raw_value,
        str,
    ):
        stripped_value = (
            raw_value.strip()
        )

        if not stripped_value:
            return ()

        try:
            decoded_value = (
                json.loads(
                    stripped_value
                )
            )

        except json.JSONDecodeError:
            decoded_value = [
                part.strip()
                for part in (
                    stripped_value.split(
                        ","
                    )
                )
                if part.strip()
            ]

        raw_value = decoded_value

    if not isinstance(
        raw_value,
        (
            list,
            tuple,
        ),
    ):
        raise ValueError(
            f"Upstage {key} 옵션은 "
            "문자열 목록이어야 합니다."
        )

    normalized_values: list[
        str
    ] = []

    for item in raw_value:
        normalized_item = str(
            item
        ).strip()

        if not normalized_item:
            continue

        normalized_values.append(
            normalized_item
        )

    return tuple(
        normalized_values
    )


def _read_timeout_seconds(
) -> int:
    raw_timeout = (
        os.getenv(
            "UPSTAGE_REQUEST_TIMEOUT_SECONDS"
        )
        or str(
            DEFAULT_REQUEST_TIMEOUT_SECONDS
        )
    )

    try:
        timeout_seconds = int(
            raw_timeout
        )

    except ValueError as error:
        raise ValueError(
            "UPSTAGE_REQUEST_TIMEOUT_SECONDS는 "
            "정수여야 합니다."
        ) from error

    if timeout_seconds < 1:
        raise ValueError(
            "UPSTAGE_REQUEST_TIMEOUT_SECONDS는 "
            "1 이상이어야 합니다."
        )

    return timeout_seconds