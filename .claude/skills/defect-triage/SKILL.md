---
name: defect-triage
description: 불량 관련 메일을 받으면 intake 스키마로 정리하고, 판단 기준표에 따라 확인할 재료 목록과 분석 패키지 초안을 만든다. "불량 메일 정리", "분석 패키지 만들어줘" 요청에 사용.
---

# defect-triage

1. 메일 본문을 `defect/intake-schema.md` 항목으로 구조화한다. 없는 값은 `미기재`.
2. `defect/judgment-criteria.md` 에서 해당 불량 유형 블록을 찾는다. 없으면 **만들지 말고** "판단 기준 없음 — 엔지니어가 먼저 채워야 함"이라고 알린다.
3. 기준표의 "반드시 확인할 데이터"를 체크리스트로 만든다. 쿼리가 `defect/queries/` 에 있으면 어떤 파일을 돌려야 하는지 안내한다(데이터 접근이 안 되는 환경에서는 실행하지 않는다).
4. `defect/analysis-package-template.md` 형식으로 초안을 `outputs/<소유자>/` 에 저장한다. 머리말 `status: 초안`.
5. 원인 후보에는 근거와 확신도를 반드시 쓰고, 근거가 없으면 "근거 부족"으로 둔다. 최종 판단은 사람이 한다.
6. 마지막에 `python3 tools/build_index.py` 를 실행해 INDEX 를 갱신한다.
