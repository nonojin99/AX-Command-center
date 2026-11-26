"""차트 (plotly). 데이터 가공은 analysis.py 가 끝낸 뒤 그리기만 한다."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def trend_with_pm(npw, pm, spec, title):
    fig = px.line(npw.sort_values("ts"), x="ts", y="defect_count", markers=True, title=title,
                  labels={"ts": "측정일", "defect_count": "결함 수"})
    fig.add_hline(y=spec, line_dash="dash", line_color="red")
    for t in pm["pm_ts"]:
        fig.add_shape(type="line", x0=t, x1=t, y0=0, y1=1, yref="paper", line=dict(dash="dot", color="gray"))
    return fig


def composition_bar(df, title, barmode="group"):
    long = df.reset_index().melt(id_vars=df.index.name or "index", var_name="element", value_name="atomic_pct")
    return px.bar(long, x="element", y="atomic_pct", color=df.index.name or "index", barmode=barmode,
                  title=title, labels={"atomic_pct": "평균 atomic %", "element": "원소"})


def wafer_map(defects, title="SPEC OVER 웨이퍼 결함 MAP (합산)", radius=150):
    fig = px.scatter(defects, x="x", y="y", opacity=0.35, title=title)
    t = np.linspace(0, 2 * np.pi, 200)
    fig.add_trace(go.Scatter(x=radius * np.cos(t), y=radius * np.sin(t), mode="lines", line=dict(color="gray"), showlegend=False))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def pm_box(events, title="PM 주기 (일)"):
    return px.box(events, x="process", y="interval_days", color="eqp_id", points="all", title=title,
                  labels={"interval_days": "PM 간격(일)", "process": "공정"})
