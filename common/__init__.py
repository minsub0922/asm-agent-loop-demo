"""공통 유틸 패키지 — 경로/환경변수 초기화.

어느 데모에서 임포트하든 레포 루트의 .env 를 읽고 outputs/ 를 준비한다.
"""

from pathlib import Path

from dotenv import load_dotenv

# 레포 루트 (common/ 의 부모)
ROOT = Path(__file__).resolve().parent.parent

# .env 는 없어도 된다 (mock 모드는 기본값만으로 동작)
load_dotenv(ROOT / ".env", override=False)

# 데모 산출물(그래프 PNG, 발행된 답변, 브리프 등) 저장 위치
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)
