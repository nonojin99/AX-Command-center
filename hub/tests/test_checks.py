"""실행: python3 hub/tests/test_checks.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from engine import checks  # noqa: E402

# 다대다 조인은 예외
l = pd.DataFrame({"k": [1, 2, 2], "a": [1, 2, 3]})
r = pd.DataFrame({"k": [1, 2, 2], "b": [1, 2, 3]})
try:
    checks.safe_merge(l, r, "k")
    raise AssertionError("다대다 조인이 막히지 않음")
except pd.errors.MergeError:
    pass

# 매칭 안 되는 행 경고
checks.WARNINGS.clear()
checks.safe_merge(pd.DataFrame({"k": range(10)}), pd.DataFrame({"k": [0], "b": [1]}), "k")
assert any("매칭 안 됨" in w for w in checks.WARNINGS), checks.WARNINGS

# 결측 / 시간 범위 / 공백 / 빈 결과
checks.WARNINGS.clear()
df = pd.DataFrame({"ts": pd.date_range("2026-01-01", periods=3), "v": [None, None, 1.0]})
checks.check_df(df, "t", time_col="ts", expected=("2026-02-01", "2026-03-01"))
checks.check_df(df.iloc[0:0], "빈표")
assert len(checks.WARNINGS) >= 4, checks.WARNINGS

# 정상 표는 경고 없음
checks.WARNINGS.clear()
ok = pd.DataFrame({"ts": pd.date_range("2026-01-01", periods=30), "v": range(30)})
checks.check_df(ok, "ok", time_col="ts", expected=("2026-01-01", "2026-01-31"), key=["ts"])
assert not checks.WARNINGS, checks.WARNINGS
print("점검 모듈 테스트 통과")
