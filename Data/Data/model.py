import pandas as pd
import numpy as np

class Model:
    def __init__(self):
        self.df = None
        self.copy_df = None

    def load_csv(self, path):
        try:
            self.df = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            self.df = pd.read_csv(path, encoding="cp949")

        self.df.columns = [c.strip() for c in self.df.columns]
        self.copy_df = self.df.copy()

    def return_df(self):
        return self.df

    def return_copy(self):
        return self.copy_df

    def save_csv(self, path):
        if self.df is not None:
            self.df.to_csv(path, index=False, encoding="utf-8-sig")

    def handle_missing(self):
        cols = [
            "총사고발생건수",
            "사망자수",
            "부상자수",
            "주민등록인구수(등록외국인포함)"
        ]
        valid = [c for c in cols if c in self.copy_df.columns]
        self.copy_df[valid] = self.copy_df[valid].fillna(
            self.copy_df[valid].median()
        )

    def handle_outliers(self):
        cols = ["총사고발생건수", "사망자수", "부상자수"]
        for col in cols:
            if col not in self.copy_df.columns:
                continue
            q1 = self.copy_df[col].quantile(0.25)
            q3 = self.copy_df[col].quantile(0.75)
            iqr = q3 - q1
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            self.copy_df[col] = np.clip(self.copy_df[col], low, high)

    # 행정 구역 목록
    def get_regions(self):
        col = "행정구역별(도/특별시/광역시)"
        if col not in self.copy_df.columns:
            return []
        regions = (
            self.copy_df[col]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
        regions.sort()
        return regions

    # 필터 + 정렬
    def filter_and_sort(self, region, sort_col, ascending):
        df = self.copy_df

        if region:
            df = df[df["행정구역별(도/특별시/광역시)"] == region]

        if sort_col:
            key = pd.to_numeric(df[sort_col], errors="coerce")
            df = df.assign(_k=key).sort_values("_k", ascending=ascending).drop(columns="_k")

        return df

    # 데이터 수정 기능
    def update_cell(self, row_idx, col_name, value):
        if self.copy_df is None:
            return

        # 빈 문자열 → NaN
        if value == "":
            value = np.nan

        # 숫자 컬럼은 숫자로 변환 시도
        try:
            value = float(value)
            if value.is_integer():
                value = int(value)
        except:
            pass

        self.copy_df.at[row_idx, col_name] = value

    def get_analysis_df(self):
        if self.copy_df is None:
            return None

        df = self.copy_df.copy()
        col_sido = '행정구역별(도/특별시/광역시)'

        # 1. 숫자 데이터 전처리 (결측치 및 '-' 처리)
        numeric_cols = [
            '총사고발생건수', '사망자수', '부상자수',
            '주민등록인구수(등록외국인포함)', '총자동차수'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 2. 시도별로 그룹화 (작성하신 시도별 랭킹의 핵심)
        area_df = df.groupby(col_sido).agg({
            '총사고발생건수': 'sum',
            '사망자수': 'sum',
            '부상자수': 'sum',
            '주민등록인구수(등록외국인포함)': 'sum',
            '총자동차수': 'sum'
        }).reset_index()

        # 3. 전국 총계 계산 (전국 대비 비율 계산용)
        total_national_accidents = area_df['총사고발생건수'].sum()

        # 4. 분석 지표 및 랭킹 관련 데이터 계산
        # 전국 대비 비율 (%)
        area_df['전국_대비_비율(%)'] = (area_df['총사고발생건수'] / total_national_accidents * 100).round(2)
        # 치명률 (%)
        area_df['사고_치명률(%)'] = (area_df['사망자수'] / area_df['총사고발생건수'] * 100).round(2)
        # 인구 1만명당 사고율
        area_df['인구대비_사고율'] = (area_df['총사고발생건수'] / area_df['주민등록인구수(등록외국인포함)'] * 10000).round(2)

        # 5. [중요] 사고 발생건수 기준 내림차순 정렬 및 순위 부여
        area_df = area_df.sort_values(by='총사고발생건수', ascending=False)
        area_df.insert(0, '순위', range(1, len(area_df) + 1))

        # 6. 최종 보여줄 컬럼 선택
        result_df = area_df[[
            '순위', col_sido, '총사고발생건수', '사망자수',
            '전국_대비_비율(%)', '사고_치명률(%)', '인구대비_사고율'
        ]]

        return result_df

    # 파생변수

    def add_risk_region(self):
        # 위험지역 여부 (사망자수 >= 5)
        self.copy_df["위험지역여부"] = np.where(
            self.copy_df["사망자수"] >= 5,
            1,
            0
        )

    def add_accident_rate(self):
        accident_col = "총사고발생건수"
        pop_col = "주민등록인구수(등록외국인포함)"

        if accident_col not in self.copy_df.columns:
            raise KeyError(accident_col)

        if pop_col not in self.copy_df.columns:
            raise KeyError(pop_col)

        # 0 또는 NaN 방어
        safe_pop = self.copy_df[pop_col].replace(0, np.nan)

        self.copy_df = self.copy_df.assign(
            인구대비사고율=self.copy_df[accident_col] / safe_pop
        )

    def get_map_value_map(self):
        # 지도시각화에 필요한 전체 지표 데이터를 REGION_KEY 기반으로 가공하여 반환
        if self.copy_df is None: return {}

        df = self.copy_df.copy()
        target_cols = ["총사고발생건수", "사망자수", "부상자수"]

        # 숫자 변환
        for c in target_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # REGION_KEY 생성 로직 (city_county_key_from_csv 반영)
        def make_key(row):
            metro = {"서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", "제주특별자치도"}
            sido = str(row["행정구역별(도/특별시/광역시)"]).strip()
            sgg = str(row["행정구역별(시/구)"]).strip()

            norm_sido = sido.replace(" ", "")
            if norm_sido in metro:
                return norm_sido
            if " " in sgg:
                first = sgg.split()[0].strip()
                if first.endswith("시"):
                    return first.replace(" ", "")
            return sgg.replace(" ", "")

        df["REGION_KEY"] = df.apply(make_key, axis=1)

        # 그룹화 및 딕셔너리 변환
        agg = df.groupby("REGION_KEY")[target_cols].sum().reset_index()
        value_map = {row["REGION_KEY"]: {k: float(row[k]) for k in target_cols} for _, row in agg.iterrows()}
        return value_map