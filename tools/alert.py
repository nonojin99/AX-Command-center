#!/usr/bin/env python3
"""판정 결과(json) → 상태가 '바뀐' 것만 한 통으로 묶어 메신저 웹훅 발송. AI 없음, 외부 패키지 없음, Windows/Linux 동일.

사용: python3 tools/alert.py <monitoring_날짜.json> <config.json> <state.json> [--mode shadow|live] [--dry-run]

- shadow: 발송하지 않고 monitoring/state/alert_log.jsonl 에 '보냈을 내용'만 기록 (임계값 보정용 2주 운영)
- live  : config 의 alert.channels(["webhook"], ["mail"], 둘 다 가능)로 발송.
          웹훅 주소·SMTP 계정은 환경변수로만 준다(저장소에 쓰지 않는다)
- --dry-run: 메시지를 화면에만 출력, 상태 파일·로그를 건드리지 않는다 (테스트용)
- 중복 억제: 이전 상태와 같으면 보내지 않는다. 발송 실패 시 상태를 저장하지 않아 다음 실행에서 다시 시도한다.
"""
import argparse
import json
import os
import smtplib
import sys
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

DATA_PROBLEM = ("판정 불가", "데이터 없음")


def build_message(summary, alert_conf, state):
    new_state, alerts, watches, recovers, data = {}, [], [], [], []
    for key, m in summary["metrics"].items():
        status, prev = m["status"], state.get(key, "정상")
        new_state[key] = status
        if status == prev:
            continue
        detail = ""
        if m.get("mean") is not None:
            detail = f" (최근 {m['latest']}, 기준 평균 {m['mean']:.2f}, z={m['z']:+.1f})"
        line = f"- {m['label']}: {prev} → {status}{detail}"
        if status == "이상":
            alerts.append(line)
        elif status == "주의":
            watches.append(line)
        elif status == "정상":
            recovers.append(line)
        elif status in DATA_PROBLEM:
            data.append(line)
    if not (alerts or watches or recovers or data):
        return None, new_state
    head = f"[모니터링] {summary['date']} " + (f"이상 {len(alerts)}건" if alerts else "상태 변경")
    parts = [head]
    for title, lines in (("🔴 이상", alerts), ("🟠 주의", watches), ("⚠ 데이터 확인", data), ("🟢 회복", recovers)):
        if lines:
            parts += [title, *lines]
    parts += [f"담당: {alert_conf.get('owner', '-')}", f"상세·해석: {alert_conf.get('portal_url', '-')}",
              "※ 자동 판정(코드 계산)입니다. 원인 해석과 조치 여부는 담당자가 결정합니다."]
    return "\n".join(parts), new_state


def send(url, text):
    req = urllib.request.Request(url, data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"webhook status {resp.status}")


def send_mail(text, mc):
    """사내 SMTP 로 발송. 계정이 필요하면 mc.user_env / mc.password_env 가 가리키는 환경변수를 쓴다."""
    msg = EmailMessage()
    msg["Subject"] = text.splitlines()[0]
    msg["From"] = mc["from"]
    msg["To"] = ", ".join(mc["to"])
    msg.set_content(text)
    with smtplib.SMTP(mc["smtp_host"], int(mc.get("smtp_port", 25)), timeout=15) as s:
        if mc.get("starttls"):
            s.starttls()
        user = os.environ.get(mc.get("user_env", ""), "")
        if user:
            s.login(user, os.environ.get(mc.get("password_env", ""), ""))
        s.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("config")
    ap.add_argument("state")
    ap.add_argument("--mode", choices=["shadow", "live"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    conf = json.loads(Path(a.config).read_text(encoding="utf-8"))
    ac = conf.get("alert", {})
    mode = a.mode or ac.get("mode", "shadow")
    summary = json.loads(Path(a.summary).read_text(encoding="utf-8"))
    sp = Path(a.state)
    state = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}

    text, new_state = build_message(summary, ac, state)
    if text is None:
        print("상태 변경 없음 — 알림 없음")
        if not a.dry_run:
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    if a.dry_run:
        print(f"[dry-run, mode={mode}]\n{text}")
        return 0
    if mode == "live":
        failed = []
        for ch in ac.get("channels", ["webhook"]):
            try:
                if ch == "webhook":
                    url = os.environ.get(ac.get("webhook_env", "ALERT_WEBHOOK_URL"))
                    if not url:
                        raise RuntimeError("웹훅 환경변수 없음")
                    send(url, text)
                elif ch == "mail":
                    send_mail(text, ac.get("mail", {}))
                else:
                    raise RuntimeError(f"알 수 없는 채널 {ch}")
                print(f"{ch} 발송 완료")
            except Exception as e:
                failed.append(ch)
                print(f"{ch} 발송 실패: {e}", file=sys.stderr)
        if failed:  # 하나라도 실패하면 상태를 저장하지 않아 다음 실행에서 다시 시도(성공한 채널은 중복 발송될 수 있음)
            return 1
    else:
        log = sp.parent / "alert_log.jsonl"
        sp.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"),
                                "date": summary["date"], "would_send": text}, ensure_ascii=False) + "\n")
        print(f"shadow 모드 — 발송하지 않고 {log} 에 기록")
    sp.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
