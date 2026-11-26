"""결과 자동 점검 — 유연한 분석에서 '조용히 틀리는' 것(조인 부풀림, 결측, 기간 어긋남)을 잡는다.
경고는 WARNINGS 에 쌓이고 Session.finish() 가 기록에 남긴다. 점검 통과 = 맞다는 뜻이 아니다(명백한 실수만 잡는다).
"""
import pandas as pd

WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print(f"⚠ {msg}")


def safe_merge(left, right, on, how="left", validate="m:1", name=""):
    """pandas merge + 행 수·매칭률 점검.
    validate 기본 'm:1' = right 의 키가 유일해야 함(어기면 예외). 의도적으로 다대다면 명시적으로 지정한다.
    left 기준 매칭 안 된 행이 5% 넘으면 경고, inner 로 20% 넘게 사라지면 경고."""
    n0 = len(left)
    out = left.merge(right, on=on, how=how, validate=validate, indicator=True)
    label = name or f"merge on {on}"
    if how == "left":
        miss = int((out["_merge"] == "left_only").sum())
        if n0 and miss / n0 > 0.05:
            warn(f"{label}: left {n0}행 중 {miss}행({miss / n0:.0%}) 매칭 안 됨")
    elif how == "inner" and n0 and 1 - len(out) / n0 > 0.2:
        warn(f"{label}: inner 조인으로 {n0}→{len(out)}행 ({1 - len(out) / n0:.0%} 사라짐)")
    if len(out) > n0 and validate in ("m:1", "1:1"):
        warn(f"{label}: 조인 후 행이 늘었습니다 {n0}→{len(out)} (키 중복 의심)")
    return out.drop(columns="_merge")


def check_df(df, name, time_col=None, expected=None, key=None, max_rows=1_000_000):
    """표 하나를 점검한다. expected=(start, end) 를 주면 시간 범위가 요청과 맞는지 본다. key 는 중복 확인용 컬럼 리스트."""
    if df is None or len(df) == 0:
        warn(f"{name}: 결과가 비어 있습니다")
        return
    if len(df) > max_rows:
        warn(f"{name}: {len(df)}행 — 너무 큽니다(집계 후 사용 권장)")
    nulls = df.isna().mean()
    for col, r in nulls[nulls > 0.3].items():
        warn(f"{name}.{col}: 결측 {r:.0%}")
    if key is not None and df.duplicated(subset=key).any():
        warn(f"{name}: 키 {key} 중복 {int(df.duplicated(subset=key).sum())}행")
    if time_col is not None and expected is not None:
        s, e = pd.Timestamp(expected[0]), pd.Timestamp(expected[1])
        t = pd.to_datetime(df[time_col])
        if t.min() < s or t.max() > e:
            warn(f"{name}: 시간 범위 {t.min():%Y-%m-%d}~{t.max():%Y-%m-%d} 가 요청 {s:%Y-%m-%d}~{e:%Y-%m-%d} 밖으로 나갑니다")
        days_req = max((e - s).days, 1)
        days_have = t.dt.normalize().nunique()
        if days_have < days_req * 0.3:
            warn(f"{name}: 요청 {days_req}일 중 데이터 있는 날 {days_have}일 — 공백이 큽니다")
