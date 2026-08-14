from __future__ import annotations

import os
import argparse
import json
import math
from pathlib import Path
from typing import Any

from fastembed import TextEmbedding

from tasks.common.constants import OCR_MEDIA_ROOT


DEFAULT_BATCH_SIZE = 8

PREFERRED_MODEL_NAMES = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
    "BAAI/bge-m3",
)


def _resolve_media_path(
    path_value: str,
) -> Path:
    """
    OCR_MEDIA_ROOT 내부의 상대 경로와 절대 경로를 지원한다.
    MEDIA_ROOT 외부 경로 접근은 허용하지 않는다.
    """
    media_root = Path(
        OCR_MEDIA_ROOT
    ).resolve()

    requested_path = Path(
        path_value
    )

    if requested_path.is_absolute():
        resolved_path = (
            requested_path.resolve()
        )
    else:
        resolved_path = (
            media_root
            / requested_path
        ).resolve()

    if (
        resolved_path != media_root
        and media_root
        not in resolved_path.parents
    ):
        raise ValueError(
            "OCR_MEDIA_ROOT 외부 경로에는 "
            "접근할 수 없습니다: "
            f"{path_value}"
        )

    return resolved_path


def _get_supported_models() -> dict[str, dict[str, Any]]:
    supported_models: dict[
        str,
        dict[str, Any],
    ] = {}

    for model_info in (
        TextEmbedding.list_supported_models()
    ):
        model_name = model_info.get(
            "model"
        )

        if isinstance(
            model_name,
            str,
        ):
            supported_models[
                model_name
            ] = model_info

    return supported_models


def resolve_model_name(
    requested_model_name: str | None = None,
) -> str:
    supported_models = (
        _get_supported_models()
    )

    if requested_model_name:
        if (
            requested_model_name
            not in supported_models
        ):
            raise ValueError(
                "FastEmbed에서 지원하지 않는 "
                "모델입니다: "
                f"{requested_model_name}"
            )

        return requested_model_name

    for model_name in (
        PREFERRED_MODEL_NAMES
    ):
        if model_name in supported_models:
            return model_name

    multilingual_candidates = sorted(
        model_name
        for model_name
        in supported_models
        if (
            "multilingual"
            in model_name.lower()
            or "bge-m3"
            in model_name.lower()
        )
    )

    if multilingual_candidates:
        return multilingual_candidates[0]

    raise RuntimeError(
        "FastEmbed 지원 목록에서 "
        "다국어 임베딩 모델을 찾지 못했습니다."
    )


def _prepare_document_text(
    text: str,
    model_name: str,
) -> str:
    """
    E5 모델은 문서와 질문에 서로 다른 prefix를 붙이는
    방식을 사용하므로 문서 Chunk에는 passage prefix를 붙인다.
    """
    if "e5" in model_name.lower():
        return f"passage: {text}"

    return text


def _to_float_list(
    vector: Any,
) -> list[float]:
    if hasattr(
        vector,
        "tolist",
    ):
        vector_values = vector.tolist()
    else:
        vector_values = list(
            vector
        )

    float_values = [
        float(value)
        for value in vector_values
    ]

    if not float_values:
        raise ValueError(
            "비어 있는 Embedding Vector가 생성됐습니다."
        )

    if not all(
        math.isfinite(value)
        for value in float_values
    ):
        raise ValueError(
            "Embedding Vector에 "
            "유효하지 않은 숫자가 포함됐습니다."
        )

    return float_values


