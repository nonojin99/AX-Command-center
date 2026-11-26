"""분석 기록 세션 — 유연한 분석을 '검증 가능하게' 만든다.

사용(분석 스크립트 맨 위):
    from engine.session import Session
    s = Session("A01 PM 전후 7일 결함 수 비교")      # 질문을 그대로 적는다
    npw = s.src.npw([...], start, end)               # s.src = 데이터 소스 (HUB_SOURCE 환경변수: synthetic(기본) | bdq)
    s.table(df, "결과", time_col="ts", expected=(start, end))   # 점검 + 저장 + 화면에는 일부 행만 출력
    s.note("가정: PM 직후 = PM 시각 이후 7일")          # 가정은 반드시 적는다
    s.finish()                                       # hub/runs/<시각>_<질문>/ 에 code.py·summary.md·표·차트 저장

화면(=Claude 가 읽는 출력)에는 HUB_PREVIEW_ROWS(기본 5) 행만 내보낸다. 0 이면 행 없이 형태·요약만. 전체 표는 runs/ 의 csv 에만 있다.
runs/ 는 .gitignore 대상이다(실데이터가 들어갈 수 있다).
"""
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from . import checks

RUNS = Path(__file__).resolve().parent.parent / "runs"


def _default_source():
    which = os.environ.get("HUB_SOURCE", "synthetic").lower()
    if which == "bdq":
        from .sources import BDQSource
        return BDQSource()
    from .sources import SyntheticSource
    return SyntheticSource()


class Session:
    def __init__(self, question, source=None):
        self.question = question
        self.src = source or _default_source()
        self.preview = int(os.environ.get("HUB_PREVIEW_ROWS", "5"))
        slug = re.sub(r"[^\w가-힣]+", "-", question)[:30].strip("-")
        self.dir = RUNS / f"{datetime.now():%Y%m%d_%H%M%S}_{slug}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.notes, self.files = [], []
        checks.WARNINGS.clear()
        script = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
        if script and script.is_file():
            shutil.copy(script, self.dir / "code.py")  # 이 분석을 만든 코드를 그대로 보관

    def table(self, df, name, **check_kwargs):
        checks.check_df(df, name, **check_kwargs)
        path = self.dir / f"{name}.csv"
        df.to_csv(path, index=True, encoding="utf-8-sig")
        self.files.append(path.name)
        print(f"[{name}] {df.shape[0]}행 x {df.shape[1]}열")
        if self.preview > 0:
            print(df.head(self.preview).to_string())
        return df

    def fig(self, figure, name):
        path = self.dir / f"{name}.html"
        figure.write_html(str(path))
        self.files.append(path.name)

    def note(self, text):
        self.notes.append(text)

    def finish(self):
        lines = [f"# {self.question}", "", f"- 실행: {datetime.now():%Y-%m-%d %H:%M}",
                 f"- 데이터 소스: {self.src.name}", "", "## 가정", *([f"- {n}" for n in self.notes] or ["- (기록된 가정 없음)"]),
                 "", "## 사용한 조회", *[f"- {x}" for x in getattr(self.src, "log", [])],
                 "", "## 자동 점검 경고", *([f"- {w}" for w in checks.WARNINGS] or ["- 없음 (※ 통과 = 맞다는 뜻이 아님)"]),
                 "", "## 파일", *[f"- {f}" for f in ["code.py", *self.files]]]
        (self.dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"기록 저장: {self.dir}")
        return self.dir
