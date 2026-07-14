# ─────────────────────────────────────────────────────────────
# loop-engineering-demo
#   리허설(D-1): make up → make seed → make verify
#   라이브 데모 : make lab (JupyterLab에서 노트북 셀 단위 실행)
# ─────────────────────────────────────────────────────────────
UV ?= uv
# 노트북 headless 실행 (결과는 outputs/executed/ 에 저장, 원본은 깨끗하게 유지)
NB = $(UV) run jupyter nbconvert --to notebook --execute --output-dir outputs/executed

.PHONY: help setup lab up down seed verify graphs \
        demo1 demo2 demo3 demo4 demo4-langfuse demo4-phoenix demo4-both demo5

help: ## 타깃 목록
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

setup: ## 의존성 설치 (uv sync) — 벡터 인덱스는 첫 실행 시 자동 빌드/캐시
	$(UV) sync

lab: ## JupyterLab 실행 (라이브 데모 진입점)
	$(UV) run jupyter lab

up: ## Langfuse + Phoenix 로컬 기동 (데모 3~5 사전 준비)
	docker compose -f selfhost/docker-compose.yml up -d

down: ## 로컬 스택 종료
	docker compose -f selfhost/docker-compose.yml down

# ── 노트북 headless 실행 (리허설/스모크용 — 라이브에서는 make lab 사용) ──
demo1: ## 데모1 s1→s4 (mock 권장)
	$(NB) demo1_workflow_to_loop/demo1.ipynb

demo2: ## 데모2 HITL — DEMO2_AUTO=all 로 3경로 자동 실행
	DEMO2_AUTO=$${DEMO2_AUTO:-all} $(NB) demo2_hitl/demo2.ipynb

demo3: ## 데모3 관측-개선 루프 (로컬 Langfuse + 키 필요)
	$(NB) demo3_langfuse_loop/demo3.ipynb

seed: demo3 ## 리허설용 별칭 — 데모3 노트북 실행으로 트레이스/데이터셋/실험 시딩

demo4: ## 데모4 OTel — 현재 env(OTEL_TARGETS 등) 그대로 실행
	$(NB) demo4_otel_swap/demo4.ipynb

demo4-langfuse: ## 데모4 OTel → Langfuse
	OTEL_TARGETS=langfuse $(NB) demo4_otel_swap/demo4.ipynb

demo4-phoenix: ## 데모4 OTel → Phoenix
	OTEL_TARGETS=phoenix $(NB) demo4_otel_swap/demo4.ipynb

demo4-both: ## 데모4 OTel → 두 백엔드 동시 fan-out
	OTEL_TARGETS=langfuse,phoenix $(NB) demo4_otel_swap/demo4.ipynb

demo5: ## 데모5 deepagents 리서치 에이전트
	$(NB) demo5_deepagents/demo5.ipynb

graphs: ## 그래프 PNG 재생성 (demo1/demo2 headless 실행 부산물)
	LLM_PROVIDER=mock $(MAKE) demo1 demo2

verify: ## mock 모드 전체 스모크 테스트
	bash scripts/verify_all.sh
