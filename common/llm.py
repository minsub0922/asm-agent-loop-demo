"""LLM / 임베딩 팩토리 — env `LLM_PROVIDER` 하나로 openai | ollama | mock 전환.

mock 프로바이더는 **규칙 기반 결정적(fake) 모델**이다. API 키·네트워크 없이
그래프의 모든 분기(라우팅 / 관련성 판정 / 쿼리 재작성 / 생성 / LLM-as-a-Judge)를
항상 같은 결과로 재현할 수 있어 오프라인 리허설에 쓴다.

■ 프롬프트 마커 규약 (mock 모델이 프롬프트를 파싱하는 기준 — 전 데모 공통)
    [질문] ...            : 사용자 질문
    [문서] ...            : 관련성 판정 대상 문서 1건
    [컨텍스트] ...        : 생성에 쓸 검색 결과 묶음
    [골든 답변] / [실제 답변] : judge 채점 입력
role 값: router | grader | rewriter | generator | direct | judge | critique
(openai/ollama 프로바이더에서는 role 이 무시되고 동일 모델이 반환된다)
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


# ──────────────────────────────────────────────────────────────
# 팩토리
# ──────────────────────────────────────────────────────────────
def provider() -> str:
    return os.getenv("LLM_PROVIDER", "mock").strip().lower()


def get_llm(role: str = "generator", temperature: float = 0.0) -> BaseChatModel:
    """역할(role)별 LLM 반환. mock 에서만 role 이 동작을 결정한다."""
    p = provider()
    if p == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature
        )
    if p == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )
    if p == "mock":
        return RuleBasedChatModel(role=role)
    raise ValueError(f"알 수 없는 LLM_PROVIDER: {p} (openai|ollama|mock 중 하나)")


def get_embeddings():
    """임베딩 모델 반환. mock 은 결정적 fake 임베딩(실제로는 키워드 검색을 사용)."""
    p = provider()
    if p == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    if p == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    from langchain_core.embeddings import DeterministicFakeEmbedding

    return DeterministicFakeEmbedding(size=256)


# ──────────────────────────────────────────────────────────────
# 토큰화 (mock 라우팅/판정/채점의 공통 기준 — retriever 도 이 함수를 쓴다)
# ──────────────────────────────────────────────────────────────
# 코퍼스 전반에 흔해서 판정 근거가 못 되는 단어들
STOPWORDS = {
    "langgraph", "langchain", "단계", "방법", "무엇", "설명", "알려줘", "어떻게",
    "해요", "하는", "있는", "위한", "대해", "언제", "기능", "사용", "적용",
    "질문", "답변", "그리고", "하면", "해서", "인가요", "뭐야", "주세요", "합니다",
}

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣_\-]+")


def tokens(text: str) -> set:
    """소문자 토큰 집합 (2글자 이상, 불용어 제외)."""
    return {
        t
        for t in (m.group(0).lower() for m in _TOKEN_RE.finditer(text or ""))
        if len(t) >= 2 and t not in STOPWORDS
    }


# ──────────────────────────────────────────────────────────────
# mock 규칙 정의
# ──────────────────────────────────────────────────────────────
# 라우터: 웹 검색이 필요한 질문의 신호
WEB_HINTS = ["웹", "web", "검색해", "최신", "뉴스", "요즘", "오늘", "이번 주", "날씨", "릴리스", "release", "동향"]
# 라우터: 내부 코퍼스(용어집)로 답할 수 있는 질문의 신호
CORPUS_HINTS = [
    "rag", "langgraph", "langfuse", "에이전트", "루프", "노드", "엣지", "그래프",
    "체크포인터", "체크포인트", "interrupt", "인터럽트", "hitl", "승인", "관측",
    "트레이스", "trace", "데이터셋", "프롬프트", "서브에이전트", "딥", "otel",
    "라우팅", "쿼리", "워크플로", "평가", "judge", "휴먼",
]
# 재작성기: (질문 속 트리거 단어들, 코퍼스 표준 용어로 재작성한 검색 쿼리)
REWRITE_RULES = [
    (
        ["approval", "승인", "human", "컨펌", "사람이 확인", "허락"],
        "LangGraph 그래프 실행 중단 interrupt 휴먼 인 더 루프 승인 수정 거부 HITL",
    ),
    (
        ["모니터링", "디버깅", "관측", "trace", "느린", "비용"],
        "Langfuse 트레이스 span generation 관측성 CallbackHandler 셀프호스팅",
    ),
    (
        ["점수", "채점", "테스트", "회귀", "품질 비교"],
        "데이터셋 실험 LLM-as-a-Judge 스코어 골든 답변 회귀 테스트",
    ),
]


def _section(text: str, name: str) -> Optional[str]:
    """프롬프트에서 [마커] 섹션 내용을 추출한다."""
    m = re.search(rf"\[{name}\]\s*(.*?)(?=\n\[[^\]]+\]|\Z)", text, re.S)
    return m.group(1).strip() if m else None


def _first_title(ctx: str) -> str:
    for line in ctx.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "제목 미상 문서"


def _first_paragraph(ctx: str, limit: int = 220) -> str:
    """제목/키워드 라인 뒤의 첫 본문 단락을 요약용으로 뽑는다."""
    body = []
    for line in ctx.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            if body:
                break
            continue
        body.append(s)
    text = " ".join(body)
    return (text[:limit] + "…") if len(text) > limit else text


def _rule_answer(role: str, text: str) -> str:
    """role 과 프롬프트 텍스트를 보고 결정적 응답을 만든다."""
    q = _section(text, "질문") or text[-500:]
    ql = q.lower()

    if role == "router":
        if any(h in ql for h in WEB_HINTS):
            return "web_search"
        if any(h in ql for h in CORPUS_HINTS):
            return "vectorstore"
        return "direct"

    if role == "grader":
        doc = _section(text, "문서") or ""
        # 문서의 "> 키워드:" 라인에 있는 시그니처 용어가 질문에 등장하면 관련 있음
        m = re.search(r">\s*키워드\s*:\s*(.+)", doc)
        if m:
            kws = [k.strip().lower() for k in m.group(1).split(",") if len(k.strip()) >= 2]
            return "yes" if any(k in ql for k in kws) else "no"
        # 키워드 라인이 없는 문서는 토큰 겹침으로 보수적으로 판정
        return "yes" if len(tokens(q) & tokens(doc)) >= 3 else "no"

    if role == "rewriter":
        for triggers, rewritten in REWRITE_RULES:
            if any(t in ql for t in triggers):
                return rewritten
        return f"{q} 개념 정의 용어"

    if role == "direct":
        return f"(모의 직접 답변) \"{q}\" — 검색이 필요 없는 질문이라 바로 답합니다. 반갑습니다, 데모를 시작해 볼까요?"

    if role == "generator":
        ctx = _section(text, "컨텍스트") or ""
        title = _first_title(ctx)
        snippet = _first_paragraph(ctx)
        # 질문은 항상 [질문] 섹션의 첫 줄 (프롬프트 규약: 지시문은 앞, [질문]은 마지막)
        q_line = q.strip().splitlines()[0] if q.strip() else ""
        relevant = len(tokens(q_line) & tokens(ctx)) >= 1
        honest = ("모른다" in text) or ("근거가 없" in text)  # 프롬프트 v2 지시 감지
        if not ctx.strip():
            return f"(모의 답변) 컨텍스트가 비어 있어 일반 지식으로 답합니다: {q}"
        if relevant:
            return f"「{title}」 문서를 근거로 답합니다.\n{snippet}\n(모의 생성 — provider=mock)"
        if honest:
            return (
                "제공된 컨텍스트에서 이 질문에 대한 근거를 찾지 못했습니다. "
                "근거 없는 내용은 답하지 않겠습니다. 질문을 바꾸거나 웹 검색을 이용해 주세요. "
                "(모의 생성 — provider=mock)"
            )
        # 허술한 프롬프트(v1) + 빗나간 문서 → 그럴듯한 동문서답 (환각 연출)
        return (
            f"좋은 질문입니다! 「{title}」 문서에 따르면 {snippet} "
            f"따라서 질문하신 내용도 같은 원리로 이해하시면 됩니다. (모의 생성 — provider=mock)"
        )

    if role == "judge":
        golden = _section(text, "골든 답변") or ""
        actual = _section(text, "실제 답변") or ""
        g, a = tokens(golden), tokens(actual)
        ratio = len(g & a) / max(1, len(g))
        score = 1.0 if ratio >= 0.5 else 0.7 if ratio >= 0.3 else 0.4 if ratio >= 0.15 else 0.1
        return f'{{"score": {score}, "reasoning": "골든 답변과의 핵심 토큰 겹침 {ratio:.2f} 기준 (모의 채점)"}}'

    if role == "critique":
        return (
            "초안 비평(모의): 1) 핵심 주장마다 코퍼스/웹 근거 인용을 붙일 것. "
            "2) '왜 중요한가' 단락에 반례(루프 없는 시스템의 실패 사례)를 추가할 것. "
            "3) 결론에 실행 가능한 다음 단계 3가지를 명시할 것."
        )

    return f"(모의 응답) {q[:120]}"


# ──────────────────────────────────────────────────────────────
# mock 모델 구현
# ──────────────────────────────────────────────────────────────
class RuleBasedChatModel(BaseChatModel):
    """규칙 기반 결정적 채팅 모델. 같은 입력 → 항상 같은 출력."""

    role: str = "generator"

    @property
    def _llm_type(self) -> str:
        return f"rule-mock-{self.role}"

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        text = "\n".join(str(m.content) for m in messages)
        content = _rule_answer(self.role, text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def bind_tools(self, tools, **kwargs):  # 데모 편의: 도구 바인딩은 무시
        return self


class ScriptedChatModel(BaseChatModel):
    """미리 짜둔 AIMessage 시퀀스를 순서대로 반환하는 모델 (데모 5 mock 용).

    도구 호출(tool_calls)이 포함된 메시지를 스크립트로 넣으면
    딥 에이전트의 플래닝→위임→종합 흐름을 오프라인에서 그대로 재현할 수 있다.
    """

    script: List[Any]  # list[AIMessage]
    _i: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted-mock"

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self._i < len(self.script):
            msg = self.script[self._i]
            self._i += 1
        else:
            msg = AIMessage(content="(스크립트 소진 — 작업을 마칩니다)")
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self
