"""분석 허브 (Streamlit) — 폼 화면. 실행: streamlit run hub/app.py
질문 5개 = 탭 5개. LLM 없이 동작한다(나중에 챗 입력창이 이 폼의 값을 채워 주는 역할을 한다).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from engine import analysis as an  # noqa: E402
from engine import charts, report  # noqa: E402
from engine.sources import SyntheticSource  # noqa: E402

st.set_page_config(page_title="분석 허브 (가상 데이터)", layout="wide")


@st.cache_resource
def get_src():
    return SyntheticSource()  # 실제 연결 시: BDQSource()


src = get_src()
master = src.eqp_master()
st.title("분석 허브")
st.warning(f"데이터 소스: {src.name} — 실제 DB 연결 전 골격입니다. 판단은 담당 엔지니어가 확인합니다.", icon="⚠️")


def show_log():
    with st.expander("사용한 조회 (근거)"):
        for line in src.log:
            st.write("•", line)


def run(fn, *a, **k):
    src.log.clear()
    return fn(src, *a, **k)


t1, t2, t3, t4, t5 = st.tabs(["① 성분(EDX) 분석", "② 설비군 불량 의심 파트", "③ PM 주기", "④ 설비 원인 추정", "⑤ SPEC OVER 주간 보고서"])

with t1:
    c1, c2 = st.columns(2)
    proc = c1.selectbox("공정", master["process"].unique(), key="p1")
    months = c2.slider("최근 N개월", 1, 6, 2, key="m1")
    if st.button("분석", key="b1"):
        r = run(an.edx_composition, proc, months)
        st.caption(f"{r['start']:%Y-%m-%d} ~ {r['end']:%Y-%m-%d}, 측정 {r['n_measure']}건, EDX 결함 {r['n_edx']}개")
        st.plotly_chart(charts.composition_bar(r["by_eqp"], "설비별 평균 성분"), width="stretch")
        st.plotly_chart(charts.composition_bar(r["by_month"], "월별 평균 성분"), width="stretch")
        st.dataframe(r["by_eqp"])
        show_log()

with t2:
    grp = st.selectbox("설비군", master["eqp_group"].unique(), key="g2")
    if st.button("검사", key="b2"):
        eqps = master.loc[master.eqp_group == grp, "eqp_id"].tolist()
        res = run(an.suspect_parts, eqps)
        st.dataframe(res, hide_index=True)
        st.caption("규칙 기반 1차 스크리닝: EDX 원소 편차(60%) + 설치 전후 초과 결함 증가(40%). 확정이 아닙니다. "
                   "원소↔파트 대응은 hub/signatures.json (예시값).")
        show_log()

with t3:
    procs = st.multiselect("공정", master["process"].unique().tolist(), default=master["process"].unique().tolist(), key="p3")
    if st.button("분석", key="b3") and procs:
        r = run(an.pm_cycle_stats, procs)
        st.plotly_chart(charts.pm_box(r["events"]), width="stretch")
        st.dataframe(r["monthly"], hide_index=True)
        show_log()

with t4:
    eqp = st.selectbox("설비", master["eqp_id"], key="e4")
    if st.button("추정", key="b4"):
        src.log.clear()
        end = src.as_of() + pd.Timedelta(days=1)
        npw = src.npw([eqp], end - pd.Timedelta(days=120), end)
        pm = src.pm(eqps=[eqp])
        pm = pm[pm.pm_ts >= end - pd.Timedelta(days=120)]
        st.plotly_chart(charts.trend_with_pm(npw, pm, float(npw["spec_upper"].max()), f"{eqp} NPW 결함 수 추세 (점선=PM, 빨간선=SPEC)"), width="stretch")
        st.dataframe(an.suspect_parts(src, [eqp]), hide_index=True)
        comp = an.edx_composition(src, master.loc[master.eqp_id == eqp, "process"].iloc[0], 1)["by_eqp"]
        st.plotly_chart(charts.composition_bar(comp, "같은 공정 설비별 최근 1개월 성분 비교"), width="stretch")
        show_log()

with t5:
    if st.button("이번 주 보고서 만들기", key="b5"):
        src.log.clear()
        w = an.spec_over_week(src)
        sus = an.suspect_parts(src, w["by_eqp"]["eqp_id"].unique().tolist()) if not w["over"].empty else None
        md = report.spec_over_markdown(w, sus)
        st.markdown(md)
        if not w["over"].empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(charts.wafer_map(w["defects"]), width="stretch")
            c2.plotly_chart(charts.composition_bar(w["composition"].to_frame("SPEC OVER").T.rename_axis("구분"), "초과 항목 성분"), width="stretch")
            st.dataframe(w["over"], hide_index=True)
            sheets = {"SPEC_OVER": w["over"], "설비별": w["by_eqp"], "성분": w["composition"].to_frame("atomic_pct")}
            if sus is not None:
                sheets["의심파트"] = sus
            st.download_button("엑셀 다운로드", report.to_excel(sheets), "spec_over_week.xlsx", on_click="ignore")
        st.download_button("보고서(.md) 다운로드", md, "spec_over_week.md", on_click="ignore")
        show_log()
