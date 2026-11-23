#!/usr/bin/env python3
"""모니터링 수치 → 이상 판정(코드) → 요약 md + 포털용 html. 외부 패키지 없음.

사용: python3 tools/monitoring_report.py <metrics.csv> <config.json> <출력폴더>
CSV 형식: date,metric,value   (config.json 의 metrics 키와 metric 값이 같아야 함)
판정은 코드가 한다(최근값 vs 직전 baseline_days 일 평균·표준편차). AI/엔지니어는 '해석'만 쓴다.
"""
import csv
import html
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path


def load(csv_path):
    data = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            data[r["metric"]].append((r["date"], float(r["value"])))
    for v in data.values():
        v.sort()
    return data


def judge(series, cfg, conf):
    latest_date, latest = series[-1]
    base = [v for _, v in series[:-1]][-conf["baseline_days"]:]
    if len(base) < 3:
        return dict(date=latest_date, latest=latest, status="판정 불가", note="기준 기간 데이터 부족")
    mean, sd = st.mean(base), st.pstdev(base)
    z = (latest - mean) / sd if sd > 0 else 0.0
    bad = {"high_bad": z, "low_bad": -z, "both": abs(z)}[cfg["direction"]]
    status = "이상" if bad > conf["alert_k"] else "주의" if bad > conf["watch_k"] else "정상"
    return dict(date=latest_date, latest=latest, mean=mean, sd=sd, z=z, status=status, n=len(base))


def main(csv_path, cfg_path, out_dir):
    conf = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    data = load(csv_path)
    results = []
    for key, mcfg in conf["metrics"].items():
        if key not in data:
            results.append((mcfg, dict(status="데이터 없음", date="-", latest=float("nan"))))
            continue
        results.append((mcfg, judge(data[key], mcfg, conf)))
    date = max(r["date"] for _, r in results if r["date"] != "-")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    md = ["---", f"title: 모니터링 요약 {date}", "owner: 자동생성", "purpose: 정기 모니터링 이상 판정과 해석",
          "type: 보고서", "data_used: 가상샘플", "status: 초안", f"updated: {date}", "---", "",
          f"# 모니터링 요약 ({date})", "",
          f"판정 기준: 최근값이 직전 {conf['baseline_days']}일 평균에서 표준편차 {conf['watch_k']}배 초과 = 주의, "
          f"{conf['alert_k']}배 초과 = 이상 (계산은 코드가 수행).", "",
          "| 지표 | 최근값 | 기준 평균 | z | 판정 |", "|---|---|---|---|---|"]
    for m, r in results:
        if "mean" in r:
            md.append(f"| {m['label']} | {r['latest']}{m['unit']} | {r['mean']:.2f}{m['unit']} | {r['z']:+.1f} | {r['status']} |")
        else:
            md.append(f"| {m['label']} | - | - | - | {r['status']} |")
    flagged = [m["label"] for m, r in results if r["status"] in ("이상", "주의")]
    md += ["", "## 해석 (엔지니어 또는 AI 작성 — 근거와 확신도 필수)",
           f"- 주의/이상 지표: {', '.join(flagged) if flagged else '없음'}",
           "- 원인 후보: (작성)", "- 확인할 것: (작성)", "- 조치 필요 여부 (사람 결정): (작성)", ""]
    (out / f"monitoring_{date}.md").write_text("\n".join(md), encoding="utf-8")

    color = {"이상": "#c0392b", "주의": "#d68910", "정상": "#1e8449"}
    rows = "".join(
        f"<tr><td>{html.escape(m['label'])}</td><td>{r['latest']}{m['unit']}</td>"
        f"<td style='color:{color.get(r['status'], '#555')};font-weight:bold'>{r['status']}</td></tr>"
        for m, r in results)
    page = (f"<!doctype html><meta charset='utf-8'><title>모니터링 요약 {date}</title>"
            "<style>body{font-family:sans-serif;margin:24px}td,th{border:1px solid #ccc;padding:6px 12px}"
            "table{border-collapse:collapse}</style>"
            f"<h2>모니터링 요약 ({date})</h2><table><tr><th>지표</th><th>최근값</th><th>판정</th></tr>{rows}</table>"
            "<p>※ 판정은 코드 계산, 해석은 담당 엔지니어 확인 후 반영됩니다. (가상 샘플)</p>")
    (out / f"monitoring_{date}.html").write_text(page, encoding="utf-8")
    def num(v):
        return None if v is None or v != v else v

    summary = {"date": date, "metrics": {
        key: {"label": m["label"], "status": r["status"], "latest": num(r.get("latest")),
              "mean": num(r.get("mean")), "z": num(r.get("z"))}
        for key, (m, r) in zip(conf["metrics"], results)}}
    (out / f"monitoring_{date}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for m, r in results:
        print(f"{m['label']}: {r['status']}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
