# LLM 관측성과 Langfuse

> 키워드: Langfuse, 트레이스, trace, span, generation, observation, 세션, 태그, 셀프호스팅, 관측성, CallbackHandler

## 왜 관측성이 필요한가

에이전트는 실행 경로가 매번 달라지는 비결정적 시스템이다.
"어느 노드에서 시간이 새는지", "어떤 질문에서 루프가 헛도는지", "비용이 어디서 발생하는지"는
로그 몇 줄로는 보이지 않는다. 관측성 없이 에이전트를 운영하는 것은 계기판 없이 비행하는 것과 같다.
런타임 루프를 개선하려면 먼저 **개발 루프의 눈** 역할을 할 트레이싱이 깔려 있어야 한다.

## 트레이스의 구조

- **Trace**: 요청 하나의 전체 실행 기록. 입력·출력·소요 시간·비용이 붙는다.
- **Span**: 트레이스 안의 작업 단위(그래프 노드, 검색, 도구 호출). 중첩 트리를 이룬다.
- **Generation**: LLM 호출 전용 span. 프롬프트, 응답, 모델명, 토큰 사용량이 기록된다.

에이전트 그래프 하나를 실행하면 "trace 아래에 노드 span들, 그 아래 generation들"의
트리가 만들어진다. 이 트리를 보면 실행 경로와 병목이 한눈에 드러난다.

## Langfuse와 LangChain 통합

Langfuse는 오픈소스 LLM 엔지니어링 플랫폼으로, 트레이싱·프롬프트 관리·평가·데이터셋을 제공한다.
LangChain/LangGraph와는 `CallbackHandler` 하나로 통합된다.
`config={"callbacks": [handler]}`를 invoke에 넘기면 모든 노드·LLM 호출이 자동 수집된다.
metadata에 `langfuse_session_id`, `langfuse_user_id`, `langfuse_tags`를 넣으면
대시보드에서 세션·사용자·태그 단위로 필터링할 수 있다.

## 셀프호스팅

Langfuse는 도커 컴포즈로 완전히 로컬에서 띄울 수 있다(v3 기준 web, worker,
Postgres, ClickHouse, Redis, MinIO 구성). 데이터가 외부로 나가지 않아
사내망·보안 환경에서도 도입할 수 있다는 점이 클라우드 전용 도구와의 큰 차이다.
