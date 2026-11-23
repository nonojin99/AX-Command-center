# 자동 실행·알림 설정 (AI 없이 동작)

매일 정해진 시각에 `조회 → 판정 → 알림` 을 실행한다. Claude 는 이 경로에 없다(인증이 끊기면 멈추는 문제 회피).
AI 해석은 알림 링크로 들어온 담당자가 Claude Code 로 따로 붙인다.

## 0. 먼저 (필수)
1. **섀도 모드로 2주 운영**: `config.json` 의 `alert.mode` 가 `shadow` 이면 발송 없이 `monitoring/state/alert_log.jsonl` 에 '보냈을 알림'만 쌓인다.
   → 실제 문제였던 날과 비교해 `alert_k`·`watch_k`·`baseline_days` 를 조정한 뒤 `live` 로 바꾼다.
2. **웹훅 주소는 저장소에 쓰지 않는다.** 환경변수 `ALERT_WEBHOOK_URL`(이름은 `alert.webhook_env`)로만 준다.
   - GitHub: 저장소 Settings → Secrets 에 등록
   - Windows: 시스템 환경변수 또는 스케줄러를 실행하는 계정의 환경변수
3. **메일**: `alert.channels` 에 `"mail"` 을 넣고 `alert.mail`(SMTP 서버·포트·보내는/받는 주소)을 채운다. SMTP 계정이 필요하면 `SMTP_USER`·`SMTP_PASSWORD` 환경변수(GitHub Secrets 등)로 준다.
   웹훅·메일 중 하나만 쓰려면 `channels` 에서 뺀다. 한 채널이라도 실패하면 다음 실행에서 전체를 다시 시도한다(성공한 채널은 중복 발송될 수 있음).
4. 웹훅 본문은 `{"text": "..."}` JSON 이다. 사내 메신저가 다른 형식을 요구하면 `tools/alert.py` 의 `send()` 만 고친다.
5. 조회 단계(BDQ → csv)는 데이터 승인 후 `tools/` 에 추가한다 (지금은 샘플 csv).

## A. 사내 GitHub Actions (러너가 BDQ 에 접근 가능해야 함 — 보통 self-hosted)
`.github/workflows/monitoring.yml` (미검증 템플릿 — 사내 GitHub/러너 환경에서 확인 필요)
```yaml
name: monitoring
on:
  schedule:
    - cron: "0 22 * * *"     # UTC 22:00 = KST 07:00. 러너 시간대에 맞게 수정
  workflow_dispatch: {}
jobs:
  run:
    runs-on: [self-hosted]    # 사내 러너 라벨로 수정
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      # - name: fetch metrics   # 데이터 승인 후: BDQ 조회 → monitoring/metrics.csv
      - run: python3 tools/monitoring_report.py monitoring/sample/sample_metrics.csv monitoring/config.json outputs/_monitoring
      - run: python3 tools/alert.py "$(ls outputs/_monitoring/monitoring_*.json | tail -1)" monitoring/config.json monitoring/state/state.json
        env: { ALERT_WEBHOOK_URL: "${{ secrets.ALERT_WEBHOOK_URL }}" }
      - run: |   # 중복 억제 상태와 요약을 저장소에 보관 (러너는 매번 새로 뜨므로)
          python3 tools/build_index.py || true
          git config user.name monitoring-bot && git config user.email monitoring-bot@example.invalid
          git add outputs/_monitoring monitoring/state registry && git commit -m "monitoring $(date +%F)" && git push || true
```
- 주의: 알림 실패 시 `alert.py` 가 종료코드 1 → 워크플로 실패로 표시된다(그래야 조용히 빠지지 않는다).

## B. Windows 작업 스케줄러 (PC/서버 켜져 있어야 함)
`run_monitoring.bat`
```bat
@echo off
cd /d C:\ax-command-center
python tools\monitoring_report.py monitoring\metrics.csv monitoring\config.json outputs\_monitoring
for /f %%f in ('dir /b /o-n outputs\_monitoring\monitoring_*.json') do (set LATEST=%%f& goto :go)
:go
python tools\alert.py outputs\_monitoring\%LATEST% monitoring\config.json monitoring\state\state.json
```
등록 (관리자 명령 프롬프트):
```
schtasks /Create /SC DAILY /ST 07:00 /TN "monitoring" /TR "C:\ax-command-center\run_monitoring.bat"
```
- PC 가 꺼져 있거나 잠금·로그오프 상태면 실행되지 않을 수 있다 → 가능하면 상시 켜진 서버, 아니면 A안 권장.
- 실패 감시: 알림이 하루도 안 오면 '정상'인지 '실행 안 됨'인지 구분이 안 된다. 주 1회 "실행 확인" 메시지(heartbeat)를 별도로 보내는 것을 권장한다.
