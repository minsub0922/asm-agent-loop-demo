# 데모 4 — OpenTelemetry 백엔드 스왑

**한 줄 요약**: Langfuse SDK 없이 OpenInference + OTLP(HTTP)로 계측하고,
받는 백엔드(Langfuse ↔ Phoenix ↔ 동시 fan-out)는 env 로만 갈아끼운다.

## 실행 — 두 가지를 나란히 보여줄 것

```bash
# ① Langfuse 로 (엔드포인트: http://localhost:3000/api/public/otel + Basic Auth)
make demo4-langfuse

# ② Phoenix 로 (엔드포인트: http://localhost:6006/v1/traces)
make demo4-phoenix

# ③ 하이라이트: 두 백엔드 동시 fan-out
make demo4-both

# 오프라인 리허설(서버 불필요): 콘솔로 span 출력
OTEL_TARGETS=console make demo4
```

표준 env 방식(코드가 백엔드를 전혀 모르는 형태)도 지원한다:

```bash
OTEL_TARGETS= \
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:3000/api/public/otel" \
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic $(echo -n 'pk-lf-loop-demo-0000:sk-lf-loop-demo-0000' | base64),x-langfuse-ingestion-version=4" \
make demo4
```

## 발표 포인트 3개

1. **임포트 목록 셀** — `import langfuse` 가 없다. `common/tracing.py::init_otel()` 의
   TracerProvider + OTLPSpanExporter + `LangChainInstrumentor().instrument()` 세 줄이 전부.
2. **make demo4-both 후 두 대시보드 나란히** — 같은 실행이 Langfuse 와 Phoenix 에
   동시에 뜬다. "계측은 한 번, 백엔드는 자유"의 하이라이트 컷.
3. **주의사항 언급** — Langfuse OTLP 는 HTTP 전용(gRPC 미지원, 공식 문서 명시),
   세션/태그 같은 풍부한 속성은 SDK 방식(데모 3)이 편하다는 트레이드오프.

## 예상 소요: 10분

## 자주 나올 질문

- **Q. 데모 3(SDK) 방식과 뭘 쓰면 되나요?**
  A. Langfuse 를 깊게 쓸 거면 SDK(프롬프트 연동·세션·스코어 헬퍼가 풍부).
  백엔드 교체 가능성·폴리글랏 서비스·사내 컬렉터 경유가 요구사항이면 OTel 표준.
  둘은 배타적이지 않다 — Langfuse v4 SDK 자체가 OTel 위에 구현되어 있다.
- **Q. 노드 이름 말고 세션·사용자별 필터도 되나요?**
  A. OTel 경로에서는 `langfuse.trace.tags` 같은 span 속성 규약(공식 매핑 표)으로
  넣어야 한다. Baggage + BaggageSpanProcessor 로 전 span 에 전파하는 것이 권장 패턴.
