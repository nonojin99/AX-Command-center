# 정기 모니터링 요약

## 흐름 (생성자 ≈9명 / 열람자 ≈21명)
```
BDQ 조회(승인 후) → metrics.csv → tools/monitoring_report.py(이상 판정, 코드) → 요약 md + 포털용 html
   → 담당 엔지니어가 '해석' 섹션 작성(Claude Code 사용자는 AI 초안 활용) → 저장소 push → 포털에 게시
```
- **계산은 코드, 해석은 사람/AI.** 수치 계산을 AI에게 맡기지 않는다.
- 열람자는 포털(Confluence/HTML)에서 읽기만 한다. Claude Code 가 없어도 된다.

## 시작하려면 채울 것
1. `config.json` — 실제 지표 이름, 단위, 나쁜 방향(`high_bad`/`low_bad`/`both`), 기준 기간·민감도(k).
2. `metrics.csv` — `date,metric,value` 3열. 조회 쿼리는 `defect/queries/` 규칙으로 별도 관리.
3. 지표별 정상 범위·조치 기준 문서(판단 기준표와 같은 방식).

## 실행 (가상 샘플)
```
python3 tools/monitoring_report.py monitoring/sample/sample_metrics.csv monitoring/config.json outputs/_example
```

## 알림·자동 실행
판정 결과가 바뀔 때만 한 통으로 묶어 메신저로 보낸다(`tools/alert.py`, 섀도 모드 → 라이브). 설정은 `SCHEDULING.md`.

## 기록·수치화 (질문 2번)
요약 md 는 날짜별로 `outputs/` 에 쌓이므로, 판정 이력(주의·이상 횟수, 해석 적중 여부)을 월 단위로 집계할 수 있다.
