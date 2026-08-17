# 독립 색인 코드 
from __future__ import annotations

import argparse
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any, Iterator

from qdrant_client import QdrantClient
from qdrant_client import models

from tasks.common.constants import OCR_WORK_ROOT


DEFAULT_COLLECTION_NAME = "document_chunks"
DEFAULT_BATCH_SIZE = 64
DEFAULT_TIMEOUT_SECONDS = 30


def _resolve_work_path(
    path_value: str,
) -> Path:
    """
    OCR_WORK_ROOT 내부의 상대 경로와 절대 경로를 지원한다.
    OCR_WORK_ROOT 외부 경로 접근은 허용하지 않는다.
    """
    work_root = Path(
        OCR_WORK_ROOT
    ).resolve()

    requested_path = Path(
        path_value
    )

    if requested_path.is_absolute():
        resolved_path = requested_path.resolve()
    else:
        resolved_path = (
            work_root
            / requested_path
        ).resolve()

    if (
        resolved_path != work_root
        and work_root
        not in resolved_path.parents
    ):
        raise ValueError(
            "OCR_WORK_ROOT 외부 경로에는 "
            "접근할 수 없습니다: "
            f"{path_value}"
        )

    return resolved_path


def _create_client(
    qdrant_url: str,
) -> QdrantClient:
    api_key = os.getenv(
        "QDRANT_API_KEY"
    )

    return QdrantClient(
        url=qdrant_url,
        api_key=api_key or None,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )


def _document_filter(
    document_id: int,
) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(
                    value=document_id
                ),
            )
        ]
    )


def _build_point_id(
    collection_name: str,
    document_id: int,
    chunk_id: str,
) -> str:
    """
    같은 문서의 같은 Chunk는 항상 같은 UUID를 사용한다.
    """
    source = (
        f"qdrant://{collection_name}"
        f"/documents/{document_id}"
        f"/chunks/{chunk_id}"
    )

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            source,
        )
    )


def _load_manifest(
    manifest_path: str,
) -> tuple[dict[str, Any], Path]:
    manifest_file = _resolve_work_path(
        manifest_path
    )

    if not manifest_file.is_file():
        raise FileNotFoundError(
            "Embedding manifest를 찾을 수 없습니다: "
            f"{manifest_file}"
        )

    with manifest_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(
            file
        )

    if not isinstance(
        manifest,
        dict,
    ):
        raise ValueError(
            "manifest.json은 JSON 객체여야 합니다."
        )

    required_fields = [
        "document_id",
        "execution_id",
        "embedding_path",
        "model_name",
        "vector_count",
        "vector_size",
    ]

    missing_fields = [
        field
        for field in required_fields
        if manifest.get(field) is None
    ]

    if missing_fields:
        raise ValueError(
            "manifest.json 필수 값이 없습니다: "
            f"{missing_fields}"
        )

    return manifest, manifest_file


def _validate_embedding_file(
    embedding_file: Path,
    document_id: int,
    execution_id: int,
    model_name: str,
    vector_size: int,
    expected_count: int,
) -> int:
    """
    Qdrant 데이터를 삭제하기 전에 JSONL 전체를 검증한다.
    """
    record_count = 0
    chunk_ids: set[str] = set()

    with embedding_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                record = json.loads(
                    stripped_line
                )
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Embedding JSONL 파싱 실패: "
                    f"line={line_number}"
                ) from exc

            if not isinstance(
                record,
                dict,
            ):
                raise ValueError(
                    "Embedding record는 "
                    "JSON 객체여야 합니다: "
                    f"line={line_number}"
                )

            record_document_id = int(
                record.get(
                    "document_id",
                    -1,
                )
            )

            record_execution_id = int(
                record.get(
                    "execution_id",
                    -1,
                )
            )

            if (
                record_document_id
                != document_id
            ):
                raise ValueError(
                    "document_id가 일치하지 않습니다: "
                    f"line={line_number}"
                )

            if (
                record_execution_id
                != execution_id
            ):
                raise ValueError(
                    "execution_id가 일치하지 않습니다: "
                    f"line={line_number}"
                )

            if (
                record.get("model_name")
                != model_name
            ):
                raise ValueError(
                    "Embedding 모델명이 "
                    "일치하지 않습니다: "
                    f"line={line_number}"
                )

            chunk_id = record.get(
                "chunk_id"
            )

            if not isinstance(
                chunk_id,
                str,
            ) or not chunk_id.strip():
                raise ValueError(
                    "유효한 chunk_id가 없습니다: "
                    f"line={line_number}"
                )

            if chunk_id in chunk_ids:
                raise ValueError(
                    "중복 chunk_id가 있습니다: "
                    f"{chunk_id}"
                )

            chunk_ids.add(
                chunk_id
            )

            text = record.get(
                "text"
            )

            if not isinstance(
                text,
                str,
            ) or not text.strip():
                raise ValueError(
                    "유효한 text가 없습니다: "
                    f"chunk_id={chunk_id}"
                )

            vector = record.get(
                "vector"
            )

            if not isinstance(
                vector,
                list,
            ):
                raise ValueError(
                    "vector는 목록이어야 합니다: "
                    f"chunk_id={chunk_id}"
                )

            if len(vector) != vector_size:
                raise ValueError(
                    "Vector 차원이 일치하지 않습니다: "
                    f"chunk_id={chunk_id}, "
                    f"expected={vector_size}, "
                    f"actual={len(vector)}"
                )

            for value in vector:
                if (
                    not isinstance(
                        value,
                        (int, float),
                    )
                    or not math.isfinite(
                        float(value)
                    )
                ):
                    raise ValueError(
                        "Vector에 유효하지 않은 값이 있습니다: "
                        f"chunk_id={chunk_id}"
                    )

            record_count += 1

    if record_count != expected_count:
        raise ValueError(
            "manifest의 vector_count와 "
            "실제 JSONL record 수가 다릅니다: "
            f"expected={expected_count}, "
            f"actual={record_count}"
        )

    if record_count <= 0:
        raise ValueError(
            "색인할 Embedding record가 없습니다."
        )

    return record_count


