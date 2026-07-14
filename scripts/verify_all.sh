#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# 전 데모 스모크 테스트 (mock 모드 — API 키·네트워크 불필요)
#   사용: make verify        (또는 bash scripts/verify_all.sh)
#   Langfuse 가 떠 있으면 데모 3까지 검증, 없으면 명시적으로 SKIP.
#   JUPYTER 환경변수로 실행기를 바꿀 수 있다 (기본: uv run jupyter)
# ─────────────────────────────────────────────────────────────
set -u
cd "$(dirname "$0")/.."

JUPYTER="${JUPYTER:-uv run jupyter}"
NB="$JUPYTER nbconvert --to notebook --execute --output-dir outputs/executed"
export LLM_PROVIDER=mock

PASS=(); FAIL=(); SKIP=()
run() {  # run <이름> <명령...>
  local name="$1"; shift
  echo ""
  echo "━━━ [$name] $* ━━━"
  if "$@" >/tmp/verify_"$name".log 2>&1; then
    PASS+=("$name"); echo "  ✅ $name"
  else
    FAIL+=("$name"); echo "  ❌ $name — 로그: /tmp/verify_$name.log (마지막 15줄)"
    tail -15 /tmp/verify_"$name".log
  fi
}

mkdir -p outputs/executed

# ── 데모 1: s1→s4 (노트북 내부 assert: rewrite 루프 1회 이상) ──
run demo1 env LLM_PROVIDER=mock $NB demo1_workflow_to_loop/demo1.ipynb
for g in s2 s3 s4; do
  if [ -f "outputs/graph_${g}.png" ]; then PASS+=("graph_${g}.png");
  else FAIL+=("graph_${g}.png"); echo "  ❌ outputs/graph_${g}.png 미생성"; fi
done

# ── 데모 2: HITL 3경로 자동 (approve/edit/reject — 내부 assert) ──
run demo2 env LLM_PROVIDER=mock DEMO2_AUTO=all $NB demo2_hitl/demo2.ipynb

# ── 데모 4: OTel 계측 (오프라인 console exporter) ──
run demo4 env LLM_PROVIDER=mock OTEL_TARGETS=console $NB demo4_otel_swap/demo4.ipynb

# ── 데모 5: deepagents (내부 assert: 브리프 파일 산출) ──
run demo5 env LLM_PROVIDER=mock $NB demo5_deepagents/demo5.ipynb

# ── 데모 3: 로컬 Langfuse 필요 — 떠 있을 때만 ──
LF="${LANGFUSE_BASE_URL:-http://localhost:3000}"
if curl -sf --max-time 3 "$LF/api/public/health" >/dev/null 2>&1; then
  run demo3 env LLM_PROVIDER=mock $NB demo3_langfuse_loop/demo3.ipynb
else
  SKIP+=("demo3")
  echo ""
  echo "━━━ [demo3] SKIP — Langfuse($LF) 미기동. 'make up' 후 다시 실행하면 검증됩니다 ━━━"
fi

echo ""
echo "═══════════════ 스모크 테스트 결과 ═══════════════"
echo "  통과: ${#PASS[@]}  (${PASS[*]:-})"
[ ${#SKIP[@]} -gt 0 ] && echo "  건너뜀: ${SKIP[*]}"
if [ ${#FAIL[@]} -gt 0 ]; then
  echo "  실패: ${FAIL[*]}"
  exit 1
fi
echo "  모든 검증 통과 ✔  (실행된 노트북: outputs/executed/)"
