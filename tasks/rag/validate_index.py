from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client import models

from tasks.common.constants import OCR_MEDIA_ROOT

DEFAULT_COLLECTION_NAME = "document_chunks"
DEFAULT_TIMEOUT_SECONDS = 30


def _resolve_media_path(
    path_value: str,
) -> Path:
    media_root = Path(
        OCR_MEDIA_ROOT
    ).resolve()

    requested_path = Path(
        path_value
    )

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
            "OCR_MEDIA_ROOT 외부 경로에는 "
            "접근할 수 없습니다: "
            f"{path_value}"
        )

    return resolved_path


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


def _create_client(
    qdrant_url: str,
) -> QdrantClient:
    return QdrantClient(
        url=qdrant_url,
        api_key=(
            os.getenv("QDRANT_API_KEY")
            or None
        ),
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )


def validate_rag_index(
    index_info: dict[str, Any],
    qdrant_url: str | None = None,
    collection_name: str | None = None,
) -> dict[str, Any]:
    required_fields = {
        "document_id",
        "execution_id",
        "model_name",
        "vector_size",
        "indexed_count",
    }

    missing_fields = sorted(
        required_fields
        - set(index_info.keys())
    )

    if missing_fields:
        raise ValueError(
            "RAG 검증 필수 값이 없습니다: "
            + ", ".join(missing_fields)
        )

    document_id = int(
        index_info["document_id"]
    )

    execution_id = int(
        index_info["execution_id"]
    )

    model_name = str(
        index_info["model_name"]
    )

    vector_size = int(
        index_info["vector_size"]
    )

    expected_count = int(
        index_info["indexed_count"]
    )

    if expected_count <= 0:
        raise ValueError(
            "검증할 Qdrant Point가 없습니다."
        )

    selected_qdrant_url = (
        qdrant_url
        or index_info.get("qdrant_url")
        or os.getenv("QDRANT_URL")
    )

    selected_collection_name = (
        collection_name
        or index_info.get("collection_name")
        or os.getenv(
            "QDRANT_COLLECTION_NAME"
        )
        or DEFAULT_COLLECTION_NAME
    )

    if not selected_qdrant_url:
        raise RuntimeError(
            "QDRANT_URL 환경변수가 없습니다."
        )

    client = _create_client(
        selected_qdrant_url
    )

    if not client.collection_exists(
        collection_name=(
            selected_collection_name
        )
    ):
        raise RuntimeError(
            "Qdrant collection을 "
            "찾을 수 없습니다: "
            f"{selected_collection_name}"
        )

    collection_info = client.get_collection(
        collection_name=(
            selected_collection_name
        )
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
            "현재 검증 코드는 named vector "
            "collection을 지원하지 않습니다."
        )

    collection_vector_size = getattr(
        vectors_config,
        "size",
        None,
    )

    if collection_vector_size != vector_size:
        raise ValueError(
            "Collection Vector 차원이 "
            "일치하지 않습니다: "
            f"expected={vector_size}, "
            f"actual={collection_vector_size}"
        )

    document_filter = _document_filter(
        document_id
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

    if stored_count != expected_count:
        raise RuntimeError(
            "Qdrant 문서별 Point 수가 "
            "일치하지 않습니다: "
            f"expected={expected_count}, "
            f"actual={stored_count}"
        )

    points, _ = client.scroll(
        collection_name=(
            selected_collection_name
        ),
        scroll_filter=document_filter,
        limit=1,
        with_payload=True,
        with_vectors=True,
    )

    if not points:
        raise RuntimeError(
            "검증할 Qdrant Point를 "
            "찾지 못했습니다."
        )

    sample_point = points[0]
    sample_payload = (
        sample_point.payload
        or {}
    )

    if int(
        sample_payload.get(
            "document_id",
            -1,
        )
    ) != document_id:
        raise ValueError(
            "Point payload의 document_id가 "
            "일치하지 않습니다."
        )

    if int(
        sample_payload.get(
            "execution_id",
            -1,
        )
    ) != execution_id:
        raise ValueError(
            "Point payload의 execution_id가 "
            "일치하지 않습니다."
        )

    if (
        sample_payload.get("model_name")
        != model_name
    ):
        raise ValueError(
            "Point payload의 model_name이 "
            "일치하지 않습니다."
        )

    sample_text = sample_payload.get(
        "text"
    )

    if not isinstance(
        sample_text,
        str,
    ) or not sample_text.strip():
        raise ValueError(
            "Point payload에 유효한 "
            "OCR text가 없습니다."
        )

    sample_vector = sample_point.vector

    if isinstance(
        sample_vector,
        dict,
    ):
        raise ValueError(
            "현재 검증 코드는 named vector를 "
            "지원하지 않습니다."
        )

    if not isinstance(
        sample_vector,
        list,
    ):
        raise ValueError(
            "검증용 Vector를 가져오지 "
            "못했습니다."
        )

    if len(sample_vector) != vector_size:
        raise ValueError(
            "검증용 Vector 차원이 "
            "일치하지 않습니다: "
            f"expected={vector_size}, "
            f"actual={len(sample_vector)}"
        )

    query_response = client.query_points(
        collection_name=(
            selected_collection_name
        ),
        query=sample_vector,
        query_filter=document_filter,
        limit=1,
        with_payload=True,
        with_vectors=False,
    )

    if not query_response.points:
        raise RuntimeError(
            "Qdrant Vector 검색 결과가 없습니다."
        )

    top_point = query_response.points[0]

    print(
        "==== RAG VALIDATION COMPLETED ====",
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
        f"collection_name: "
        f"{selected_collection_name}",
        flush=True,
    )
    print(
        f"expected_count: {expected_count}",
        flush=True,
    )
    print(
        f"stored_count: {stored_count}",
        flush=True,
    )
    print(
        f"sample_point_id: "
        f"{sample_point.id}",
        flush=True,
    )
    print(
        f"sample_score: "
        f"{float(top_point.score):.6f}",
        flush=True,
    )

    return {
        **index_info,
        "validation_status": "SUCCESS",
        "stored_count": stored_count,
        "sample_point_id": str(
            sample_point.id
        ),
        "sample_score": float(
            top_point.score
        ),
    }


def _load_manifest_index_info(
    manifest_path: str,
) -> dict[str, Any]:
    manifest_file = _resolve_media_path(
        manifest_path
    )

    if not manifest_file.is_file():
        raise FileNotFoundError(
            "Embedding manifest를 "
            "찾을 수 없습니다: "
            f"{manifest_file}"
        )

    with manifest_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(
            file
        )

    return {
        "document_id": int(
            manifest["document_id"]
        ),
        "execution_id": int(
            manifest["execution_id"]
        ),
        "model_name": str(
            manifest["model_name"]
        ),
        "vector_size": int(
            manifest["vector_size"]
        ),
        "indexed_count": int(
            manifest["vector_count"]
        ),
        "embedding_manifest_path": (
            manifest_path
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Qdrant 색인 결과와 "
            "Vector 검색을 검증합니다."
        )
    )

    parser.add_argument(
        "--manifest-path",
        required=True,
    )

    parser.add_argument(
        "--qdrant-url",
    )

    parser.add_argument(
        "--collection-name",
    )

    args = parser.parse_args()

    index_info = _load_manifest_index_info(
        args.manifest_path
    )

    result = validate_rag_index(
        index_info=index_info,
        qdrant_url=args.qdrant_url,
        collection_name=(
            args.collection_name
        ),
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