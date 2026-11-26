"""예시 분석 — 정형 5개에 없던 질문: 'A01 의 가장 최근 PM 전후 7일 결함 수를 비교'.
Claude Code 가 자유 질문에 답할 때 이 모양(Session → src 조회 → 점검 → 표 → 가정 기록 → finish)을 따른다.
실행: python3 hub/examples/pm_before_after.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from engine.session import Session  # noqa: E402

EQP, DAYS = "A01", 7
s = Session(f"{EQP} 최근 PM 전후 {DAYS}일 결함 수 비교")
s.note(f"'최근 PM' = {EQP} 의 가장 마지막 PM 이력 시각")
s.note(f"'전/후' = PM 시각 기준 앞·뒤 {DAYS}일, 결함 수는 측정별 defect_count 의 평균")

pm = s.src.pm(eqps=[EQP]).sort_values("pm_ts")
last = pm["pm_ts"].iloc[-1]
start, end = last - pd.Timedelta(days=DAYS), min(last + pd.Timedelta(days=DAYS), s.src.as_of() + pd.Timedelta(days=1))
npw = s.src.npw([EQP], start, end)
s.table(npw, "npw_원본", time_col="ts", expected=(start, end), key=["measure_id"])

npw["구간"] = ["PM 후" if t >= last else "PM 전" for t in npw["ts"]]
res = npw.groupby("구간")["defect_count"].agg(측정수="count", 평균결함수="mean").round(1)
s.table(res, "결과")
if res["측정수"].min() < 3:
    s.note("경고: 한쪽 구간 측정이 3건 미만 — 결론 보류")
s.finish()
