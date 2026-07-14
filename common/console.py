"""rich 기반 데모 출력 헬퍼 — 청중이 화면으로 읽기 좋은 구조화된 출력.

노트북(Jupyter)과 터미널 양쪽에서 동작한다.
"""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console()


def banner(title: str, subtitle: str = "") -> None:
    """데모/단계 시작 배너."""
    console.print()
    console.print(Rule(f"[bold white on blue] {title} [/]", style="blue"))
    if subtitle:
        console.print(f"[dim]{subtitle}[/]")


def step(text: str) -> None:
    """단계 구분선."""
    console.print(Rule(f"[bold cyan]{text}[/]", style="cyan"))


def node_log(name: str, note: str = "") -> None:
    """그래프 노드 진입 로그."""
    console.print(f"  [bold cyan]▶ {name}[/]" + (f"  [dim]{note}[/]" if note else ""))


def show_answer(question: str, answer: str, route: Optional[str] = None, title: str = "최종 답변") -> None:
    """최종 답변 강조 패널."""
    head = f"[bold]Q.[/] {question}"
    if route:
        head += f"\n[dim]경로: {route}[/]"
    console.print(Panel(f"{head}\n\n[bold green]A.[/] {answer}", title=f"✅ {title}", border_style="green"))


def diff_panel(lines: Iterable[str], title: str = "이번 단계에서 달라진 점") -> None:
    """이전 단계 대비 diff 포인트 강조."""
    body = "\n".join(f"[bold yellow]+[/] {l}" for l in lines)
    console.print(Panel(body, title=f"🔍 {title}", border_style="yellow"))


def compare_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
    """before/after 비교 표."""
    t = Table(title=title, show_lines=True, title_style="bold")
    for c in columns:
        t.add_column(c, overflow="fold")
    for r in rows:
        t.add_row(*[str(c) for c in r])
    console.print(t)


def _summarize_delta(delta) -> str:
    """노드가 반환한 상태 변경분을 한 줄로 요약."""
    if not isinstance(delta, dict):
        return ""
    parts = []
    for key, val in delta.items():
        if key == "documents" and isinstance(val, list):
            titles = ", ".join(d.metadata.get("title", "?") for d in val) or "0건"
            parts.append(f"documents={len(val)}건 [{titles}]")
        elif key in ("answer", "draft_answer") and isinstance(val, str):
            one = val.replace("\n", " ")
            parts.append(f"{key}='{one[:60]}…'" if len(one) > 60 else f"{key}='{one}'")
        elif isinstance(val, (str, int, float, bool)):
            parts.append(f"{key}={val}")
    return "  ".join(parts)


def stream_run(app, inputs, config: Optional[dict] = None) -> Tuple[Optional[dict], Optional[tuple]]:
    """그래프를 스트리밍 실행하며 노드 진입을 로그로 보여준다.

    반환: (최종 상태, interrupt 페이로드 튜플 또는 None)
    - stream_mode "updates" 로 노드별 변경분을, "values" 로 최종 상태를 받는다.
    - HITL 데모에서 그래프가 interrupt 로 멈추면 두 번째 반환값에 담긴다.
    """
    final_state, interrupted = None, None
    for mode, chunk in app.stream(inputs, config=config, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
            continue
        for node, delta in chunk.items():
            if node == "__interrupt__":
                interrupted = delta
                console.print("  [bold red]⏸ interrupt — 사람의 판단을 기다립니다[/]")
                continue
            node_log(node, _summarize_delta(delta))
    return final_state, interrupted
