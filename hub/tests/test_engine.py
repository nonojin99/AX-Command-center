"""실행: python3 hub/tests/test_engine.py  (pandas 만 있으면 엔진 테스트, streamlit 이 있으면 화면 스모크 테스트도)"""
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB))

import pandas as pd  # noqa: E402

from engine import analysis as an, report  # noqa: E402
from engine.sources import SyntheticSource  # noqa: E402

src = SyntheticSource()
master = src.eqp_master()

# 조인 키 정합성: 모든 edx/defect 의 measure_id 가 npw 에 있다
npw_ids = set(src._t["npw"]["measure_id"])
assert set(src._t["edx"]["measure_id"]) <= npw_ids and set(src._t["npw_defect"]["measure_id"]) <= npw_ids

# 4-1: A01 은 Al 비율이 동료(A02)보다 높다
comp = an.edx_composition(src, "ㄱ", 2)["by_eqp"]
assert comp.loc["A01", "Al"] > comp.loc["A02", "Al"] * 1.5, comp

# 4-4: A01 의 1순위 의심 파트는 LINER(높음), 나머지는 낮음
s = an.suspect_parts(src, ["A01"])
assert s.iloc[0]["파트종류"] == "LINER" and s.iloc[0]["의심도"] == "높음", s
assert (s.iloc[1:]["의심도"] == "낮음").all(), s

# 4-2: 시나리오가 없는 ㄴ설비군에서는 '높음'이 나오지 않는다 (오탐 확인)
b = an.suspect_parts(src, master.loc[master.eqp_group == "ㄴ설비군", "eqp_id"].tolist())
assert not (b["의심도"] == "높음").any(), b

# 4-3: PM 주기는 공정 기준 주기(30/40/35일) 근처
m = an.pm_cycle_stats(src, ["ㄱ", "ㄴ", "ㄷ"])["monthly"]
assert m.groupby("process")["평균주기"].mean().between(25, 45).all(), m

# 4-5: 이번 주 SPEC OVER 는 A01 에서만 나오고 보고서가 만들어진다
w = an.spec_over_week(src)
assert len(w["over"]) > 0 and set(w["over"]["eqp_id"]) == {"A01"}, w["by_eqp"]
md = report.spec_over_markdown(w, s)
assert "SPEC 초과" in md and "A01" in md
assert len(report.to_excel({"a": w["over"]})) > 1000
print("엔진 테스트 통과")

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    print("streamlit 없음 — 화면 테스트 건너뜀")
    sys.exit(0)
at = AppTest.from_file(str(HUB / "app.py"), default_timeout=60).run()
assert not at.exception, at.exception
for key in ("b1", "b2", "b3", "b4", "b5"):
    at.button(key=key).click().run()
    assert not at.exception, (key, at.exception)
print("화면 스모크 테스트 통과 (탭 5개 버튼 실행)")
