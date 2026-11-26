---
name: monitoring-summary
description: 모니터링 수치(csv)로 이상 판정 요약을 만들고 '해석' 초안을 작성한다. "모니터링 요약", "오늘 지표 정리" 요청에 사용.
---

# monitoring-summary

1. `monitoring/config.json` 과 입력 csv(`date,metric,value`)를 확인한다. 지표가 config 에 없으면 추가하지 말고 질문한다.
2. 수치 판정은 직접 계산하지 말고 `python3 tools/monitoring_report.py <csv> monitoring/config.json outputs/<소유자>` 를 실행한다.
3. 생성된 md 의 '해석' 섹션만 채운다: 주의/이상 지표별로 **근거(어떤 수치가 기준 대비 어땠는지)·원인 후보·확신도·확인할 것**. 근거가 없으면 "근거 부족".
4. 조치 필요 여부는 쓰지 않고 `(사람 결정)` 으로 남긴다. 상태는 `초안` 유지.
5. `python3 tools/build_index.py` 로 INDEX 갱신.
