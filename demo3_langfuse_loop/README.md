# 데모 3 — Langfuse 관측–개선 루프

**한 줄 요약**: 트레이싱 → 실패 수집(👎 score) → 데이터셋 승격 → 프롬프트 v1/v2 →
실험 + LLM-as-a-Judge, 개발 루프 한 바퀴를 로컬 Langfuse 위에서 완주한다.

## 실행

```bash
make up                        # 로컬 Langfuse (키/계정 자동 부트스트랩)
cp .env.example .env           # 부트스트랩 키가 이미 들어 있음
make lab                       # demo3_langfuse_loop/demo3.ipynb
# 리허설(headless): make demo3   (= make seed)
```

- 전제가 안 갖춰지면 첫 셀이 즉시 명확한 메시지로 중단한다 (조용한 실패 없음).
- mock 모드에서도 전 과정이 돌며, v2 > v1 점수 차이가 결정적으로 재현된다.

## 발표 포인트 3개

1. **① 트레이싱 셀** — 그래프 코드는 데모 1 그대로, 바뀐 건 `config` 한 줄.
   출력된 트레이스 URL을 열어 노드 span 트리를 보여줄 것 (route→retrieve→grade→generate).
2. **③ 데이터셋 승격 셀** — `source_trace_id` 를 강조: 데이터셋 항목에서 원본 실패
   현장으로 바로 점프된다. "실패는 버리는 게 아니라 시험지가 된다."
3. **⑤ 실험 결과 표 + run URL** — 같은 데이터셋·같은 judge 에서 프롬프트만 바꿔
   v1 vs v2 평균 점수가 갈린다. 대시보드 Runs 비교 화면으로 마무리.
   (judge 는 절대평가가 아니라 **상대 비교** 도구라는 캐비앳 언급)

## 예상 소요: 25분 (① 5분 / ②③ 8분 / ④ 4분 / ⑤⑥ 8분)

## 자주 나올 질문

- **Q. user_feedback 을 실제 서비스에선 어떻게 모으나요?**
  A. 답변 UI의 👍/👎 버튼에서 `create_score(trace_id=...)` 를 호출하면 끝이다.
  trace_id 를 응답과 함께 프론트로 내려주는 것이 유일한 배선이다.
- **Q. judge 가 틀리면요?**
  A. 그래서 judge 프롬프트/모델도 버전 관리·검증 대상이다. 데모에선 동일 judge 로
  두 run 을 상대 비교하므로 절대값의 정확성보다 순위의 일관성만 필요하다.