def embed_chunks(
    chunk_info: dict[str, Any],
    model_name: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError(
            "batch_size는 1 이상이어야 합니다."
        )

    chunk_path = chunk_info.get(
        "chunk_path"
    )

    if not chunk_path:
        raise ValueError(
            "chunk_path가 없습니다."
        )

    chunk_file = _resolve_media_path(
        str(chunk_path)
    )

    if not chunk_file.is_file():
        raise FileNotFoundError(
            "Chunk 결과 파일을 찾을 수 없습니다: "
            f"{chunk_file}"
        )

    with chunk_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        chunk_result = json.load(
            file
        )

    document_id = chunk_info.get(
        "document_id",
        chunk_result.get(
            "document_id"
        ),
    )

    execution_id = chunk_info.get(
        "execution_id",
        chunk_result.get(
            "execution_id"
        ),
    )

    if document_id is None:
        raise ValueError(
            "document_id를 찾을 수 없습니다."
        )

    if execution_id is None:
        raise ValueError(
            "execution_id를 찾을 수 없습니다."
        )

    document_id = int(
        document_id
    )

    execution_id = int(
        execution_id
    )

    result_document_id = (
        chunk_result.get(
            "document_id"
        )
    )

    result_execution_id = (
        chunk_result.get(
            "execution_id"
        )
    )

    if (
        result_document_id is not None
        and int(result_document_id)
        != document_id
    ):
        raise ValueError(
            "요청 document_id와 "
            "chunks.json의 document_id가 "
            "일치하지 않습니다."
        )

    if (
        result_execution_id is not None
        and int(result_execution_id)
        != execution_id
    ):
        raise ValueError(
            "요청 execution_id와 "
            "chunks.json의 execution_id가 "
            "일치하지 않습니다."
        )

    chunks = chunk_result.get(
        "chunks",
        []
    )

    if not isinstance(
        chunks,
        list,
    ):
        raise ValueError(
            "chunks는 목록이어야 합니다."
        )

    if not chunks:
        raise ValueError(
            "Embedding할 Chunk가 없습니다."
        )

    validated_chunks: list[
        dict[str, Any]
    ] = []

    input_texts: list[str] = []

    selected_model_name = (
        resolve_model_name(
            model_name
        )
    )

    for chunk_index, chunk in enumerate(
        chunks
    ):
        if not isinstance(
            chunk,
            dict,
        ):
            raise ValueError(
                "Chunk는 JSON 객체여야 합니다: "
                f"index={chunk_index}"
            )

        chunk_id = chunk.get(
            "chunk_id"
        )

        text = chunk.get(
            "text"
        )

        if not chunk_id:
            raise ValueError(
                "chunk_id가 없습니다: "
                f"index={chunk_index}"
            )

        if not isinstance(
            text,
            str,
        ):
            raise ValueError(
                "Chunk text는 문자열이어야 합니다: "
                f"chunk_id={chunk_id}"
            )

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError(
                "비어 있는 Chunk text입니다: "
                f"chunk_id={chunk_id}"
            )

        validated_chunks.append(
            chunk
        )

        input_texts.append(
            _prepare_document_text(
                text=normalized_text,
                model_name=(
                    selected_model_name
                ),
            )
        )

    print(
        "==== EMBEDDING MODEL LOAD ====",
        flush=True,
    )
    print(
        f"model_name: "
        f"{selected_model_name}",
        flush=True,
    )
    print(
        f"chunk_count: "
        f"{len(validated_chunks)}",
        flush=True,
    )
    print(
        f"batch_size: {batch_size}",
        flush=True,
    )

    embedding_model_cache_dir = os.getenv(
        "EMBEDDING_MODEL_CACHE_DIR",
        "/opt/airflow/embedding-models",
    )

    embedding_model = TextEmbedding(
        model_name=selected_model_name,
        cache_dir=embedding_model_cache_dir,
        local_files_only=True,
    )

    generated_vectors = list(
        embedding_model.embed(
            input_texts,
            batch_size=batch_size,
        )
    )

    if (
        len(generated_vectors)
        != len(validated_chunks)
    ):
        raise RuntimeError(
            "Chunk 수와 생성된 Vector 수가 "
            "일치하지 않습니다: "
            f"chunks={len(validated_chunks)}, "
            f"vectors={len(generated_vectors)}"
        )

    output_dir = (
        Path(OCR_MEDIA_ROOT)
        / "embedding_results"
        / str(document_id)
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    embedding_file = (
        output_dir
        / "embeddings.jsonl"
    )

    manifest_file = (
        output_dir
        / "manifest.json"
    )

    temporary_embedding_file = (
        embedding_file.with_suffix(
            ".jsonl.tmp"
        )
    )

    vector_size: int | None = None

    with temporary_embedding_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        for chunk, vector in zip(
            validated_chunks,
            generated_vectors,
        ):
            vector_values = (
                _to_float_list(
                    vector
                )
            )

            if vector_size is None:
                vector_size = len(
                    vector_values
                )
            elif (
                len(vector_values)
                != vector_size
            ):
                raise RuntimeError(
                    "Embedding Vector 차원이 "
                    "서로 일치하지 않습니다."
                )

            output_record = {
                "document_id": document_id,
                "execution_id": execution_id,
                "chunk_id": chunk[
                    "chunk_id"
                ],
                "chunk_index": chunk.get(
                    "chunk_index"
                ),
                "page_number": chunk.get(
                    "page_number"
                ),
                "page_chunk_index": (
                    chunk.get(
                        "page_chunk_index"
                    )
                ),
                "start_char": chunk.get(
                    "start_char"
                ),
                "end_char": chunk.get(
                    "end_char"
                ),
                "block_indexes": chunk.get(
                    "block_indexes",
                    [],
                ),
                "bbox_refs": chunk.get(
                    "bbox_refs",
                    [],
                ),
                "text": chunk["text"],
                "model_name": (
                    selected_model_name
                ),
                "vector_size": (
                    vector_size
                ),
                "vector": vector_values,
            }

            file.write(
                json.dumps(
                    output_record,
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                )
            )

            file.write("\n")

    temporary_embedding_file.replace(
        embedding_file
    )

    if vector_size is None:
        raise RuntimeError(
            "생성된 Vector가 없습니다."
        )

    embedding_relative_path = (
        Path("embedding_results")
        / str(document_id)
        / "embeddings.jsonl"
    ).as_posix()

    manifest_relative_path = (
        Path("embedding_results")
        / str(document_id)
        / "manifest.json"
    ).as_posix()

    manifest = {
        "document_id": document_id,
        "execution_id": execution_id,
        "source_chunk_path": str(
            chunk_path
        ),
        "embedding_path": (
            embedding_relative_path
        ),
        "model_name": (
            selected_model_name
        ),
        "vector_count": len(
            generated_vectors
        ),
        "vector_size": vector_size,
    }

    temporary_manifest_file = (
        manifest_file.with_suffix(
            ".json.tmp"
        )
    )

    with temporary_manifest_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_manifest_file.replace(
        manifest_file
    )

    print(
        "==== EMBEDDING COMPLETED ====",
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
        f"model_name: "
        f"{selected_model_name}",
        flush=True,
    )
    print(
        f"vector_count: "
        f"{len(generated_vectors)}",
        flush=True,
    )
    print(
        f"vector_size: {vector_size}",
        flush=True,
    )
    print(
        f"embedding_path: "
        f"{embedding_relative_path}",
        flush=True,
    )

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "chunk_path": str(
            chunk_path
        ),
        "embedding_path": (
            embedding_relative_path
        ),
        "embedding_manifest_path": (
            manifest_relative_path
        ),
        "model_name": (
            selected_model_name
        ),
        "vector_count": len(
            generated_vectors
        ),
        "vector_size": vector_size,
    }


def _print_supported_models() -> None:
    supported_models = (
        _get_supported_models()
    )

    for model_name in sorted(
        supported_models
    ):
        model_info = supported_models[
            model_name
        ]

        print(
            f"{model_name}"
            f"\tdim={model_info.get('dim')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "chunks.json의 텍스트를 "
            "FastEmbed Vector로 변환합니다."
        )
    )

    parser.add_argument(
        "--chunk-path",
        help=(
            "OCR_MEDIA_ROOT 기준 "
            "chunks.json 상대 경로"
        ),
    )

    parser.add_argument(
        "--model-name",
        help=(
            "FastEmbed 지원 모델 이름. "
            "생략하면 지원되는 다국어 모델을 "
            "자동 선택합니다."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help=(
            "FastEmbed 지원 모델 목록을 "
            "출력합니다."
        ),
    )

    args = parser.parse_args()

    if args.list_models:
        _print_supported_models()
        return

    if not args.chunk_path:
        parser.error(
            "--chunk-path가 필요합니다."
        )

    result = embed_chunks(
        {
            "chunk_path": (
                args.chunk_path
            ),
        },
        model_name=args.model_name,
        batch_size=args.batch_size,
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