def _iter_points(
    embedding_file: Path,
    collection_name: str,
    document_id: int,
) -> Iterator[models.PointStruct]:
    with embedding_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            stripped_line = line.strip()

            if not stripped_line:
                continue

            record = json.loads(
                stripped_line
            )

            chunk_id = str(
                record["chunk_id"]
            )

            point_id = _build_point_id(
                collection_name=collection_name,
                document_id=document_id,
                chunk_id=chunk_id,
            )

            payload = {
                "document_id": document_id,
                "execution_id": int(
                    record["execution_id"]
                ),
                "chunk_id": chunk_id,
                "chunk_index": record.get(
                    "chunk_index"
                ),
                "page_number": record.get(
                    "page_number"
                ),
                "page_chunk_index": record.get(
                    "page_chunk_index"
                ),
                "start_char": record.get(
                    "start_char"
                ),
                "end_char": record.get(
                    "end_char"
                ),
                "block_indexes": record.get(
                    "block_indexes",
                    [],
                ),
                "bbox_refs": record.get(
                    "bbox_refs",
                    [],
                ),
                "text": record["text"],
                "model_name": record[
                    "model_name"
                ],
                "vector_size": int(
                    record["vector_size"]
                ),
            }

            yield models.PointStruct(
                id=point_id,
                vector=[
                    float(value)
                    for value
                    in record["vector"]
                ],
                payload=payload,
            )


def _ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    model_name: str,
) -> None:
    exists = client.collection_exists(
        collection_name=collection_name
    )

    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

        print(
            "Qdrant collection 생성 완료: "
            f"{collection_name}",
            flush=True,
        )

        return

    collection_info = client.get_collection(
        collection_name=collection_name
    )

    vectors_config = (
        collection_info
        .config
        .params
        .vectors
    )

    if isinstance(
        vectors_config,
        dict,
    ):
        raise ValueError(
            "현재 코드는 named vector collection을 "
            "지원하지 않습니다."
        )

    existing_size = getattr(
        vectors_config,
        "size",
        None,
    )

    existing_distance = getattr(
        vectors_config,
        "distance",
        None,
    )

    if existing_size != vector_size:
        raise ValueError(
            "기존 Qdrant collection의 Vector 차원이 "
            "현재 모델과 다릅니다: "
            f"collection={existing_size}, "
            f"embedding={vector_size}"
        )

    if (
        existing_distance
        != models.Distance.COSINE
    ):
        raise ValueError(
            "기존 Qdrant collection의 "
            "거리 방식이 COSINE이 아닙니다: "
            f"{existing_distance}"
        )

    existing_points, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_payload=[
            "model_name"
        ],
        with_vectors=False,
    )

    if existing_points:
        existing_payload = (
            existing_points[0].payload
            or {}
        )

        existing_model_name = (
            existing_payload.get(
                "model_name"
            )
        )

        if (
            existing_model_name
            and existing_model_name
            != model_name
        ):
            raise ValueError(
                "기존 collection에 다른 Embedding "
                "모델 데이터가 있습니다: "
                f"existing={existing_model_name}, "
                f"current={model_name}"
            )

    print(
        "Qdrant collection 확인 완료: "
        f"{collection_name}",
        flush=True,
    )


def _upsert_in_batches(
    client: QdrantClient,
    collection_name: str,
    points: Iterator[models.PointStruct],
    batch_size: int,
) -> int:
    indexed_count = 0
    batch: list[
        models.PointStruct
    ] = []

    for point in points:
        batch.append(
            point
        )

        if len(batch) >= batch_size:
            client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True,
            )

            indexed_count += len(
                batch
            )

            print(
                "Qdrant upsert 진행: "
                f"{indexed_count}",
                flush=True,
            )

            batch = []

    if batch:
        client.upsert(
            collection_name=collection_name,
            points=batch,
            wait=True,
        )

        indexed_count += len(
            batch
        )

        print(
            "Qdrant upsert 진행: "
            f"{indexed_count}",
            flush=True,
        )

    return indexed_count


