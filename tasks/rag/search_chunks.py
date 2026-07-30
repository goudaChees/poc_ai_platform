from __future__ import annotations

import argparse
import json
import os
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client import models


DEFAULT_COLLECTION_NAME = "document_chunks"
DEFAULT_TOP_K = 5


def _create_client() -> tuple[QdrantClient, str]:
    qdrant_url = os.getenv(
        "QDRANT_URL"
    )

    collection_name = os.getenv(
        "QDRANT_COLLECTION_NAME",
        DEFAULT_COLLECTION_NAME,
    )

    if not qdrant_url:
        raise RuntimeError(
            "QDRANT_URL 환경변수가 없습니다."
        )

    client = QdrantClient(
        url=qdrant_url,
        api_key=(
            os.getenv("QDRANT_API_KEY")
            or None
        ),
        timeout=30,
    )

    if not client.collection_exists(
        collection_name=collection_name
    ):
        raise RuntimeError(
            "Qdrant collection이 없습니다: "
            f"{collection_name}"
        )

    return client, collection_name


def _get_model_name(
    client: QdrantClient,
    collection_name: str,
) -> str:
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_payload=[
            "model_name",
        ],
        with_vectors=False,
    )

    if not points:
        raise RuntimeError(
            "Qdrant collection에 Point가 없습니다."
        )

    payload = points[0].payload or {}

    model_name = payload.get(
        "model_name"
    )

    if not isinstance(
        model_name,
        str,
    ) or not model_name.strip():
        raise RuntimeError(
            "Qdrant payload에서 "
            "model_name을 찾지 못했습니다."
        )

    return model_name


def _prepare_query(
    query: str,
    model_name: str,
) -> str:
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError(
            "검색 질문이 비어 있습니다."
        )

    if (
        "e5" in model_name.lower()
        and not normalized_query.lower().startswith(
            "query:"
        )
    ):
        return f"query: {normalized_query}"

    return normalized_query


def _create_query_filter(
    document_id: int | None,
) -> models.Filter | None:
    if document_id is None:
        return None

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


def search_chunks(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    document_id: int | None = None,
) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError(
            "top_k는 1 이상이어야 합니다."
        )

    client, collection_name = (
        _create_client()
    )

    model_name = _get_model_name(
        client=client,
        collection_name=collection_name,
    )

    prepared_query = _prepare_query(
        query=query,
        model_name=model_name,
    )

    print(
        "==== QUERY EMBEDDING ====",
        flush=True,
    )
    print(
        f"model_name={model_name}",
        flush=True,
    )
    print(
        f"query={query}",
        flush=True,
    )

    embedding_model = TextEmbedding(
        model_name
    )

    query_vector = next(
        embedding_model.query_embed(
            [prepared_query]
        )
    ).tolist()

    query_filter = _create_query_filter(
        document_id
    )

    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    results: list[dict[str, Any]] = []

    for point in response.points:
        payload = point.payload or {}

        results.append(
            {
                "score": float(
                    point.score
                ),
                "point_id": str(
                    point.id
                ),
                "document_id": payload.get(
                    "document_id"
                ),
                "execution_id": payload.get(
                    "execution_id"
                ),
                "chunk_id": payload.get(
                    "chunk_id"
                ),
                "chunk_index": payload.get(
                    "chunk_index"
                ),
                "page_number": payload.get(
                    "page_number"
                ),
                "text": payload.get(
                    "text",
                    "",
                ),
            }
        )

    return {
        "query": query,
        "collection_name": collection_name,
        "model_name": model_name,
        "document_id": document_id,
        "top_k": top_k,
        "result_count": len(results),
        "results": results,
    }


def _print_results(
    search_result: dict[str, Any],
) -> None:
    print()
    print(
        "==== SEARCH RESULTS ===="
    )
    print(
        "collection="
        f"{search_result['collection_name']}"
    )
    print(
        "model_name="
        f"{search_result['model_name']}"
    )
    print(
        "result_count="
        f"{search_result['result_count']}"
    )

    for index, result in enumerate(
        search_result["results"],
        start=1,
    ):
        print()
        print(
            f"[{index}] "
            f"score={result['score']:.6f}"
        )
        print(
            "document_id="
            f"{result['document_id']}"
        )
        print(
            "execution_id="
            f"{result['execution_id']}"
        )
        print(
            "chunk_id="
            f"{result['chunk_id']}"
        )
        print(
            "page_number="
            f"{result['page_number']}"
        )
        print(
            "text="
            f"{result['text']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "질문과 의미적으로 가까운 "
            "Qdrant Chunk를 검색합니다."
        )
    )

    parser.add_argument(
        "--query",
        required=True,
        help="검색할 질문",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    parser.add_argument(
        "--document-id",
        type=int,
        help=(
            "특정 문서 안에서만 검색할 때 사용"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON으로 출력",
    )

    args = parser.parse_args()

    result = search_chunks(
        query=args.query,
        top_k=args.top_k,
        document_id=args.document_id,
    )

    if args.json:
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    _print_results(
        result
    )


if __name__ == "__main__":
    main()