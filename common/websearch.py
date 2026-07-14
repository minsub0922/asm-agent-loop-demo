"""웹 검색 헬퍼 — Tavily 키가 있으면 실제 호출, 없으면 모의 결과로 자동 폴백.

폴백은 조용히 일어나지 않고 콘솔에 경고를 남긴다 (실패를 삼키지 않기).
"""

from __future__ import annotations

import os
from typing import Dict, List

from common.llm import provider

MOCK_BADGE = "(모의 웹 결과)"


def _mock_results(query: str, max_results: int) -> List[Dict]:
    base = [
        {
            "title": f"'{query[:40]}' 최신 동향 정리 {MOCK_BADGE}",
            "url": "https://example.com/mock/trend",
            "content": (
                f"[모의 웹 검색] {query} 관련 요약: LangGraph 와 에이전트 생태계는 "
                "루프 기반 설계, 휴먼 인 더 루프, 관측성 표준(OTel) 중심으로 진화하고 있다."
            ),
        },
        {
            "title": f"커뮤니티 반응 모음 {MOCK_BADGE}",
            "url": "https://example.com/mock/community",
            "content": (
                f"[모의 웹 검색] {query} 에 대한 개발자 커뮤니티의 평: 워크플로보다 "
                "루프와 평가 사이클을 먼저 설계하라는 조언이 많다."
            ),
        },
        {
            "title": f"공식 블로그 하이라이트 {MOCK_BADGE}",
            "url": "https://example.com/mock/blog",
            "content": f"[모의 웹 검색] {query} 공식 발표 요지: 안정 버전 릴리스와 문서 개편이 진행 중.",
        },
    ]
    return base[:max_results]


def web_search(query: str, max_results: int = 3) -> List[Dict]:
    """[{title, url, content}] 목록을 반환한다."""
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if key and provider() != "mock":
        try:
            from langchain_tavily import TavilySearch

            tool = TavilySearch(max_results=max_results)
            res = tool.invoke({"query": query})
            items = res.get("results", []) if isinstance(res, dict) else []
            if items:
                return [
                    {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
                    for r in items
                ]
            print("⚠ Tavily 응답이 비어 있어 모의 결과로 폴백합니다.")
        except Exception as e:  # 키 오류/네트워크 오류 → 데모가 멈추지 않게 폴백
            print(f"⚠ Tavily 호출 실패({e.__class__.__name__}: {e}) — 모의 결과로 폴백합니다.")
    return _mock_results(query, max_results)


def format_web_results(results: List[Dict]) -> str:
    """웹 결과를 [컨텍스트] 섹션 문자열로 변환."""
    return "\n\n".join(f"# {r['title']}\n{r['content']}\n(출처: {r['url']})" for r in results)
