#!/usr/bin/env python3
"""outputs/ 아래 .md 파일의 머리말을 읽어 registry/INDEX.md 를 만든다. 외부 패키지 없음."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["title", "owner", "type", "status", "data_used", "updated", "purpose"]


def read_header(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return None


def main():
    rows, missing = [], []
    for p in sorted((ROOT / "outputs").rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        meta = read_header(p)
        if not meta or any(not meta.get(k) for k in FIELDS):
            missing.append(rel)
            continue
        rows.append((rel, meta))
    out = ["# 산출물 목록 (자동 생성 — 직접 수정 금지)", "",
           "| 제목 | 소유자 | 유형 | 상태 | 데이터 | 갱신 | 목적 |", "|---|---|---|---|---|---|---|"]
    for rel, m in sorted(rows, key=lambda r: r[1]["updated"], reverse=True):
        out.append(f"| [{m['title']}](../{rel}) | {m['owner']} | {m['type']} | {m['status']} | "
                   f"{m['data_used']} | {m['updated']} | {m['purpose']} |")
    (ROOT / "registry" / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"INDEX 갱신: {len(rows)}건")
    if missing:
        print("머리말 없음/누락 (INDEX 제외):")
        for rel in missing:
            print("  -", rel)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
