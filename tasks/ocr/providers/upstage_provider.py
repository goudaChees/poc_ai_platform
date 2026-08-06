from __future__ import annotations

import json
import mimetypes
import os # api통신시 사용
import requests
from collections.abc import Mapping

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

DEFAULT_UPSTAGE_MODEL = "ocr"
DEFAULT_UPSTAGE_OCR_MODE = "REPLAY"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120


# api 통신시 비용처리가 되어 현재는 저장된 response.json 데이터를 넘겨 
# airflow dag를 선택적으로 처리하기 위한 코드
DEFAULT_UPSTAGE_REPLAY_RESPONSE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "upstage"
    / "sample_response.json"
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
            "replay_response_path", # test용 임시
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

        self.mode = _read_ocr_mode()

        self.model = _read_string_option(
            selected_options,
            key="model",
            default=(
                os.getenv(
                    "UPSTAGE_OCR_MODEL"
                )
                or os.getenv(
                    "UPSTAGE_DOCUMENT_PARSE_MODEL"
                )
                or DEFAULT_UPSTAGE_MODEL
            ),
        )

        replay_path_value = (
            selected_options.get(
                "replay_response_path"
            )
            or os.getenv(
                "UPSTAGE_REPLAY_RESPONSE_PATH"
            )
            or DEFAULT_UPSTAGE_REPLAY_RESPONSE_PATH
        )

        self.replay_response_path = Path(
            str(replay_path_value)
        )

        if not self.replay_response_path.is_absolute():
            self.replay_response_path = (
                Path.cwd()
                / self.replay_response_path
            ).resolve()

        self.api_key = ""
        self.api_url = DEFAULT_UPSTAGE_API_URL
        self.timeout_seconds = (
            DEFAULT_REQUEST_TIMEOUT_SECONDS
        )

        if self.mode == "LIVE":
            self.api_key = str(
                os.getenv(
                    "UPSTAGE_API_KEY"
                )
                or ""
            ).strip()

            if not self.api_key:
                raise RuntimeError(
                    "UPSTAGE_OCR_MODE가 LIVE이지만 "
                    "UPSTAGE_API_KEY 환경변수가 없습니다."
                )

            self.api_url = str(
                os.getenv(
                    "UPSTAGE_OCR_URL"
                )
                or os.getenv(
                    "UPSTAGE_DOCUMENT_PARSE_URL"
                )
                or DEFAULT_UPSTAGE_API_URL
            ).strip()

            if not self.api_url:
                raise RuntimeError(
                    "Upstage OCR API URL이 "
                    "비어 있습니다."
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

        print(
            "==== UPSTAGE OCR START ====",
            flush=True,
        )
        print(
            f"mode: {self.mode}",
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

        if self.mode == "LIVE":
            response_payload = (
                self._call_upstage_api(
                    source_file=source_file,
                )
            )

        else:
            print(
                "replay_response_path: "
                f"{self.replay_response_path}",
                flush=True,
            )

            response_payload = (
                _read_replay_response(
                    replay_response_path=(
                        self.replay_response_path
                    )
                )
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

        raw_response_path = (
            _write_raw_response(
                response_payload=(
                    response_payload
                ),
                image_info=image_info,
            )
        )

        print(
            "==== UPSTAGE OCR "
            f"{self.mode} SUCCESS ====",
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
        print(
            "raw_response_path: "
            f"{raw_response_path}",
            flush=True,
        )

        return results

    def _call_upstage_api(
            self,
            *,
            source_file: Path,
        ) -> dict[str, Any]:
            mime_type = (
                mimetypes.guess_type(
                    source_file.name
                )[0]
                or "application/octet-stream"
            )

            print(
                "==== UPSTAGE OCR LIVE REQUEST ====",
                flush=True,
            )
            print(
                f"api_url: {self.api_url}",
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
                        data={
                            "model": self.model,
                        },
                        timeout=(
                            self.timeout_seconds
                        ),
                    )

            except requests.RequestException as error:
                raise RuntimeError(
                    "Upstage OCR API 호출에 "
                    "실패했습니다: "
                    f"{error}"
                ) from error

            if not response.ok:
                response_body = (
                    response.text
                    or ""
                )[:2000]

                raise RuntimeError(
                    "Upstage OCR API가 "
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
                    "Upstage OCR API 응답이 "
                    "JSON 형식이 아닙니다."
                ) from error

            if not isinstance(
                response_payload,
                dict,
            ):
                raise ValueError(
                    "Upstage OCR API 응답은 "
                    "JSON 객체여야 합니다."
                )

            print(
                "status_code: "
                f"{response.status_code}",
                flush=True,
            )

            return response_payload


def _read_ocr_mode(
) -> str:
    mode = str(
        os.getenv(
            "UPSTAGE_OCR_MODE"
        )
        or DEFAULT_UPSTAGE_OCR_MODE
    ).strip().upper()

    if mode not in {
        "REPLAY",
        "LIVE",
    }:
        raise ValueError(
            "UPSTAGE_OCR_MODE는 "
            "REPLAY 또는 LIVE여야 합니다: "
            f"{mode}"
        )

    return mode

def _read_replay_response(
    *,
    replay_response_path: Path,
) -> dict[str, Any]:
    if not replay_response_path.is_file():
        raise FileNotFoundError(
            "Upstage replay 응답 파일을 "
            "찾을 수 없습니다: "
            f"{replay_response_path}"
        )

    try:
        with replay_response_path.open(
            "r",
            encoding="utf-8",
        ) as file_object:
            response_payload = json.load(
                file_object
            )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Upstage replay 응답 파일이 "
            "올바른 JSON 형식이 아닙니다: "
            f"{replay_response_path}"
        ) from error

    if not isinstance(
        response_payload,
        dict,
    ):
        raise ValueError(
            "Upstage replay 응답의 "
            "최상위 값은 JSON 객체여야 합니다."
        )

    return response_payload


def _normalize_upstage_response(
    *,
    response_payload: dict[str, Any],
    source_file_path: str,
) -> list[OcrPageResult]:
    raw_pages = response_payload.get(
        "pages"
    )

    if not isinstance(
        raw_pages,
        list,
    ) or not raw_pages:
        return _normalize_root_text(
            response_payload=(
                response_payload
            ),
            source_file_path=(
                source_file_path
            ),
        )

    results: list[
        OcrPageResult
    ] = []

    for (
        page_index,
        raw_page,
    ) in enumerate(
        raw_pages,
        start=1,
    ):
        if not isinstance(
            raw_page,
            Mapping,
        ):
            continue

        page_number = (
            _resolve_page_number(
                raw_page=raw_page,
                fallback_page_number=(
                    page_index
                ),
            )
        )

        texts, scores = (
            _extract_page_lines(
                raw_page
            )
        )

        if not texts:
            texts, scores = (
                _extract_page_words(
                    raw_page
                )
            )

        if not texts:
            page_text = _normalize_text(
                raw_page.get(
                    "text"
                )
            )

            if page_text:
                texts = _split_text_lines(
                    page_text
                )

                page_score = (
                    _normalize_confidence(
                        raw_page.get(
                            "confidence"
                        )
                    )
                )

                scores = [
                    page_score
                    for _ in texts
                ]

        if not texts:
            print(
                "빈 Upstage OCR 페이지를 "
                "건너뜁니다: "
                f"page_number={page_number}",
                flush=True,
            )
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
                "scores": scores,
            }
        )

    if not results:
        raise RuntimeError(
            "Upstage OCR 응답에서 "
            "인식 텍스트를 찾지 못했습니다."
        )

    return results


def _resolve_page_number(
    *,
    raw_page: Mapping[str, Any],
    fallback_page_number: int,
) -> int:
    raw_page_number = raw_page.get(
        "page"
    )

    if raw_page_number is not None:
        try:
            page_number = int(
                raw_page_number
            )

            if page_number >= 1:
                return page_number

        except (
            TypeError,
            ValueError,
        ):
            pass

    raw_page_id = raw_page.get(
        "id"
    )

    if raw_page_id is not None:
        try:
            page_id = int(
                raw_page_id
            )

            if page_id >= 0:
                return page_id + 1

        except (
            TypeError,
            ValueError,
        ):
            pass

    return fallback_page_number


def _extract_page_lines(
    raw_page: Mapping[str, Any],
) -> tuple[list[str], list[float]]:
    raw_lines = raw_page.get(
        "lines"
    )

    if not isinstance(
        raw_lines,
        list,
    ):
        return [], []

    valid_lines = [
        line
        for line in raw_lines
        if isinstance(
            line,
            Mapping,
        )
    ]

    sorted_lines = sorted(
        valid_lines,
        key=_ocr_item_sort_key,
    )

    texts: list[str] = []
    scores: list[float] = []

    page_confidence = raw_page.get(
        "confidence"
    )

    for line in sorted_lines:
        text = _normalize_text(
            line.get(
                "text"
            )
        )

        if not text:
            continue

        texts.append(
            text
        )

        scores.append(
            _normalize_confidence(
                line.get(
                    "confidence"
                ),
                fallback=(
                    page_confidence
                ),
            )
        )

    return texts, scores


def _extract_page_words(
    raw_page: Mapping[str, Any],
) -> tuple[list[str], list[float]]:
    raw_words = raw_page.get(
        "words"
    )

    if not isinstance(
        raw_words,
        list,
    ):
        return [], []

    valid_words = [
        word
        for word in raw_words
        if isinstance(
            word,
            Mapping,
        )
    ]

    sorted_words = sorted(
        valid_words,
        key=_ocr_item_sort_key,
    )

    texts: list[str] = []
    scores: list[float] = []

    page_confidence = raw_page.get(
        "confidence"
    )

    for word in sorted_words:
        text = _normalize_text(
            word.get(
                "text"
            )
        )

        if not text:
            continue

        texts.append(
            text
        )

        scores.append(
            _normalize_confidence(
                word.get(
                    "confidence"
                ),
                fallback=(
                    page_confidence
                ),
            )
        )

    return texts, scores


def _ocr_item_sort_key(
    item: Mapping[str, Any],
) -> int:
    try:
        return int(
            item.get(
                "id",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def _normalize_text(
    raw_text: Any,
) -> str:
    if not isinstance(
        raw_text,
        str,
    ):
        return ""

    normalized_lines = [
        " ".join(
            line.split()
        )
        for line in (
            raw_text
            .replace(
                "\r\n",
                "\n",
            )
            .replace(
                "\r",
                "\n",
            )
            .split(
                "\n"
            )
        )
    ]

    return "\n".join(
        line
        for line in normalized_lines
        if line
    )


def _split_text_lines(
    text: str,
) -> list[str]:
    return [
        line
        for line in text.split(
            "\n"
        )
        if line.strip()
    ]


def _normalize_confidence(
    raw_confidence: Any,
    *,
    fallback: Any = None,
) -> float:
    for value in (
        raw_confidence,
        fallback,
    ):
        try:
            if value is None:
                continue

            confidence = float(
                value
            )

            if confidence < 0:
                return 0.0

            if confidence > 1:
                return 1.0

            return confidence

        except (
            TypeError,
            ValueError,
        ):
            continue

    return 0.0


def _normalize_root_text(
    *,
    response_payload: Mapping[str, Any],
    source_file_path: str,
) -> list[OcrPageResult]:
    text = _normalize_text(
        response_payload.get(
            "text"
        )
    )

    if not text:
        raise RuntimeError(
            "Upstage OCR 응답에 "
            "pages와 text가 없습니다."
        )

    texts = _split_text_lines(
        text
    )

    score = _normalize_confidence(
        response_payload.get(
            "confidence"
        )
    )

    return [
        {
            "page_number": 1,
            "image_path": (
                source_file_path
            ),
            "texts": texts,
            "scores": [
                score
                for _ in texts
            ],
        }
    ]


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


def _read_timeout_seconds(
) -> int:
    raw_timeout = (
        os.getenv(
            "UPSTAGE_OCR_TIMEOUT"
        )
        or os.getenv(
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
            "UPSTAGE_OCR_TIMEOUT은 "
            "정수여야 합니다."
        ) from error

    if timeout_seconds < 1:
        raise ValueError(
            "UPSTAGE_OCR_TIMEOUT은 "
            "1 이상이어야 합니다."
        )

    return timeout_seconds


def _write_raw_response(
    *,
    response_payload: dict[str, Any],
    image_info: dict[str, Any],
) -> str:
    document_id = int(
        image_info["document_id"]
    )
    execution_id = int(
        image_info["execution_id"]
    )

    output_dir = (
        Path(
            os.environ["OCR_MEDIA_ROOT"]
        )
        / "ocr_results"
        / str(document_id)
        / str(execution_id)
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_response_file = (
        output_dir
        / "upstage_raw_response.json"
    )

    with raw_response_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            response_payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return str(
        raw_response_file
    )