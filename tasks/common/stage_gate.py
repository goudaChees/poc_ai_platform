from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class StageGateError(ValueError):
    """Execution Plan의 Stage Gate 처리 오류."""


def is_stage_enabled(
    conf: Mapping[str, Any] | None,
    stage_code: str,
) -> bool:
    normalized_stage_code = (
        _normalize_stage_code(
            stage_code
        )
    )

    # 과거 수동 실행이나 기존 Kafka 메시지처럼
    # execution_plan이 없는 경우에는
    # 기존 전체 Pipeline을 그대로 실행한다.
    
    if not conf:
        _print_gate_result(
            normalized_stage_code,
            enabled=True,
            legacy=True,
        )

        return True

    execution_plan = conf.get(
        "execution_plan"
    )

    if execution_plan is None:
        _print_gate_result(
            normalized_stage_code,
            enabled=True,
            legacy=True,
        )

        return True

    if not isinstance(
        execution_plan,
        Mapping,
    ):
        raise StageGateError(
            "execution_plan은 객체 형식이어야 "
            "합니다."
        )

    resolved_stages = execution_plan.get(
        "resolved_stages"
    )

    if not isinstance(
        resolved_stages,
        list,
    ):
        raise StageGateError(
            "execution_plan.resolved_stages는 "
            "목록 형식이어야 합니다."
        )

    normalized_resolved_stages: set[str] = set()

    for resolved_stage in resolved_stages:
        normalized_resolved_stages.add(
            _normalize_stage_code(
                resolved_stage
            )
        )

    enabled = (
        normalized_stage_code
        in normalized_resolved_stages
    )

    _print_gate_result(
        normalized_stage_code,
        enabled=enabled,
        legacy=False,
    )

    return enabled


def pass_through_pipeline_info(
    pipeline_info: Any,
    *,
    task_name: str,
    stage_code: str,
) -> Any:
    print(
        "==== STAGE GATE NO-OP ====",
        flush=True,
    )
    print(
        f"task_name: {task_name}",
        flush=True,
    )
    print(
        f"stage_code: {stage_code}",
        flush=True,
    )
    print(
        "Service 호출 없이 입력값을 "
        "다음 Task로 전달합니다.",
        flush=True,
    )

    return pipeline_info


def _normalize_stage_code(
    stage_code: Any,
) -> str:
    if not isinstance(
        stage_code,
        str,
    ):
        raise StageGateError(
            "Stage code는 문자열이어야 합니다."
        )

    normalized_stage_code = (
        stage_code.strip().upper()
    )

    if not normalized_stage_code:
        raise StageGateError(
            "Stage code가 비어 있습니다."
        )

    return normalized_stage_code


def _print_gate_result(
    stage_code: str,
    *,
    enabled: bool,
    legacy: bool,
) -> None:
    action = (
        "RUN"
        if enabled
        else "NO-OP"
    )

    mode = (
        "LEGACY_FULL_PIPELINE"
        if legacy
        else "EXECUTION_PLAN"
    )

    print(
        "==== STAGE GATE ====",
        flush=True,
    )
    print(
        f"stage_code: {stage_code}",
        flush=True,
    )
    print(
        f"action: {action}",
        flush=True,
    )
    print(
        f"mode: {mode}",
        flush=True,
    )