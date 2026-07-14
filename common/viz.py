"""그래프 시각화 헬퍼.

- 노트북: `show_graph(app, "s2")` → PNG 인라인 표시 + outputs/graph_s2.png 저장
- 렌더러 3단 폴백: mermaid.ink(고품질, 네트워크 필요) → networkx/matplotlib(오프라인)
  → ASCII(grandalf). 오프라인 리허설에서도 PNG 가 항상 생성된다.
"""

from __future__ import annotations

from common import OUTPUTS


def _draw_png_offline(g, path) -> bytes:
    """mermaid.ink 없이 networkx + matplotlib 로 계층형 PNG 렌더링."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    G = nx.DiGraph()
    for nid in g.nodes:
        G.add_node(nid)
    for e in g.edges:
        G.add_edge(e.source, e.target, conditional=bool(getattr(e, "conditional", False)))

    # __start__ 로부터의 거리로 레이어를 나눠 왼→오 계층 배치 (mermaid LR 과 유사)
    try:
        depth = nx.single_source_shortest_path_length(G, "__start__")
    except Exception:
        depth = {}
    maxd = max(depth.values(), default=0)
    for n in G.nodes:
        G.nodes[n]["layer"] = depth.get(n, maxd + 1)
    pos = nx.multipartite_layout(G, subset_key="layer", align="vertical", scale=2.0)

    fig, ax = plt.subplots(figsize=(2.6 * (maxd + 2), 5.5))
    solid = [(u, v) for u, v, d in G.edges(data=True) if not d["conditional"]]
    dashed = [(u, v) for u, v, d in G.edges(data=True) if d["conditional"]]
    common_kw = dict(ax=ax, arrows=True, arrowsize=18, node_size=4200,
                     min_source_margin=28, min_target_margin=28)
    nx.draw_networkx_edges(G, pos, edgelist=solid, edge_color="#495057",
                           connectionstyle="arc3,rad=0.08", **common_kw)
    nx.draw_networkx_edges(G, pos, edgelist=dashed, style="dashed", edge_color="#e8590c",
                           connectionstyle="arc3,rad=0.18", **common_kw)
    for n, (x, y) in pos.items():
        ax.text(x, y, n, ha="center", va="center", fontsize=9, zorder=5,
                bbox=dict(boxstyle="round,pad=0.45", fc="#e7f5ff", ec="#1c7ed6", lw=1.2))
    ax.set_axis_off()
    ax.set_title("offline renderer / dashed = conditional edge", fontsize=8, color="#868e96")
    ax.margins(0.15)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path.read_bytes()


def show_graph(app, name: str):
    """컴파일된 그래프를 그려 노트북에 표시하고 outputs/graph_{name}.png 로 저장한다."""
    g = app.get_graph()
    path = OUTPUTS / f"graph_{name}.png"
    png = None
    try:
        png = g.draw_mermaid_png()  # 1순위: mermaid.ink API (네트워크 필요, 가장 예쁨)
        renderer = "mermaid.ink"
    except Exception:
        try:
            png = _draw_png_offline(g, path)  # 2순위: 오프라인 networkx 렌더러
            renderer = "networkx(offline)"
        except Exception as e2:
            print(f"⚠ PNG 렌더링 실패({e2.__class__.__name__}) — ASCII 폴백:\n")
            print(g.draw_ascii())  # 3순위: ASCII (grandalf)
            return None
    path.write_bytes(png)
    print(f"저장: outputs/graph_{name}.png  (renderer: {renderer})")
    from IPython.display import Image

    return Image(png)


def mermaid_source(app) -> str:
    """mermaid 소스 텍스트 (README/슬라이드에 붙여넣기 용)."""
    return app.get_graph().draw_mermaid()
