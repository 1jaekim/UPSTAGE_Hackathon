# Timely의 SubagentStop 훅(http 타입)이 호출하는 로깅 엔드포인트.
# 별도 DB 새로 만들지 않고 기존 Chroma Cloud에 execution_logs 컬렉션을 하나 더 두고 쓴다.
# run_id로만 필터링해서 가져오면 되는 용도라 의미 검색이 필요 없음 -> 고정 더미 임베딩을 직접
# 넘겨서 chromadb의 기본 임베딩 함수(최초 호출 시 79MB 모델을 내려받음, 환경에 따라 매우 느림)를
# 아예 타지 않게 한다.
#
# 실행: uvicorn hooks_server:app --host 0.0.0.0 --port 8787
#
# Timely SubagentStop 이벤트 계약 (matcher 없음 - 모든 서브에이전트 종료 시 호출됨):
# {
#   "session_id": "...", "cwd": "...", "hook_event_name": "SubagentStop",
#   "transcript_path": null, "permission_mode": "default",
#   "last_assistant_message": "<서브에이전트 최종 응답 텍스트, 최대 2000자>"
# }
#
# 판정 결과가 구조화되어 오지 않고 last_assistant_message(자유 텍스트)로만 온다.
# 그래서 이 훅이 실제로 로그를 남기려면, Timely에서 safety-validator/correction-planner
# 서브에이전트의 "마지막 응답"을 반드시 아래 형태의 JSON 문자열 하나로만 끝내도록
# 프롬프트에 명시해야 한다 (2000자 제한 있으니 issues/changelog는 간결하게):
#   {"agent": "safety-validator", "attempt": 1, "event": "judge_result",
#    "payload": {"passed": false, "issues": [{"rule_id": "ROM-01", "detail": "..."}]}}
#   {"agent": "correction-planner", "attempt": 1, "event": "corrector_changelog",
#    "payload": {"before": "...", "after": "...", "reason": "..."}}
# 이 형태로 안 오는 서브에이전트(input-parser, exercise-retriever 등)는 조용히 무시한다.
# SubagentStop은 차단 불가 이벤트라 응답 JSON 내용은 Timely 쪽에서 의미 없음 - 2xx만 지키면 됨.
#
# POST /hooks/validation-log   — Timely가 SubagentStop마다 호출
# GET  /hooks/validation-log?run_id=<session_id>  — Reporter가 리포트 작성 직전 호출

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chroma_client import get_chroma_client
from harness_runner import run_harness_pipeline

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="SafeRx Harness — validation log hook + pipeline runner")

# 프론트엔드가 브라우저에서 이 서버로 직접 fetch하므로 CORS 허용 필요.
# 배포 시엔 allow_origins를 실제 프론트 도메인으로 좁히는 걸 권장.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_collection = None
_DUMMY_EMBEDDING = [0.0]
_LOGGED_EVENTS = {"judge_result", "corrector_changelog"}


@app.post("/run-harness")
def run_harness(payload: dict):
    return run_harness_pipeline(payload)


def get_log_collection():
    global _collection
    if _collection is None:
        _collection = get_chroma_client().get_or_create_collection("execution_logs")
    return _collection


class TimelyHookEvent(BaseModel):
    session_id: str
    cwd: str | None = None
    hook_event_name: str
    transcript_path: str | None = None
    permission_mode: str | None = None
    last_assistant_message: str = ""


def _try_parse_log_entry(message: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(message.strip())
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(parsed, dict):
        return None
    if parsed.get("event") not in _LOGGED_EVENTS:
        return None
    if "agent" not in parsed or "payload" not in parsed:
        return None
    return parsed


@app.post("/hooks/validation-log")
def write_log(event: TimelyHookEvent):
    entry = _try_parse_log_entry(event.last_assistant_message)
    if entry is None:
        # judge/corrector가 아닌 다른 서브에이전트(input-parser 등)의 종료 -> 로깅 대상 아님
        return {}

    run_id = event.session_id
    ts = datetime.now(timezone.utc).isoformat()
    entry_id = f"{run_id}-{uuid.uuid4()}"
    payload_json = json.dumps(entry["payload"], ensure_ascii=False)
    get_log_collection().add(
        ids=[entry_id],
        documents=[payload_json],
        embeddings=[_DUMMY_EMBEDDING],
        metadatas=[
            {
                "run_id": run_id,
                "agent": entry["agent"],
                "attempt": entry.get("attempt", 0),
                "event": entry["event"],
                "ts": ts,
                "payload_json": payload_json,
            }
        ],
    )
    return {"status": "ok", "id": entry_id}


@app.get("/hooks/validation-log")
def read_log(run_id: str):
    collection = get_log_collection()
    result = collection.get(where={"run_id": run_id}, include=["metadatas"])
    entries = [
        {
            "ts": meta["ts"],
            "agent": meta["agent"],
            "attempt": meta["attempt"],
            "event": meta["event"],
            "payload": json.loads(meta["payload_json"]),
        }
        for meta in result["metadatas"]
    ]
    entries.sort(key=lambda e: e["ts"])
    if not entries:
        raise HTTPException(status_code=404, detail=f"run_id '{run_id}'에 대한 로그가 없습니다.")
    return {"run_id": run_id, "entries": entries}
