from datetime import datetime

class Controller:
    # 뷰와 모델을 어떻게 적절하게 활용할건지 담당하는 클래스, 모델과 뷰를 연결해주는 역할
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.logs = []

    def load_file(self, path):
        try:
            self.model.load_csv(path)
            self.view.update_region_list(self.model.get_regions())
            self.view.display_data(self.model.return_copy())
            self.view.show_popup("파일 읽기", "파일 읽기 성공")
        except Exception as e:
            self.view.show_popup("파일 읽기 에러", f"파일을 불러오는 중 오류가 발생했습니다:\n{e}")

    def save_file(self, path):
        try:
            self.model.save_csv(path)
            self.view.show_popup("저장 완료", "파일이 성공적으로 저장되었습니다.")
        except Exception as e:
            self.view.show_popup("저장 에러", f"파일 저장 중 오류가 발생했습니다:\n{e}")

    def handle_missing_(self):
        try:
            self.model.handle_missing()
            self.add_log(action="결측치 처리", target="수치 컬럼", detail="NaN → 중앙값 대체")
            self.view.display_data(self.model.return_copy())
            self.view.show_popup("전처리", "결측치 처리가 완료되었습니다.")
        except Exception as e:
            self.view.show_popup("전처리 에러", f"결측치 처리 중 오류 발생:\n{e}")

    def handle_outliers_(self):
        try:
            self.model.handle_outliers()
            self.add_log(action="이상치 처리", target="총사고발생건수/사망자수/부상자수", detail="IQR 기준 clipping")
            self.view.display_data(self.model.return_copy())
            self.view.show_popup("전처리", "이상치 처리가 완료되었습니다.")
        except Exception as e:
            self.view.show_popup("전처리 에러", f"이상치 처리 중 오류 발생:\n{e}")

    def show_origin(self):
        try:
            self.view.hide_control_bar()
            self.view.display_data(self.model.return_df())
        except Exception as e:
            self.view.show_popup("표시 에러", f"원본 데이터를 표시할 수 없습니다:\n{e}")

    def show_copy(self):
        try:
            self.view.hide_control_bar()
            self.view.display_data(self.model.return_copy())
        except Exception as e:
            self.view.show_popup("표시 에러", f"복사본 데이터를 표시할 수 없습니다:\n{e}")

    def toggle_region_bar(self):
        try:
            self.view.toggle_control_bar()
        except Exception as e:
            # UI 토글은 치명적이지 않으므로 콘솔에 출력하거나 가볍게 처리
            print(f"UI Toggle Error: {e}")

    def apply_filter_sort(self, region, sort_col, ascending):
        try:
            df = self.model.filter_and_sort(region, sort_col, ascending)
            self.view.display_data(df)
        except Exception as e:
            self.view.show_popup("필터/정렬 에러", f"데이터를 거르는 중 오류가 발생했습니다:\n{e}")

    def update_cell(self, row_idx, col_name, value):
        try:
            before = self.model.copy_df.at[row_idx, col_name]
            self.model.update_cell(row_idx, col_name, value)
            after = self.model.copy_df.at[row_idx, col_name]

            self.add_log(action="셀 수정", target=f"row={row_idx}, col={col_name}", detail=f"{before} → {after}")

            self.model.update_cell(row_idx, col_name, value)
            self.view.display_data(self.model.return_copy())
        except Exception as e:
            self.view.show_popup("수정 에러", f"데이터 수정에 실패했습니다:\n{e}")\

    def handle_analysis_report(self):
        try:
            # 모델에서 가공된 분석용 DF를 가져옴
            analysis_df = self.model.get_analysis_df()

            if analysis_df is not None:
                # 팝업 띄우기
                self.view.show_analysis_table(analysis_df)
            else:
                self.view.show_error("먼저 CSV 파일을 열어주세요.")
        except Exception as e:
            self.view.show_popup("분석 에러", f"데이터 분석 중 오류가 발생했습니다:\n{e}")

    def show_logs(self):
        if not self.logs:
            self.view.show_popup("전처리 로그", "기록된 전처리 내역이 없습니다.")
            return

        text = "\n".join(
            f"[{l['time']}] {l['action']} | {l['target']} | {l['detail']}"
            for l in self.logs
        )
        self.view.show_popup("전처리 로그", text)

    # 로그 기록용 공통 함수
    def add_log(self, action, target="", detail=""):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append({
            "time": time,
            "action": action,
            "target": target,
            "detail": detail
        })

    #파생변수 실행 함수
    def create_derived_variable(self, var_type):
        try:
            df = self.model.return_copy()

            if var_type == "risk":
                if "위험지역여부" in df.columns:
                    self.view.show_popup(
                        "파생변수",
                        "이미 '위험지역여부' 컬럼이 존재합니다."
                    )
                    return

                self.model.add_risk_region()
                self.add_log(
                    action="파생변수 생성",
                    target="위험지역여부",
                    detail="사망자수 >= 5 → 1/0"
                )

            elif var_type == "rate":
                if "인구대비사고율" in df.columns:
                    self.view.show_popup(
                        "파생변수",
                        "이미 '인구대비사고율' 컬럼이 존재합니다."
                    )
                    return

                self.model.add_accident_rate()
                self.add_log(
                    action="파생변수 생성",
                    target="인구대비사고율",
                    detail="발생건수 / 주민등록인구수"
                )

            self.view.display_data(self.model.return_copy())
            self.view.show_popup("파생변수", "파생변수가 생성되었습니다.")

        except Exception as e:
            self.view.show_popup("파생변수 에러", str(e))

    def open_derived_popup(self):
        self.view.open_derived_popup()

    def handle_map_visualization(self):
        try:
            # 1. 모델에서 지도용 가공 데이터 가져오기 (인자 제거)
            map_data = self.model.get_map_value_map()

            # 2. 뷰에 지도 팝업 요청 (메서드 이름 일치 및 인자 수정)
            if map_data:
                self.view.open_traffic_map(map_data)
            else:
                self.view.show_error("표시할 데이터가 없습니다.")
        except Exception as e:
            self.view.show_popup("지도 에러", f"지도를 생성할 수 없습니다: {e}")

    def show_scatter(self):

        try:
            df = self.model.return_copy()
            self.view.show_graph(df, "scatter")
        except Exception as e:
            self.view.show_popup("표시 에러", f"먼저 csv파일을 열어야됩니다.:\n{e}")

    def show_bar(self):
        try:
            df = self.model.return_copy()
            self.view.show_graph(df, "bar")
        except Exception as e:
            self.view.show_popup("표시 에러", f"먼저 csv파일을 열어야됩니다.:\n{e}")