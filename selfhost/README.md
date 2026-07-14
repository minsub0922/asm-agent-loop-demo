# Self-host — Langfuse v3 + Phoenix 로컬 스택

**한 줄 요약**: 데모 3~5가 쓰는 관측 스택 전체를 도커 컴포즈 하나로 로컬에 띄운다.
데이터는 한 바이트도 외부로 나가지 않는다 — 이것이 셀프호스팅의 요점이다.

## 기동 / 종료

```bash
make up      # langfuse-web(3000), worker, postgres, clickhouse, redis, minio, phoenix(6006)
make down
```

첫 기동은 이미지 다운로드 때문에 수 분 걸린다 (D-1 리허설 때 미리 받아둘 것).

## 계정·프로젝트·키 — 자동 부트스트랩됨

이 compose 는 `LANGFUSE_INIT_*` 변수로 최초 기동 시 아래를 **자동 생성**한다.
`.env.example` 의 기본값과 일치하므로 `cp .env.example .env` 만 하면 바로 데모 3이 돈다.

| 항목 | 값 |
|---|---|
| 접속 | http://localhost:3000 |
| 로그인 | `demo@example.com` / `Demo1234!` |
| 프로젝트 | `loop-engineering-demo` |
| Public Key | `pk-lf-loop-demo-0000` |
| Secret Key | `sk-lf-loop-demo-0000` |
| Phoenix UI | http://localhost:6006 |

수동으로 만들고 싶다면(또는 INIT 변수를 지웠다면): ① http://localhost:3000 접속 →
Sign Up 으로 첫 계정 생성 ② New Organization → New Project 생성 ③ 프로젝트
Settings → API Keys 에서 키 발급 ④ `.env` 의 `LANGFUSE_PUBLIC_KEY` /
`LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL=http://localhost:3000` 반영.

## 상태 확인

```bash
curl -s localhost:3000/api/public/health   # {"status":"OK", ...} 이면 정상
curl -s -o /dev/null -w "%{http_code}\n" localhost:6006   # 200 이면 Phoenix 정상
```

## 사내망(폐쇄망) 적용 체크리스트

외부 통신이 차단된 환경에 이 스택을 옮길 때 확인할 것들:

- [ ] **텔레메트리 차단**: `TELEMETRY_ENABLED=false` (이 compose 는 이미 기본 false).
      Phoenix 도 익명 사용 통계를 보내지 않는지 버전별 문서 확인.
- [ ] **이미지 미러링**: `langfuse/langfuse:3`, `langfuse-worker:3`, `clickhouse-server`,
      `postgres:17`, `redis:7`, `cgr.dev/chainguard/minio`, `arizephoenix/phoenix` 를
      사내 프라이빗 레지스트리로 미러링하고 image 경로를 치환.
- [ ] **기본 비밀번호 전면 교체**: 이 파일의 `# CHANGEME` 주석 전부
      (SALT, ENCRYPTION_KEY 는 `openssl rand -hex 32`), `LANGFUSE_INIT_USER_PASSWORD` 포함.
      데모용 키(`pk-lf-loop-demo-0000`)는 절대 운영에 쓰지 말 것.
- [ ] **타임존 UTC 고정**: postgres 는 이미 `TZ=UTC`. 호스트/타 서비스도 UTC 로 맞춰야
      트레이스 타임스탬프가 어긋나지 않는다.
- [ ] **LLM 연동 포인트**: 폐쇄망에서는 OpenAI 대신 사내 Ollama/vLLM 을 쓴다.
      본 레포는 `.env` 의 `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL=http://사내호스트:11434`
      만 바꾸면 코드 수정 없이 동작한다 (OpenAI 호환 API 인 vLLM 은 `OPENAI_BASE_URL` 지정
      방식으로 langchain-openai 를 그대로 사용 가능).
- [ ] **포트 정책**: 외부 노출은 3000(web), 9090(minio 업로드), 6006(phoenix)만 —
      나머지는 127.0.0.1 바인딩(원본 compose 의 보안 권고 유지).
- [ ] **볼륨 백업**: postgres(메타데이터)·clickhouse(트레이스)·minio(이벤트 원본) 볼륨이
      실데이터다. 스냅숏 정책을 정할 것.

## 예상 소요: 5분 (데모 마무리 세그먼트에서 compose 파일 훑기 + 체크리스트 강조)

## 자주 나올 질문

- **Q. Langfuse Cloud 와 기능 차이는?**
  A. 트레이싱·프롬프트·데이터셋·실험 등 데모에서 쓴 핵심 기능은 OSS(MIT)에 포함.
  일부 엔터프라이즈 기능(SSO 강제, 감사 로그 등)은 라이선스 키가 필요하다.
- **Q. ClickHouse 까지 꼭 필요한가요?**
  A. v3 아키텍처의 필수 구성이다(트레이스 저장·집계). v2 는 Postgres 단독이었지만
  대량 트레이스에서 성능 한계로 v3 에서 분리됐다 — "관측 데이터는 OLAP 성격"이라는 점 자체가
  세션의 좋은 이야깃거리.
