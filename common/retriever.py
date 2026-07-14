"""코퍼스 로딩 + retriever 헬퍼.

- mock  : 키워드 겹침 점수 기반 검색 (결정적 — 리허설용)
- 그 외 : FAISS 벡터 검색 (최초 1회 임베딩 후 .cache/ 에 저장)

두 구현 모두 `retrieve(query) -> list[Document]` 인터페이스만 가진다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List

import numpy as np
from langchain_core.documents import Document

from common import ROOT
from common.llm import get_embeddings, provider, tokens

CORPUS_DIR = ROOT / "data" / "corpus"
CACHE_DIR = ROOT / ".cache"


def load_corpus() -> List[Document]:
    """data/corpus/*.md 를 문서 단위로 로드한다 (문서가 작아 청킹 없이 통째로)."""
    docs = []
    for p in sorted(CORPUS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        docs.append(Document(page_content=text, metadata={"source": p.name, "title": title}))
    if not docs:
        raise FileNotFoundError(f"코퍼스가 비어 있습니다: {CORPUS_DIR}")
    return docs


class KeywordRetriever:
    """질문 토큰이 문서에 몇 종류나 등장하는지로 점수를 매기는 결정적 검색기."""

    def __init__(self, docs: List[Document], k: int = 2):
        self.docs, self.k = docs, k

    def retrieve(self, query: str) -> List[Document]:
        qtok = tokens(query)
        scored = []
        for d in self.docs:
            body = d.page_content.lower()
            score = sum(1 for t in qtok if t in body)
            scored.append((score, d.metadata["source"], d))
        # 점수 내림차순, 동점이면 파일명 순 (완전 결정적)
        scored.sort(key=lambda x: (-x[0], x[1]))
        # 점수가 0이어도 top-k 를 반환한다 — "빗나간 검색"을 일부러 겪게 하는 장치
        return [d for _, _, d in scored[: self.k]]


class VectorRetriever:
    """FAISS 코사인 유사도 검색기. 임베딩은 코퍼스가 바뀌지 않는 한 캐시를 재사용."""

    def __init__(self, docs: List[Document], k: int = 2):
        import faiss  # 지연 임포트

        self.docs, self.k = docs, k
        self.embeddings = get_embeddings()
        vecs = self._load_or_build(docs)
        self.index = faiss.IndexFlatIP(vecs.shape[1])
        self.index.add(vecs)

    def _fingerprint(self, docs) -> str:
        h = hashlib.sha256()
        h.update(provider().encode())
        for d in docs:
            h.update(d.metadata["source"].encode())
            h.update(d.page_content.encode())
        return h.hexdigest()[:16]

    def _load_or_build(self, docs) -> np.ndarray:
        CACHE_DIR.mkdir(exist_ok=True)
        fp = self._fingerprint(docs)
        cache = CACHE_DIR / f"corpus_emb_{fp}.npz"
        if cache.exists():
            return np.load(cache)["vecs"]
        raw = self.embeddings.embed_documents([d.page_content for d in docs])
        vecs = np.asarray(raw, dtype="float32")
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10  # 정규화 → 내적=코사인
        np.savez(cache, vecs=vecs)
        (CACHE_DIR / "meta.json").write_text(
            json.dumps({"fingerprint": fp, "provider": provider()}, ensure_ascii=False)
        )
        return vecs

    def retrieve(self, query: str) -> List[Document]:
        qv = np.asarray([self.embeddings.embed_query(query)], dtype="float32")
        qv /= np.linalg.norm(qv, axis=1, keepdims=True) + 1e-10
        _, idx = self.index.search(qv, self.k)
        return [self.docs[i] for i in idx[0] if i >= 0]


def get_retriever(k: int = 2):
    """프로바이더에 맞는 retriever 반환."""
    docs = load_corpus()
    if provider() == "mock":
        return KeywordRetriever(docs, k=k)
    return VectorRetriever(docs, k=k)


def format_docs(docs: List[Document]) -> str:
    """검색 결과를 [컨텍스트] 섹션에 넣을 문자열로 변환."""
    if not docs:
        return ""
    return "\n\n---\n\n".join(d.page_content for d in docs)
