"""Langfuse / OpenTelemetry 초기화 헬퍼.

- 데모 3, 5: `get_langfuse_handler()` 를 config={"callbacks": [...]} 로 주입
- 데모 4  : `init_otel()` 로 OpenInference + OTLP 계측 (Langfuse SDK 미사용)
"""

from __future__ import annotations

import base64
import os
from typing import Optional


# ──────────────────────────────────────────────────────────────
# Langfuse (SDK v4 — CallbackHandler)
# ──────────────────────────────────────────────────────────────
def _sync_base_url_env() -> None:
    """LANGFUSE_HOST(구) ↔ LANGFUSE_BASE_URL(신) 별칭을 맞춰준다."""
    base = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or "http://localhost:3000"
    os.environ.setdefault("LANGFUSE_BASE_URL", base)
    os.environ.setdefault("LANGFUSE_HOST", base)


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def get_langfuse_handler():
    """LangChain/LangGraph 용 Langfuse CallbackHandler (v4: langfuse.langchain)."""
    _sync_base_url_env()
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def get_langfuse_client():
    """Langfuse 싱글턴 클라이언트 (datasets/prompts/scores API)."""
    _sync_base_url_env()
    from langfuse import get_client

    return get_client()


def trace_config(
    handler,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list] = None,
    extra_metadata: Optional[dict] = None,
) -> dict:
    """대시보드 필터링용 trace 속성이 담긴 invoke config 를 만든다.

    Langfuse v4 는 metadata 의 langfuse_* 키로 trace 속성을 받는다.
    """
    metadata = dict(extra_metadata or {})
    if session_id:
        metadata["langfuse_session_id"] = session_id
    if user_id:
        metadata["langfuse_user_id"] = user_id
    if tags:
        metadata["langfuse_tags"] = tags
    return {"callbacks": [handler], "metadata": metadata}


# ──────────────────────────────────────────────────────────────
# OpenTelemetry (데모 4 — 벤더 중립 계측)
# ──────────────────────────────────────────────────────────────
def _langfuse_otlp_endpoint_and_headers() -> tuple:
    """Langfuse 의 OTLP HTTP 엔드포인트와 Basic Auth 헤더.

    주의: Langfuse OTLP 는 HTTP(protobuf)만 지원한다 (gRPC 미지원).
    """
    _sync_base_url_env()
    base = os.environ["LANGFUSE_BASE_URL"].rstrip("/")
    token = base64.b64encode(
        f"{os.getenv('LANGFUSE_PUBLIC_KEY','')}:{os.getenv('LANGFUSE_SECRET_KEY','')}".encode()
    ).decode()
    return f"{base}/api/public/otel/v1/traces", {"Authorization": f"Basic {token}"}


def _phoenix_otlp_endpoint() -> str:
    return os.getenv("PHOENIX_OTLP_ENDPOINT", "http://localhost:6006/v1/traces")


def init_otel(targets: Optional[str] = None, service_name: str = "loop-engineering-demo"):
    """OpenInference LangChain 계측 + OTLP HTTP exporter 초기화.

    targets:
      - None: env OTEL_TARGETS 사용, 그것도 없으면 표준 env
        (OTEL_EXPORTER_OTLP_ENDPOINT / _HEADERS)를 그대로 따르는 exporter 1개
      - "langfuse,phoenix": 지정 백엔드로 fan-out (SpanProcessor 여러 개 등록)
      - "console": 디버그용 콘솔 출력
    반환: TracerProvider
    """
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider_ = TracerProvider(resource=Resource.create({"service.name": service_name}))

    targets = (targets if targets is not None else os.getenv("OTEL_TARGETS", "")).strip()
    names = [t.strip().lower() for t in targets.split(",") if t.strip()]

    if not names:
        # 표준 OTel env 만으로 결정 — "계측 코드는 백엔드를 모른다"의 기본형
        provider_.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        print(f"OTel exporter → {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', '(env 미설정)')}")
    else:
        for name in names:
            if name == "langfuse":
                ep, headers = _langfuse_otlp_endpoint_and_headers()
                provider_.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=ep, headers=headers)))
                print(f"OTel exporter → Langfuse {ep}")
            elif name == "phoenix":
                ep = _phoenix_otlp_endpoint()
                provider_.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=ep)))
                print(f"OTel exporter → Phoenix {ep}")
            elif name == "console":
                provider_.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
                print("OTel exporter → console (디버그)")
            else:
                raise ValueError(f"알 수 없는 OTEL_TARGETS 항목: {name}")

    from openinference.instrumentation.langchain import LangChainInstrumentor

    LangChainInstrumentor().instrument(tracer_provider=provider_)
    print("OpenInference LangChain 계측 활성화 — 코드 어디에도 벤더 SDK 없음")
    return provider_
