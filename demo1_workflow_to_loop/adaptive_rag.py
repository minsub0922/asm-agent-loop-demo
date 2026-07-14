"""데모 1 s4 (Adaptive RAG) — 재사용 모듈.

demo1.ipynb 의 s4 섹션과 **동일한 구현**이다.
노트북은 교육용으로 셀 단위 전개하고, 이 모듈은 데모 2/3/5 가 임포트해 재사용한다.
(의도된 중복 — 한쪽을 고치면 다른 쪽도 함께 고칠 것)

그래프 구조:
                       ┌── direct_answer ───────────────────────┐
    route_question ────┼── web_search ─────────────┐            │
                       └── retrieve ── grade_documents ── generate ── END
                             ▲                │
                             └ transform_query┘  (관련 문서 없음 & 재작성 예산 남음)
"""

from __future__ import annotations

from typing import List, TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from common.console import console
from common.llm import get_llm
from common.retriever import format_docs, get_retriever
from common.websearch import format_web_results, web_search

# 루프 탈출 조건 — 이 값이 없으면 잘못된 질문에서 그래프가 영원히 돈다
MAX_REWRITES = 2

# ── 프롬프트 (mock 모델의 마커 규약 [질문]/[문서]/[컨텍스트] 를 따른다) ──
ROUTER_PROMPT = (
    "당신은 질문 라우터다. 아래 질문을 보고 다음 중 하나만 소문자로 출력하라.\n"
    "- vectorstore: 내부 용어집(LangGraph/Langfuse/에이전트 설계)으로 답할 수 있는 질문\n"
    "- web_search: 최신 소식·외부 정보가 필요한 질문\n"
    "- direct: 검색이 필요 없는 인사·잡담·단순 질문\n"
    "[질문]\n{question}"
)
GRADER_PROMPT = (
    "당신은 문서 관련성 평가자다. 문서가 질문에 답하는 근거로 쓸모 있으면 yes,\n"
    "아니면 no 만 출력하라.\n"
    "[질문]\n{question}\n[문서]\n{document}"
)
REWRITER_PROMPT = (
    "당신은 검색 쿼리 재작성기다. 아래 질문을 내부 용어집이 쓰는 표준 용어로\n"
    "바꿔 검색 쿼리 한 줄만 출력하라.\n"
    "[질문]\n{question}"
)
# '허술한' v1 성격의 생성 프롬프트 — 컨텍스트에 근거가 없어도 답하게 방치한다.
# 데모 3 에서 이 프롬프트가 v2 로 개선되는 것이 관측-개선 루프의 소재가 된다.
# (프롬프트 규약: 지시문을 앞에, [질문] 섹션을 마지막에 둔다)
GENERATION_PROMPT = (
    "다음 컨텍스트를 참고해 질문에 한국어로 간결하게 답하라.\n"
    "[컨텍스트]\n{context}\n[질문]\n{question}"
)
DIRECT_PROMPT = "검색 없이 바로 한국어로 간결하게 답하라.\n[질문]\n{question}"


class RagState(TypedDict, total=False):
    """그래프 전체가 공유하는 상태."""

    question: str          # 현재 질문 (transform_query 가 재작성하면 바뀐다)
    documents: List[Document]
    answer: str
    route: str             # vectorstore | web_search | direct
    rewrite_count: int     # 루프 탈출 조건용 카운터


# ── 노드 ──────────────────────────────────────────────────────
_retriever = None


def _ret():
    global _retriever
    if _retriever is None:
        _retriever = get_retriever(k=2)
    return _retriever


def route_question(state: RagState) -> dict:
    """진입 라우터: 질문 성격에 따라 3갈래 분기."""
    label = (
        get_llm("router")
        .invoke(ROUTER_PROMPT.format(question=state["question"]))
        .content.strip().lower()
    )
    if label not in ("vectorstore", "web_search", "direct"):
        label = "vectorstore"  # 안전망: 이상 출력이면 기본 경로
    return {"route": label, "rewrite_count": state.get("rewrite_count", 0)}


