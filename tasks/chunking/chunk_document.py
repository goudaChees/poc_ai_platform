from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tasks.common.constants import OCR_MEDIA_ROOT


DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120


def _resolve_media_path(path_value: str) -> Path:

    # 상대 경로와 절대 경로를 모두 지원하되,
    # OCR_MEDIA_ROOT 외부 경로 접근은 막는다.

    media_root = Path(OCR_MEDIA_ROOT).resolve()
    requested_path = Path(path_value)

    if requested_path.is_absolute():
        resolved_path = requested_path.resolve()
    else:
        resolved_path = (
            media_root
            / requested_path
        ).resolve()

    if (
        resolved_path != media_root
        and media_root not in resolved_path.parents
    ):
        raise ValueError(
            "MEDIA_ROOT 외부 경로에는 접근할 수 없습니다: "
            f"{path_value}"
        )

    return resolved_path


def _normalize_ocr_lines(
    texts: list[Any],
) -> str:

    # PaddleOCR의 rec_texts 목록을 페이지 단위 문자열로 정리한다.
    # 각 OCR 인식 줄은 개행으로 연결해서 원래 줄 구분을 최대한 유지한다.

    normalized_lines: list[str] = []

    for value in texts:
        if value is None:
            continue

        normalized_text = " ".join(
            str(value).split()
        )

        if normalized_text:
            normalized_lines.append(
                normalized_text
            )

    return "\n".join(
        normalized_lines
    )


def _find_chunk_end(
    text: str,
    start: int,
    preferred_end: int,
) -> int:

    # chunk_size 위치에서 무조건 자르지 않고,
    # 가까운 개행이나 공백 위치를 우선 사용한다.

    if preferred_end >= len(text):
        return len(text)

    search_start = max(
        start + 1,
        preferred_end - 150,
    )

    separators = (
        "\n",
        ". ",
        "? ",
        "! ",
        " ",
    )

    for separator in separators:
        separator_index = text.rfind(
            separator,
            search_start,
            preferred_end,
        )

        if separator_index >= 0:
            return (
                separator_index
                + len(separator)
            )

    return preferred_end


def _split_page_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError(
            "chunk_size는 1 이상이어야 합니다."
        )

    if chunk_overlap < 0:
        raise ValueError(
            "chunk_overlap은 0 이상이어야 합니다."
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap은 chunk_size보다 작아야 합니다."
        )

    chunks: list[dict[str, Any]] = []

    start = 0

    while start < len(text):
        preferred_end = min(
            start + chunk_size,
            len(text),
        )

        end = _find_chunk_end(
            text=text,
            start=start,
            preferred_end=preferred_end,
        )

        chunk_text = text[
            start:end
        ].strip()

        if chunk_text:
            chunks.append(
                {
                    "start_char": start,
                    "end_char": end,
                    "text": chunk_text,
                    "char_count": len(
                        chunk_text
                    ),
                }
            )

        if end >= len(text):
            break

        next_start = max(
            end - chunk_overlap,
            start + 1,
        )

        while (
            next_start < end
            and text[next_start].isspace()
        ):
            next_start += 1

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def chunk_document(
    ocr_info: dict[str, Any],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict[str, Any]:
    result_path = ocr_info.get(
        "result_path"
    )

    if not result_path:
        raise ValueError(
            "result_path가 없습니다."
        )

    result_file = _resolve_media_path(
        str(result_path)
    )

    if not result_file.is_file():
        raise FileNotFoundError(
            "OCR 결과 파일을 찾을 수 없습니다: "
            f"{result_file}"
        )

    with result_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        ocr_result = json.load(file)

    document_id = ocr_info.get(
        "document_id",
        ocr_result.get("document_id"),
    )

    execution_id = ocr_info.get(
        "execution_id",
        ocr_result.get("execution_id"),
    )

    if document_id is None:
        raise ValueError(
            "document_id를 찾을 수 없습니다."
        )

    if execution_id is None:
        raise ValueError(
            "execution_id를 찾을 수 없습니다."
        )

    document_id = int(document_id)
    execution_id = int(execution_id)

    result_document_id = ocr_result.get(
        "document_id"
    )

    result_execution_id = ocr_result.get(
        "execution_id"
    )

    if (
        result_document_id is not None
        and int(result_document_id) != document_id
    ):
        raise ValueError(
            "요청 document_id와 OCR 결과의 "
            "document_id가 일치하지 않습니다."
        )

    if (
        result_execution_id is not None
        and int(result_execution_id) != execution_id
    ):
        raise ValueError(
            "요청 execution_id와 OCR 결과의 "
            "execution_id가 일치하지 않습니다."
        )

    pages = ocr_result.get(
        "results",
        []
    )

    if not isinstance(pages, list):
        raise ValueError(
            "OCR 결과의 results는 목록이어야 합니다."
        )

    chunks: list[dict[str, Any]] = []
    global_chunk_index = 0

    for page_index, page in enumerate(
        pages,
        start=1,
    ):
        if not isinstance(page, dict):
            continue

        page_number = int(
            page.get(
                "page_number",
                page_index,
            )
        )

        texts = page.get(
            "texts",
            []
        )

        if isinstance(texts, str):
            texts = [texts]

        if not isinstance(texts, list):
            raise ValueError(
                "OCR 페이지의 texts는 목록이어야 합니다: "
                f"page_number={page_number}"
            )

        page_text = _normalize_ocr_lines(
            texts
        )

        if not page_text:
            print(
                "빈 OCR 페이지 건너뜀: "
                f"page_number={page_number}",
                flush=True,
            )
            continue

        page_chunks = _split_page_text(
            text=page_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for page_chunk_index, page_chunk in enumerate(
            page_chunks
        ):
            chunk_id = (
                f"{document_id}-"
                f"{global_chunk_index:06d}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": global_chunk_index,
                    "page_number": page_number,
                    "page_chunk_index": (
                        page_chunk_index
                    ),
                    "start_char": (
                        page_chunk["start_char"]
                    ),
                    "end_char": (
                        page_chunk["end_char"]
                    ),
                    "char_count": (
                        page_chunk["char_count"]
                    ),
                    "text": page_chunk["text"],
                }
            )

            global_chunk_index += 1

    if not chunks:
        raise ValueError(
            "생성된 Chunk가 없습니다. "
            "OCR 결과의 texts 내용을 확인하세요."
        )

    output_dir = (
        Path(OCR_MEDIA_ROOT)
        / "chunk_results"
        / str(document_id)
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "chunks.json"
    )

    output_relative_path = (
        Path("chunk_results")
        / str(document_id)
        / "chunks.json"
    ).as_posix()

    output_payload = {
        "document_id": document_id,
        "execution_id": execution_id,
        "source_result_path": str(
            result_path
        ),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }

    temporary_file = output_file.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output_payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_file.replace(
        output_file
    )

    print(
        "==== CHUNKING COMPLETED ====",
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
        f"chunk_count: {len(chunks)}",
        flush=True,
    )
    print(
        f"chunk_path: {output_relative_path}",
        flush=True,
    )

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "result_path": str(result_path),
        "chunk_path": output_relative_path,
        "chunk_count": len(chunks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "PaddleOCR result.json을 "
            "RAG 검색용 Chunk로 변환합니다."
        )
    )

    parser.add_argument(
        "--result-path",
        required=True,
        help=(
            "OCR_MEDIA_ROOT 기준 상대 경로 또는 "
            "MEDIA_ROOT 내부 절대 경로"
        ),
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
    )

    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
    )

    args = parser.parse_args()

    result = chunk_document(
        {
            "result_path": args.result_path,
        },
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()