# OpenTelemetry와 관측 백엔드 스왑

> 키워드: OpenTelemetry, OTel, OTLP, OpenInference, 익스포터, exporter, Phoenix, 벤더 중립, 백엔드 스왑, 계측

## 벤더 종속 없는 계측

특정 관측 도구의 SDK로 코드를 계측하면 도구를 바꿀 때 코드를 전부 걷어내야 한다.
OpenTelemetry(OTel)는 트레이스·메트릭의 **수집과 전송을 표준화**한 CNCF 프로젝트로,
계측은 한 번만 하고 데이터를 받을 백엔드는 설정으로 갈아끼우는 구조를 만든다.

## 핵심 구성요소

- **TracerProvider**: span을 만들고 수명주기를 관리하는 팩토리.
- **SpanProcessor / Exporter**: 만들어진 span을 배치로 모아 백엔드로 전송한다.
  processor를 여러 개 등록하면 **하나의 실행을 여러 백엔드로 동시에(fan-out)** 보낼 수 있다.
- **OTLP**: OTel 표준 전송 프로토콜. HTTP와 gRPC 두 가지가 있으며
  백엔드마다 지원 범위가 다르므로 확인이 필요하다(예: Langfuse는 HTTP만 지원).

## OpenInference

OTel의 시맨틱 컨벤션을 LLM 도메인으로 확장한 스펙이자 계측 라이브러리 모음이다.
`openinference-instrumentation-langchain`의 `LangChainInstrumentor`를 활성화하면
LangChain/LangGraph의 모든 실행이 자동으로 OTel span이 된다.
코드에는 특정 벤더 SDK가 전혀 등장하지 않는다.

## 백엔드 스왑

전송 대상은 환경변수로만 결정한다.

- `OTEL_EXPORTER_OTLP_ENDPOINT`: 수신 주소 (Langfuse의 OTLP 엔드포인트, Phoenix의 /v1/traces 등)
- `OTEL_EXPORTER_OTLP_HEADERS`: 인증 헤더 (Basic Auth 등)

같은 코드가 env 값만 바꾸면 Langfuse로도, Phoenix로도, 사내 컬렉터로도 트레이스를 보낸다.
Phoenix는 Arize가 만든 오픈소스 OTLP 백엔드로 도커 이미지 하나로 뜨기 때문에
로컬 실험용 수신처로 적합하다.
