# 데모 5 — Deep Agents 리서치 에이전트

**한 줄 요약**: `create_deep_agent` 리서치 에이전트가 플래닝(TODO) → 서브에이전트 위임
(critique + **데모 1 Adaptive RAG 그래프**) → 웹 조사 → 파일 산출까지 완주한다.

## 실행

```bash
make lab        # demo5_deepagents/demo5.ipynb
make demo5      # 리허설(headless, mock)
```

- mock 모드: 메인 에이전트의 "판단"만 `ScriptedChatModel` 대본으로 재생 —
  도구 실행·서브에이전트(그래프)·파일 쓰기는 전부 실제 동작이다.
- 산출물: `outputs/deepagent_work/loop_engineering_brief_draft.md`(초안) → 비평 반영
  `loop_engineering_brief.md`(최종). 재실행 시 작업 폴더가 초기화된다(멱등).
- Langfuse 가 떠 있으면 자동으로 트레이싱이 붙는다 (Sessions=demo5).

## 서브에이전트로서의 LangGraph 그래프

deepagents 는 `CompiledSubAgent` = `{"name", "description", "runnable"}` 로
**컴파일된 그래프**를 서브에이전트로 공식 지원한다. 단 runnable 의 상태 스키마에
`messages` 키가 필요해서, 데모 1 그래프(`question/answer` 상태)를 6줄짜리 브리지
그래프로 감쌌다 (노트북 첫 코드 셀). 문서 근거: deepagents `CompiledSubAgent` docstring.

## 발표 포인트 3개

1. **브리지 셀** — "데모 1의 그래프가 부하 직원이 됐다". 자산 재사용: 그래프 → 서브에이전트.
2. **실행 트리 출력** — `task(rag-agent)` 다음 ToolMessage 로 코퍼스 근거 답변이
   **한 줄 요약으로만** 돌아온다: 컨텍스트 격리가 눈에 보이는 순간.
3. **초안 vs 최종 파일 diff** — critique-agent 비평(근거 인용·반례·다음 단계) 반영 전후를
   두 파일로 비교. "쓰기 도구는 덮어쓰지 않는다 → 개정 이력이 남는다"도 잔재미 포인트.

## 예상 소요: 15분

## 자주 나올 질문

- **Q. mock 대본이면 사기 아닌가요?**
  A. 대본은 LLM 의 '판단 순서'만 대신한다. 플래닝 상태 관리, task 라우팅, 그래프
  서브에이전트 실행, 파일 산출은 deepagents 실물 코드가 그대로 돈다. 실 모델로 바꾸면
  (`LLM_PROVIDER=openai`) 같은 코드에서 판단까지 실시간이 된다.
- **Q. 서브에이전트가 많아지면 비용/시간이 폭증하지 않나요?**
  A. 그래서 관측(데모 3~4)이 전제 조건이다. 트레이스 트리에서 어느 위임이 비싼지 보고
  서브에이전트 단위로 모델 등급을 낮추는 것(`model` 오버라이드)이 표준 최적화다.
