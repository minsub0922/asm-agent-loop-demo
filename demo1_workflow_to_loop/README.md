# 데모 1 — Workflow → Loop Engineering (메인)

**한 줄 요약**: 같은 질문 세트가 s1(직선) → s2(그래프화) → s3(루프) → s4(라우터)를
거치며 답이 좋아지는 것을 노트북 셀 단위로 눈앞에서 보여준다.

## 실행

```bash
make lab                      # JupyterLab → demo1_workflow_to_loop/demo1.ipynb 열기
# 리허설(headless):
make demo1                    # 실행 결과는 outputs/executed/demo1.ipynb
```

- `LLM_PROVIDER=mock`(기본): 키·네트워크 없이 완전 재현. 실 모델은 `.env`에서 `openai|ollama`.
- 그래프 그림: 각 단계의 `show_graph()` 셀이 `outputs/graph_s2~s4.png` 저장
  (mermaid.ink → 실패 시 오프라인 networkx → ASCII 순 폴백).

## 예시 질문 3개 (노트북 QUESTIONS 셀)

1. 정상: "LangGraph에서 조건부 엣지는 무엇이고 언제 쓰나요?"
2. 한계: "LangGraph로 human approval 단계를 넣으려면 어떻게 해요?" ← 어휘 불일치로 검색이 빗나감
3. 라우팅: "LangGraph 최신 릴리스 소식을 웹에서 검색해 요약해줘" / 인사말

## 발표 포인트 3개

1. **s1 한계 질문 셀** — 검색이 `human`이라는 단어에 걸려 엉뚱한 문서를 물어와도
   생성은 멈추지 않는다. "실패가 감지되지 않고 사용자에게 전달된다"를 답변 패널로 보여줄 것.
2. **s3 조건부 엣지 셀** (`decide_to_generate` + `g3.add_edge("transform_query", "retrieve")`) —
   되돌아가는 엣지 한 줄이 루프의 전부다. 직후 실행 셀의 `실행 경로:` 출력에서
   `transform_query → retrieve` 재진입을 가리킬 것. **"루프에는 반드시 탈출 조건"**
   (`rewrite_count ≤ MAX_REWRITES=2`) 멘트 필수.
3. **s4 마지막 총괄표 셀** — 같은 질문의 답이 단계별로 어떻게 변했는지 매트릭스로 마무리.
   "경로가 다양해지는 순간 관측이 필요해진다"로 데모 3을 예고.

## 예상 소요: 30분 (섹션당 6~8분 + 질문 버퍼)

## 자주 나올 질문

- **Q. grade/rewrite 를 LLM 이 하면 비용이 2배 아닌가요?**
  A. 판정은 저렴한 소형 모델로 충분하고, 정상 질문은 루프를 안 돌기 때문에(노트북 s3 두 번째
  실행 셀에서 확인) 추가 비용은 실패 케이스에만 발생한다. 오답이 사용자에게 나가는 비용과 비교할 것.
- **Q. 재작성 2회로도 못 찾으면?**
  A. 탈출 조건이 발동해 빈 컨텍스트로 generate 로 넘어간다. 이때 "모른다"고 답하게 만드는
  프롬프트 개선이 데모 3의 소재다 (v1→v2 실험).
