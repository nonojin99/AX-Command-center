"""데이터 소스 계층 — 분석 코드는 이 인터페이스만 부른다. 실제 BDQ 연결은 BDQSource 만 채우면 된다.

모든 메서드는 pandas DataFrame 을 돌려주고, 무엇을 조회했는지 self.log 에 남긴다(화면에 '사용한 조회'로 보여 줌).
컬럼 이름은 synth.py 의 표를 따른다 — 실제 테이블 컬럼이 다르면 BDQSource 안에서 이름만 맞춰 돌려준다(어댑터).
"""
import pandas as pd

from .synth import make_data


def _as_list(x):
    return list(x) if hasattr(x, "__iter__") and not isinstance(x, str) else [x]


class SyntheticSource:
    name = "가상 데이터 (실제 데이터 아님)"

    def __init__(self):
        self._t = make_data()
        self.log = []

    def as_of(self):
        return self._t["npw"]["ts"].max().normalize()

    def eqp_master(self, process=None, group=None):
        df = self._t["eqp_master"]
        if process is not None:
            df = df[df["process"].isin(_as_list(process))]
        if group is not None:
            df = df[df["eqp_group"].isin(_as_list(group))]
        return df.reset_index(drop=True)

    def npw(self, eqps, start, end):
        self.log.append(f"NPW 측정: 설비 {_as_list(eqps)}, {start:%Y-%m-%d} ~ {end:%Y-%m-%d}")
        df = self._t["npw"]
        return df[df["eqp_id"].isin(_as_list(eqps)) & (df["ts"] >= start) & (df["ts"] < end)].copy()

    def defects(self, measure_ids):
        self.log.append(f"결함 좌표(MAP): 측정 {len(_as_list(measure_ids))}건")
        df = self._t["npw_defect"]
        return df[df["measure_id"].isin(_as_list(measure_ids))].copy()

    def edx(self, measure_ids):
        self.log.append(f"EDX 성분: 측정 {len(_as_list(measure_ids))}건")
        df = self._t["edx"]
        return df[df["measure_id"].isin(_as_list(measure_ids))].copy()

    def pm(self, processes=None, eqps=None):
        self.log.append(f"PM 이력: 공정 {processes}, 설비 {eqps}")
        df = self._t["pm"]
        if processes is not None:
            df = df[df["process"].isin(_as_list(processes))]
        if eqps is not None:
            df = df[df["eqp_id"].isin(_as_list(eqps))]
        return df.copy()

    def parts(self, eqps, installed_only=True):
        self.log.append(f"파트 장착 이력: 설비 {_as_list(eqps)}, {'현재 장착' if installed_only else '전체 이력'}")
        df = self._t["parts"]
        df = df[df["eqp_id"].isin(_as_list(eqps))]
        return (df[df["remove_ts"].isna()] if installed_only else df).copy()


class BDQSource:
    """실제 BigDataQuery 연결 자리 (미구현). SyntheticSource 와 같은 메서드·같은 컬럼을 돌려주면 된다.

    예) npw(): 아래처럼 조회하고 컬럼 이름을 measure_id, ts, eqp_id, wafer_id, defect_count, spec_upper 로 맞춘다.
        SELECT <측정ID> AS measure_id, <시각> AS ts, <설비> AS eqp_id, ...
        FROM `<PROJECT.DATASET.NPW_TABLE>`
        WHERE <설비> IN UNNEST(@eqps) AND <시각> >= @start AND <시각> < @end
    - 쿼리는 파라미터 바인딩을 쓰고(문자열 이어붙이기 금지), 읽기 전용 계정으로 접속한다.
    - 조회한 쿼리 문장을 self.log 에 남기면 화면에서 근거로 보여 줄 수 있다.
    """

    def __init__(self):
        raise NotImplementedError("실제 BDQ 어댑터는 사내 환경에서 구현")