def retrieve(state: RagState) -> dict:
    """코퍼스 검색."""
    return {"documents": _ret().retrieve(state["question"])}


def grade_documents(state: RagState) -> dict:
    """문서별 관련성 이진 판정 — 쓸모없는 문서를 걸러낸다."""
    grader = get_llm("grader")
    keep = []
    for d in state["documents"]:
        verdict = (
            grader.invoke(
                GRADER_PROMPT.format(question=state["question"], document=d.page_content)
            ).content.strip().lower()
        )
        console.print(f"    · 관련성 판정 {d.metadata['source']} → [bold]{verdict}[/]")
        if verdict.startswith("y"):
            keep.append(d)
    return {"documents": keep}


def transform_query(state: RagState) -> dict:
    """검색 친화적으로 질문 재작성 → retrieve 로 되돌아가는 루프를 만든다."""
    new_q = (
        get_llm("rewriter")
        .invoke(REWRITER_PROMPT.format(question=state["question"]))
        .content.strip()
    )
    console.print(f"    · 쿼리 재작성: [italic]{new_q}[/]")
    return {"question": new_q, "rewrite_count": state.get("rewrite_count", 0) + 1}


def web_search_node(state: RagState) -> dict:
    """웹 검색 (Tavily 키 없으면 모의 결과 폴백)."""
    results = web_search(state["question"])
    doc = Document(
        page_content=format_web_results(results),
        metadata={"source": "web_search", "title": "웹 검색 결과"},
    )
    return {"documents": [doc]}


def generate(state: RagState) -> dict:
    """검색 결과를 근거로 답변 생성."""
    answer = (
        get_llm("generator")
        .invoke(
            GENERATION_PROMPT.format(
                context=format_docs(state.get("documents", [])), question=state["question"]
            )
        ).content
    )
    return {"answer": answer}


def direct_answer(state: RagState) -> dict:
    """검색 없이 바로 답하는 경로."""
    answer = get_llm("direct").invoke(DIRECT_PROMPT.format(question=state["question"])).content
    return {"answer": answer}


# ── 조건부 엣지 판정 함수 ─────────────────────────────────────
def route_label(state: RagState) -> str:
    return state["route"]


def decide_after_grade(state: RagState) -> str:
    """관련 문서가 있으면 생성, 없으면 재작성 루프 (단, 예산 소진 시 탈출)."""
    if state["documents"]:
        return "generate"
    if state.get("rewrite_count", 0) >= MAX_REWRITES:
        console.print(f"    · 재작성 예산 소진(max {MAX_REWRITES}) → 탈출하여 생성으로")
        return "generate"
    return "transform_query"


# ── 그래프 빌더 ───────────────────────────────────────────────
def build_graph() -> StateGraph:
    """노드/엣지 구성이 끝난 (컴파일 전) StateGraph — 데모 2 가 노드를 덧붙여 확장한다."""
    g = StateGraph(RagState)
    g.add_node("route_question", route_question)
    g.add_node("retrieve", retrieve)
    g.add_node("grade_documents", grade_documents)
    g.add_node("transform_query", transform_query)
    g.add_node("web_search", web_search_node)
    g.add_node("generate", generate)
    g.add_node("direct_answer", direct_answer)

    g.add_edge(START, "route_question")
    g.add_conditional_edges(
        "route_question",
        route_label,
        {"vectorstore": "retrieve", "web_search": "web_search", "direct": "direct_answer"},
    )
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges(
        "grade_documents",
        decide_after_grade,
        {"generate": "generate", "transform_query": "transform_query"},
    )
    g.add_edge("transform_query", "retrieve")  # ← 루프를 만드는 되돌아가는 엣지
    g.add_edge("web_search", "generate")
    g.add_edge("generate", END)
    g.add_edge("direct_answer", END)
    return g


def build_adaptive_rag(checkpointer=None):
    """컴파일된 Adaptive RAG 그래프 (데모 2/3/5 재사용 진입점)."""
    return build_graph().compile(checkpointer=checkpointer)
