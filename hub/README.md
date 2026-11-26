# 분석 허브 (Streamlit) — 가상 데이터 골격

"설비·공정 질문 → 여러 DB 조인 → 분석·차트·보고서"를 한 화면에서. **지금은 가상 데이터**로 돌아가며,
실제 BDQ 에는 `engine/sources.py` 의 `BDQSource` 만 채우면 연결된다(분석 코드는 그대로).

## 실행 / 테스트
```
pip install streamlit plotly pandas openpyxl
streamlit run hub/app.py
python3 hub/tests/test_engine.py        # 엔진 + 화면 스모크 테스트
```

## 질문 5개 → 기능
| 질문 | 탭 / 함수 |
|---|---|
| ㄱ공정 NPW EDX 성분 최근 2달 | ① `analysis.edx_composition` |
| ㄴ설비군 장착 파트 중 불량 의심 | ② `analysis.suspect_parts` (설비군 전체) |
| ㄱ·ㄴ·ㄷ 공정 월별 PM 주기 | ③ `analysis.pm_cycle_stats` |
| A설비 NPW 추세 불량 → EDX 로 파트 유추 | ④ 추세(PM 표시) + `suspect_parts` (한 설비) |
| 이번 주 SPEC OVER MAP·성분·보고서 | ⑤ `analysis.spec_over_week` + `report` (md·엑셀) |

## 구조
```
app.py                  폼 화면(탭 5개). 나중에 챗 입력창이 이 폼의 값을 채움
engine/sources.py       데이터 소스 인터페이스 — SyntheticSource(가상) / BDQSource(미구현, 실제 연결 자리)
engine/analysis.py      분석 함수 (계산은 전부 코드)
engine/charts.py        plotly 차트        engine/report.py  보고서·엑셀
engine/synth.py         가상 데이터 + 표 구조 설명(실제 DB 1·2·3 에 대응시킬 컬럼)
signatures.json         EDX 원소 ↔ 파트 종류 대응표 (예시값 — 엔지니어가 실제 재질로 교체)
```

## 실제 데이터 연결 순서
1. `synth.py` 상단 설명의 표 6개를 실제 DB 의 테이블·컬럼과 대응시킨다(조인 키: measure_id, 설비+시각).
2. `BDQSource` 를 구현 — 같은 메서드·같은 컬럼명으로 DataFrame 반환, 쿼리는 파라미터 바인딩·읽기 전용 계정.
3. `signatures.json` 을 실제 파트 재질/검출 원소로 교체, `suspect_parts` 의 가중치·기준을 실데이터로 보정.
4. `app.py` 의 `SyntheticSource()` 를 `BDQSource()` 로 교체.

## 한계 (꼭 읽을 것)
- 가상 데이터에는 **A01 LINER 문제를 심어 두었다.** 테스트가 이를 찾는 것은 로직이 돌아간다는 확인일 뿐,
  실제 데이터에서의 정확도를 보장하지 않는다. 오탐 확인용으로 문제 없는 설비군(ㄴ)에서 '높음'이 안 나오는지도 테스트한다.
- `suspect_parts` 는 규칙 기반 **1차 스크리닝**이다(EDX 원소 편차 60% + 설치 전후 초과 결함 40%). 확정 판정이 아니다.
- 챗(자연어) 입력, PPT 생성, 사용 로그/피드백은 아직 없다.
