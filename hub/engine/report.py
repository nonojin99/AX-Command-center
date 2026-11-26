"""보고서(markdown)와 엑셀 생성. 문장은 템플릿이고 숫자는 분석 결과에서 그대로 가져온다."""
import io

import pandas as pd


def _md(df, index=False):
    """의존성 없는 markdown 표."""
    d = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns)
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in d.itertuples(index=False)]
    return "\n".join([head, *rows])


def spec_over_markdown(res, suspects=None):
    s, e = res["start"].date(), (res["end"] - pd.Timedelta(days=1)).date()
    over = res["over"]
    lines = [f"# 주간 SPEC OVER 보고 ({s} ~ {e})", "",
             f"- 측정 {res['total']}건 중 SPEC 초과 **{len(over)}건** ({len(over) / max(res['total'], 1):.0%})", ""]
    if over.empty:
        return "\n".join(lines + ["SPEC 초과 항목 없음."])
    lines += ["## 설비별", "", _md(res["by_eqp"]), "", "## 초과 항목 성분 (평균 atomic %)", "",
              _md(res["composition"].to_frame("atomic %"), index=True), "",
              f"- 가장 높은 성분: **{res['composition'].index[0]}** ({res['composition'].iloc[0]}%)"]
    if suspects is not None and not suspects.empty:
        top = suspects.iloc[0]
        lines += ["", "## 불량 의심 파트 (1차 스크리닝)", "",
                  f"- 최상위: {top['설비']} {top['파트ID']} ({top['파트종류']}), 의심도 {top['의심도']} — {top['EDX 근거']}"]
    lines += ["", "> 자동 집계 결과입니다(코드 계산). 원인 해석과 조치 여부는 담당 엔지니어가 확인 후 결정합니다. "
              "상태: 초안."]
    return "\n".join(lines)


def to_excel(sheets):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name[:31], index=not isinstance(df.index, pd.RangeIndex))
    return buf.getvalue()
