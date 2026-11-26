"""가상 데이터 — 실제 데이터가 아니다. 키·컬럼 구조만 실제 DB 와 비슷하게 흉내 낸다.

테이블(실제 DB 1·2·3 에 대응시킬 자리):
  eqp_master  설비 마스터            (eqp_id, process, eqp_group)
  npw         NPW 측정(웨이퍼 단위)   (measure_id, ts, eqp_id, wafer_id, defect_count, spec_upper)
  npw_defect  측정별 결함 좌표(MAP)   (measure_id, defect_id, x, y)
  edx         결함별 EDX 성분(long)   (measure_id, defect_id, element, atomic_pct)
  pm          PM 이력                (eqp_id, process, pm_ts, pm_type)
  parts       파트 장착 이력          (eqp_id, part_id, part_type, install_ts, remove_ts[비어 있으면 현재 장착])
공통 조인 키: measure_id (npw↔npw_defect↔edx), eqp_id + 시각 (npw↔pm↔parts)

심어 둔 시나리오: A01 설비는 마지막 PM 때 LINER 를 교체했고, 그 뒤 결함 수가 늘고 EDX 에서 Al 이 높다.
(분석 로직이 이를 찾아내는지 확인하는 용도. 실제 데이터에서는 이런 관계를 가정하지 않는다.)
"""
import numpy as np
import pandas as pd

AS_OF = pd.Timestamp("2026-11-26")
PROCESSES = {"ㄱ": ["A01", "A02"], "ㄴ": ["B01", "B02", "B03"], "ㄷ": ["C01", "C02"]}
PM_DAYS = {"ㄱ": 30, "ㄴ": 40, "ㄷ": 35}
PART_TYPES = ["LINER", "ELECTRODE", "O_RING", "SHOWERHEAD"]
ELEMENTS = ["Si", "O", "C", "Al", "Fe", "Y"]
BASE_ALPHA = np.array([6, 6, 3, 1, 1, 0.5])
SPEC = 50
FAULT = dict(eqp="A01", part_type="LINER", element="Al", extra_defects=25)


def make_data(seed=7):
    rng = np.random.default_rng(seed)
    start = AS_OF - pd.Timedelta(days=180)
    master, pm, parts, npw, defects, edx = [], [], [], [], [], []
    mid = did = 0
    for proc, eqps in PROCESSES.items():
        for e in eqps:
            master.append(dict(eqp_id=e, process=proc, eqp_group=f"{proc}설비군"))
            # PM 일정: 마지막 PM 에서 거꾸로 만든다
            last = AS_OF - pd.Timedelta(days=18 if e == FAULT["eqp"] else int(rng.integers(3, PM_DAYS[proc])))
            pms = [last]
            while pms[-1] > start:
                pms.append(pms[-1] - pd.Timedelta(days=int(PM_DAYS[proc] + rng.integers(-5, 6))))
            pms = sorted(pms)
            pm += [dict(eqp_id=e, process=proc, pm_ts=t, pm_type="정기") for t in pms]

            # 파트: PM 마다 한 종류씩 교체
            serial = {pt: 0 for pt in PART_TYPES}
            cur = {pt: dict(eqp_id=e, part_id=f"P-{e}-{pt}-0", part_type=pt,
                            install_ts=pms[0] - pd.Timedelta(days=90), remove_ts=pd.NaT) for pt in PART_TYPES}
            fault_install = None
            for i, t in enumerate(pms[1:], 1):
                is_fault = e == FAULT["eqp"] and i == len(pms) - 1
                pt = FAULT["part_type"] if is_fault else PART_TYPES[int(rng.integers(0, len(PART_TYPES)))]
                cur[pt]["remove_ts"] = t
                parts.append(cur[pt])
                serial[pt] += 1
                cur[pt] = dict(eqp_id=e, part_id=f"P-{e}-{pt}-{serial[pt]}", part_type=pt, install_ts=t, remove_ts=pd.NaT)
                if is_fault:
                    fault_install = t
            parts += list(cur.values())

            # NPW 측정: PM 뒤 시간이 지날수록 서서히 증가 + (A01 은 교체 파트 뒤 급증)
            for day in pd.date_range(start, AS_OF, freq="D"):
                if rng.random() > 0.8:
                    continue
                ts = day + pd.Timedelta(hours=int(rng.integers(0, 24)))
                prev = [p for p in pms if p <= ts]
                dsp = (ts - prev[-1]).days if prev else 10
                faulty = fault_install is not None and ts >= fault_install
                cnt = max(0, int(round(20 + 0.5 * dsp + rng.normal(0, 3) + (FAULT["extra_defects"] if faulty else 0))))
                mid += 1
                npw.append(dict(measure_id=mid, ts=ts, eqp_id=e, wafer_id=f"W{mid:05d}", defect_count=cnt, spec_upper=SPEC))
                m = min(cnt, 120)
                r = 150 * np.sqrt(rng.random(m))
                if faulty:  # 결함이 가장자리에 몰림
                    edge = rng.random(m) < 0.6
                    r[edge] = rng.uniform(120, 150, int(edge.sum()))
                th = rng.uniform(0, 2 * np.pi, m)
                ids = np.arange(did + 1, did + m + 1)
                did += m
                defects.append(pd.DataFrame(dict(measure_id=mid, defect_id=ids,
                                                 x=(r * np.cos(th)).round(1), y=(r * np.sin(th)).round(1))))
                alpha = BASE_ALPHA.copy()
                if faulty:
                    alpha[ELEMENTS.index(FAULT["element"])] = 8
                for d_id in ids[:3]:  # 측정당 3개 결함만 EDX 분석
                    edx.append(pd.DataFrame(dict(measure_id=mid, defect_id=d_id, element=ELEMENTS,
                                                 atomic_pct=(rng.dirichlet(alpha) * 100).round(2))))
    return dict(eqp_master=pd.DataFrame(master), npw=pd.DataFrame(npw), npw_defect=pd.concat(defects, ignore_index=True),
                edx=pd.concat(edx, ignore_index=True), pm=pd.DataFrame(pm), parts=pd.DataFrame(parts))
