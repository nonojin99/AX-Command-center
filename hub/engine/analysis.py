"""분석 함수 — 질문 하나 = 함수 하나. 데이터 소스(src)만 알고 DB 종류는 모른다.
계산은 전부 코드가 한다(LLM 이 숫자를 만들지 않는다). 결과는 DataFrame/dict 로 돌려준다.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SIG = json.loads((Path(__file__).parent.parent / "signatures.json").read_text(encoding="utf-8"))["element_to_part_type"]


def _window(src, months=None, days=None, as_of=None):
    as_of = as_of or src.as_of()
    end = as_of + pd.Timedelta(days=1)
    start = as_of - (pd.DateOffset(months=months) if months else pd.Timedelta(days=days))
    return start, end


def _edx_frame(src, eqps, start, end):
    npw = src.npw(eqps, start, end)
    edx = src.edx(npw["measure_id"]).merge(npw[["measure_id", "eqp_id", "ts"]], on="measure_id")
    return npw, edx


# 4-1. 공정의 NPW EDX 성분 최근 N개월 ------------------------------------------------------
def edx_composition(src, process, months=2, as_of=None):
    start, end = _window(src, months=months, as_of=as_of)
    eqps = src.eqp_master(process=process)["eqp_id"].tolist()
    npw, df = _edx_frame(src, eqps, start, end)
    df["month"] = df["ts"].dt.strftime("%Y-%m")

    def pivot(idx):
        return df.pivot_table(index=idx, columns="element", values="atomic_pct", aggfunc="mean").round(1)

    return dict(by_eqp=pivot("eqp_id"), by_month=pivot("month"), n_measure=len(npw),
                n_edx=int(df["defect_id"].nunique()), start=start, end=end)


# 4-2 / 4-4. 불량 의심 파트 ----------------------------------------------------------------
def _excess(src, eqp, peers, s, t):
    a = src.npw([eqp], s, t)["defect_count"]
    b = src.npw(peers, s, t)["defect_count"]
    return a.mean() - b.mean() if len(a) >= 3 and len(b) >= 3 else None


def _did(src, eqp, peers, install_ts, end, ba_days):
    """설치 전후 '같은 시기 동료 설비 대비 초과 결함 수' 의 변화 (difference-in-differences)."""
    t, d = pd.Timestamp(install_ts), pd.Timedelta(days=ba_days)
    after = _excess(src, eqp, peers, t, min(t + d, end))
    before = _excess(src, eqp, peers, t - d, t)
    return None if after is None or before is None else after - before


def suspect_parts(src, eqps, as_of=None, window_days=30, ba_days=20, recent_days=45,
                  w_sig=0.6, w_trend=0.4):
    """현재 장착 파트별 의심 점수 = w_sig*EDX 근거 + w_trend*설치 전후 증가.
    - EDX 근거: 최근 window_days 일 이 설비의 결함 성분 중, 파트 종류에 대응하는 원소(signatures.json)가
      동료 설비보다 얼마나 높은가(표준편차 단위, 0~3 을 0~1 로).
    - 설치 전후 증가: recent_days 이내 설치된 파트만. 설치 전후 ba_days 일의 '동료 대비 초과 결함 수' 증가분
      (SPEC 의 20% 이상 증가 = 1점).
    규칙 기반 1차 스크리닝이며 확정이 아니다. 가중치·기준은 인자로 조정한다."""
    as_of = as_of or src.as_of()
    end = as_of + pd.Timedelta(days=1)
    master = src.eqp_master()
    rows = []
    for e in eqps:
        grp = master.loc[master.eqp_id == e, "eqp_group"].iloc[0]
        peers = (master[(master.eqp_group == grp) & (master.eqp_id != e)].eqp_id.tolist()
                 or master[master.eqp_id != e].eqp_id.tolist())
        s = end - pd.Timedelta(days=window_days)
        _, mine = _edx_frame(src, [e], s, end)
        _, base = _edx_frame(src, peers, s, end)
        dev = {}
        for el in mine["element"].unique():
            m, b = mine.loc[mine.element == el, "atomic_pct"], base.loc[base.element == el, "atomic_pct"]
            dev[el] = float((m.mean() - b.mean()) / (b.std() or 1)) if len(b) > 1 else 0.0
        spec = float(src.npw([e], s, end)["spec_upper"].max() or 50)
        for _, p in src.parts([e], installed_only=True).iterrows():
            els = [el for el, pts in SIG.items() if p.part_type in pts]
            best = max(els, key=lambda el: dev.get(el, -9), default=None)
            d = dev.get(best, 0.0) if best else 0.0
            sig = float(np.clip(d, 0, 3) / 3)
            age = (as_of - pd.Timestamp(p.install_ts).normalize()).days
            did = _did(src, e, peers, p.install_ts, end, ba_days) if age <= recent_days else None
            trend = float(np.clip(did / (0.2 * spec), 0, 1)) if did is not None else 0.0
            score = w_sig * sig + w_trend * trend
            rows.append({"설비": e, "파트ID": p.part_id, "파트종류": p.part_type, "설치일": pd.Timestamp(p.install_ts).date(),
                         "경과일": age,
                         "EDX 근거": f"{best} 동료 대비 {d:+.1f}σ" if best else "대응 원소 없음",
                         "설치 전후 초과 결함 증가": None if did is None else round(float(did), 1),
                         "의심점수": round(score, 2),
                         "의심도": "높음" if score >= 0.6 else "중간" if score >= 0.3 else "낮음",
                         "비고": "" if did is not None else ("설치 후 기간 짧음/데이터 부족" if age <= recent_days else f"설치 {recent_days}일 초과 — 전후 비교 안 함")})
    return pd.DataFrame(rows).sort_values("의심점수", ascending=False).reset_index(drop=True)


# 4-3. 공정별 월별 PM 주기 ------------------------------------------------------------------
def pm_cycle_stats(src, processes, as_of=None, months=6):
    start, _ = _window(src, months=months, as_of=as_of)
    pm = src.pm(processes=processes).sort_values(["eqp_id", "pm_ts"])
    pm["interval_days"] = pm.groupby("eqp_id")["pm_ts"].diff().dt.days
    ev = pm.dropna(subset=["interval_days"])
    ev = ev[ev["pm_ts"] >= start].copy()
    ev["month"] = ev["pm_ts"].dt.strftime("%Y-%m")
    monthly = (ev.groupby(["process", "month"])["interval_days"]
               .agg(PM횟수="count", 평균주기="mean", 최소="min", 최대="max").round(1).reset_index())
    return dict(events=ev, monthly=monthly)


# 4-5. 이번 주 SPEC OVER ---------------------------------------------------------------------
def spec_over_week(src, as_of=None):
    start, end = _window(src, days=7, as_of=as_of)
    eqps = src.eqp_master()["eqp_id"].tolist()
    npw = src.npw(eqps, start, end)
    over = npw[npw["defect_count"] > npw["spec_upper"]].sort_values("defect_count", ascending=False)
    defects = src.defects(over["measure_id"])
    edx = src.edx(over["measure_id"]).merge(over[["measure_id", "eqp_id"]], on="measure_id")
    comp = edx.groupby("element")["atomic_pct"].mean().round(1).sort_values(ascending=False)
    by_eqp = (over.groupby("eqp_id").agg(건수=("measure_id", "count"), 최대결함수=("defect_count", "max"),
                                         평균결함수=("defect_count", "mean")).round(1).reset_index())
    return dict(start=start, end=end, total=len(npw), over=over, defects=defects, composition=comp, by_eqp=by_eqp)
