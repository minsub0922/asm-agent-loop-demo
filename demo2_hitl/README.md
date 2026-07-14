# 데모 2 — Human-in-the-Loop (interrupt / Command)

**한 줄 요약**: Adaptive RAG 그래프의 발행(publish) 직전에 `interrupt()`로 멈춰
사람의 승인/수정/거부를 받고 `Command(resume=...)`으로 재개한다.

## 실행

```bash
make lab                       # demo2_hitl/demo2.ipynb — 라이브에서는 input()으로 직접 개입
DEMO2_AUTO=all make demo2      # 리허설: approve/edit/reject 3경로 자동 실행
```

- `DEMO2_AUTO`: 빈 값(대화형) | `approve` | `edit` | `reject` | `all`(시나리오별 기본 액션)
- 발행 결과는 `outputs/published_answers.md` 에 append 된다 (위험 도구의 대역).

## 발표 포인트 3개

1. **`publish_answer` 노드 셀** — `interrupt(payload)` 는 노드 안의 함수 호출 한 줄.
   payload(질문/초안/선택지)가 그대로 호출자에게 노출된다. "UI가 아니라 원시 연산"임을 강조.
2. **승인 시나리오 실행 셀** — `publish_answer 진입` 로그가 **두 번** 찍힌다.
   재개 시 노드가 처음부터 재실행된다는 뜻이고, 그래서 파일 쓰기(발행)가 interrupt
   **뒤에** 있는 이유를 코드로 가리킬 것.
3. **그래프 조립 셀** — 데모 1 모듈의 노드를 그대로 임포트하고 `generate → publish_answer`
   엣지 하나만 바꿨다. `compile(checkpointer=MemorySaver())` 가 전제 조건임을 언급
   (thread_id = 승인 대기열의 키).

## 예상 소요: 15분 (시나리오당 3~4분)

## 자주 나올 질문

- **Q. 서버가 재시작되면 대기 중인 승인은 날아가나요?**
  A. MemorySaver 는 데모용 인메모리라 날아간다. 운영에서는 Postgres/SQLite 체크포인터로
  바꾸면 같은 thread_id 로 언제든 재개할 수 있다 (코드는 compile 인자 하나 차이).
- **Q. 승인을 Slack 버튼으로 받고 싶다면?**
  A. interrupt payload 를 Slack 메시지로 보내고, 버튼 콜백에서 `Command(resume=...)`을
  호출하는 어댑터만 붙이면 된다. 그래프 코드는 그대로다.
