"""그래프 시각화 헬퍼.

- 노트북: `show_graph(app, "s2")` → PNG 인라인 표시 + outputs/graph_s2.png 저장
- 오프라인: mermaid.ink 접속이 안 되면 ASCII 아트로 자동 폴백 (grandalf)
"""

from __future__ import annotations

from common import OUTPUTS


def show_graph(app, name: str):
    """컴파일된 그래프를 그려 노트북에 표시하고 outputs/ 에 저장한다."""
    g = app.get_graph()
    try:
        png = g.draw_mermaid_png()  # 기본 렌더러는 mermaid.ink API (네트워크 필요)
        path = OUTPUTS / f"graph_{name}.png"
        path.write_bytes(png)
        print(f"저장: {path.relative_to(OUTPUTS.parent)}")
        from IPython.display import Image

        return Image(png)
    except Exception as e:
        print(f"⚠ PNG 렌더링 실패({e.__class__.__name__}) — 오프라인 ASCII 폴백:\n")
        print(g.draw_ascii())
        return None


def mermaid_source(app) -> str:
    """mermaid 소스 텍스트 (README/슬라이드에 붙여넣기 용)."""
    return app.get_graph().draw_mermaid()