def index_embeddings(
    embedding_info: dict[str, Any],
    qdrant_url: str | None = None,
    collection_name: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError(
            "batch_size는 1 이상이어야 합니다."
        )

    manifest_path = embedding_info.get(
        "embedding_manifest_path"
    )

    if not manifest_path:
        raise ValueError(
            "embedding_manifest_path가 없습니다."
        )

    manifest, _ = _load_manifest(
        str(manifest_path)
    )

    document_id = int(
        embedding_info.get(
            "document_id",
            manifest["document_id"],
        )
    )

    execution_id = int(
        embedding_info.get(
            "execution_id",
            manifest["execution_id"],
        )
    )

    if (
        document_id
        != int(manifest["document_id"])
    ):
        raise ValueError(
            "요청 document_id와 manifest의 "
            "document_id가 일치하지 않습니다."
        )

    if (
        execution_id
        != int(manifest["execution_id"])
    ):
        raise ValueError(
            "요청 execution_id와 manifest의 "
            "execution_id가 일치하지 않습니다."
        )

    model_name = str(
        manifest["model_name"]
    )

    vector_size = int(
        manifest["vector_size"]
    )

    vector_count = int(
        manifest["vector_count"]
    )

    embedding_path = str(
        manifest["embedding_path"]
    )

    embedding_file = _resolve_work_path(
        embedding_path
    )

    if not embedding_file.is_file():
        raise FileNotFoundError(
            "embeddings.jsonl을 찾을 수 없습니다: "
            f"{embedding_file}"
        )

    selected_qdrant_url = (
        qdrant_url
        or os.getenv("QDRANT_URL")
    )

    selected_collection_name = (
        collection_name
        or os.getenv(
            "QDRANT_COLLECTION_NAME"
        )
        or DEFAULT_COLLECTION_NAME
    )

    if not selected_qdrant_url:
        raise RuntimeError(
            "QDRANT_URL 환경변수가 없습니다."
        )

    validated_count = (
        _validate_embedding_file(
            embedding_file=embedding_file,
            document_id=document_id,
            execution_id=execution_id,
            model_name=model_name,
            vector_size=vector_size,
            expected_count=vector_count,
        )
    )

    print(
        "==== QDRANT INDEX START ====",
        flush=True,
    )
    print(
        f"qdrant_url: "
        f"{selected_qdrant_url}",
        flush=True,
    )
    print(
        f"collection_name: "
        f"{selected_collection_name}",
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
        f"model_name: {model_name}",
        flush=True,
    )
    print(
        f"vector_size: {vector_size}",
        flush=True,
    )
    print(
        f"vector_count: {validated_count}",
        flush=True,
    )

    client = _create_client(
        selected_qdrant_url
    )

    _ensure_collection(
        client=client,
        collection_name=(
            selected_collection_name
        ),
        vector_size=vector_size,
        model_name=model_name,
    )

    document_filter = _document_filter(
        document_id
    )

    client.delete(
        collection_name=(
            selected_collection_name
        ),
        points_selector=models.FilterSelector(
            filter=document_filter
        ),
        wait=True,
    )

    print(
        "기존 문서 Point 제거 완료: "
        f"document_id={document_id}",
        flush=True,
    )

    indexed_count = _upsert_in_batches(
        client=client,
        collection_name=(
            selected_collection_name
        ),
        points=_iter_points(
            embedding_file=embedding_file,
            collection_name=(
                selected_collection_name
            ),
            document_id=document_id,
        ),
        batch_size=batch_size,
    )

    count_result = client.count(
        collection_name=(
            selected_collection_name
        ),
        count_filter=document_filter,
        exact=True,
    )

    stored_count = int(
        count_result.count
    )

    if stored_count != indexed_count:
        raise RuntimeError(
            "Qdrant 저장 건수가 일치하지 않습니다: "
            f"indexed={indexed_count}, "
            f"stored={stored_count}"
        )

    print(
        "==== QDRANT INDEX COMPLETED ====",
        flush=True,
    )
    print(
        f"indexed_count: "
        f"{indexed_count}",
        flush=True,
    )
    print(
        f"stored_count: "
        f"{stored_count}",
        flush=True,
    )

    return {
        "document_id": document_id,
        "execution_id": execution_id,
        "embedding_path": embedding_path,
        "embedding_manifest_path": str(
            manifest_path
        ),
        "qdrant_url": selected_qdrant_url,
        "collection_name": (
            selected_collection_name
        ),
        "model_name": model_name,
        "vector_size": vector_size,
        "indexed_count": indexed_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "embeddings.jsonl을 "
            "Qdrant collection에 색인합니다."
        )
    )

    parser.add_argument(
        "--manifest-path",
        required=True,
        help=(
            "OCR_WORK_ROOT 기준 "
            "embedding manifest 상대 경로"
        ),
    )

    parser.add_argument(
        "--qdrant-url",
    )

    parser.add_argument(
        "--collection-name",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    args = parser.parse_args()

    result = index_embeddings(
        {
            "embedding_manifest_path": (
                args.manifest_path
            ),
        },
        qdrant_url=args.qdrant_url,
        collection_name=(
            args.collection_name
        ),
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