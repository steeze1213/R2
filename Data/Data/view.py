import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# Popup 전담 클래스
class Popup:
    @staticmethod
    def info(title, msg):
        messagebox.showinfo(title, msg)

    @staticmethod
    def error(msg):
        messagebox.showerror("에러", msg)

# 검색 전담 클래스
class ControlBar(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # 1.행정 구역 필터
        ttk.Label(self, text="행정 구역").pack(side="left", padx=4)
        self.region_var = tk.StringVar()
        self.region_combo = ttk.Combobox(
            self, textvariable=self.region_var,
            state="readonly", width=18
        )
        self.region_combo.pack(side="left", padx=4)

        # 2.정렬 기준 필터
        ttk.Label(self, text="정렬 기준").pack(side="left", padx=4)
        self.sort_var = tk.StringVar()
        self.sort_combo = ttk.Combobox(
            self, textvariable=self.sort_var,
            state="readonly", width=26,
            values=["총사고발생건수", "사망자수", "부상자수", "주민등록인구수(등록외국인포함)"]
        )
        self.sort_combo.pack(side="left", padx=4)

        # 3.정렬 방향 필터
        ttk.Label(self, text="정렬 방향").pack(side="left", padx=4)
        self.order_var = tk.StringVar(value="오름차순")
        ttk.Combobox(
            self, textvariable=self.order_var,
            state="readonly", width=10,
            values=["오름차순", "내림차순"]
        ).pack(side="left", padx=4)

        # 4.적용 버튼
        ttk.Button(self, text="적용", command=self.on_apply).pack(side="left", padx=8)

    def update_regions(self, regions):
        # 컨트롤러가 데이터를 로드한 후 호출하여 콤보박스 목록 갱신
        self.region_combo["values"] = regions
        self.region_var.set("")

    def on_apply(self):
        # 적용 버튼 클릭 시 컨트롤러에 필터/정렬 값 전달
        region = self.region_var.get().strip()
        sort_col = self.sort_var.get().strip()
        ascending = (self.order_var.get() == "오름차순")
        self.controller.apply_filter_sort(region, sort_col, ascending)

# DataTable 전담 클래스
class DataTable(ttk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.tree = ttk.Treeview(self, show="headings", selectmode="none")
        self.tree.pack(expand=True, fill="both")

        # 더블클릭 바인딩
        self.tree.bind("<Double-1>", self._on_double_click)

        self._edit_entry = None

    def update_data(self, df, limit=200):
        self.df = df  # 현재 표시 중인 df 저장
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)

        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="w")

        for idx, row in df.head(limit).iterrows():
            self.tree.insert("", "end", iid=str(idx), values=list(row))

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)

        if not row_id or not col_id:
            return

        col_index = int(col_id.replace("#", "")) - 1
        col_name = self.tree["columns"][col_index]

        x, y, w, h = self.tree.bbox(row_id, col_id)
        value = self.tree.set(row_id, col_name)

        self._edit_entry = ttk.Entry(self.tree)
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.insert(0, value)
        self._edit_entry.focus()

        def cleanup():
            if self._edit_entry:
                self._edit_entry.destroy()
                self._edit_entry = None
            self.tree.selection_remove(self.tree.selection())
            self.tree.focus("")

        def save_edit(event=None):
            new_value = self._edit_entry.get()
            cleanup()
            self.controller.update_cell(
                row_idx=int(row_id),
                col_name=col_name,
                value=new_value
            )

        def cancel_edit(event=None):
            cleanup()

        # 키 이벤트
        self._edit_entry.bind("<Return>", save_edit)
        self._edit_entry.bind("<Escape>", cancel_edit)

        # 마우스 클릭 등 포커스 잃을 때
        self._edit_entry.bind("<FocusOut>", cancel_edit)

# 요약 통계 전담 클래스
class AnalysisTablePopup(tk.Toplevel):
    def __init__(self, parent, df):
        super().__init__(parent)
        self.title("교통사고 종합 지표 분석 리포트")
        self.geometry("1000x600")

        # 안내 문구
        header = ttk.Label(
            self,
            text="지역별 사고 치명률 및 특성 분석 결과",
            font=("맑은 고딕", 12, "bold")
        )
        header.pack(pady=10)

        # 표가 들어갈 프레임
        container = ttk.Frame(self)
        container.pack(expand=True, fill="both", padx=10, pady=10)

        # 기존 DataTable 클래스 재활용
        self.table = DataTable(container, controller=None)
        self.table.pack(expand=True, fill="both")

        # 데이터 업데이트
        self.table.update_data(df)

        # 닫기 버튼
        ttk.Button(self, text="닫기", command=self.destroy).pack(pady=10)

# 메뉴바 전담 클래스
class MainMenu(tk.Menu):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # 파일
        file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="열기", command=self.open_file)
        file_menu.add_command(label="저장", command=self.save_file)

        # 기능
        func_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="기능", menu=func_menu)
        func_menu.add_command(label="결측치 처리", command=controller.handle_missing_)
        func_menu.add_command(label="이상치 처리", command=controller.handle_outliers_)
        func_menu.add_command(label="파생변수생성", command=controller.open_derived_popup)

        # 보기
        view_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="보기", menu=view_menu)
        view_menu.add_command(label="원본 보기", command=controller.show_origin)
        view_menu.add_command(label="복사본 보기", command=controller.show_copy)
        view_menu.add_command(label="종합 통계표 보기", command=controller.handle_analysis_report)
        view_menu.add_command(label = "전처리 로그", command=controller.show_logs)
        view_menu.add_command(label="지도로 보기", command=controller.handle_map_visualization)

        # 그래프
        view_graph = tk.Menu(self, tearoff=0)
        self.add_cascade(label="그래프", menu=view_graph)
        view_graph.add_command(label="산점도", command=controller.show_scatter)
        view_graph.add_command(label="막대그래프", command=controller.show_bar)

        # 검색 (토글 버튼)
        self.add_command(
            label="검색",
            command=controller.toggle_region_bar
        )

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            self.controller.load_file(path)

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.controller.save_file(path)

# 파생변수 생성 전담 클래스
class DerivedVariablePopup(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title("파생변수 생성")
        self.geometry("300x180")
        self.resizable(False, False)
        self.grab_set()

        ttk.Label(self, text="생성할 파생변수 선택").pack(pady=12)

        self.btn_risk = ttk.Button(
            self,
            text="위험지역 여부 (사망자수 기준)",
            command=lambda: self.create("risk")
        )
        self.btn_risk.pack(fill="x", padx=20, pady=5)

        self.btn_rate = ttk.Button(
            self,
            text="인구 대비 사고율",
            command=lambda: self.create("rate")
        )
        self.btn_rate.pack(fill="x", padx=20, pady=5)

    def create(self, var_type):
        self.btn_risk.config(state="disabled")
        self.btn_rate.config(state="disabled")

        self.controller.create_derived_variable(var_type)
        self.destroy()

# 메인 View (컨테이너)
class View(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.controller = None

        # 1. 메인 레이아웃 (View 본체)
        self.pack(expand=True, fill="both", padx=5, pady=5)

        # 2. 검색 바 전담 클래스 생성 (초기엔 보이지 않음)
        self.control_bar = None
        self.control_bar_visible = False

        # 3. 데이터 테이블 생성
        self.data_table = DataTable(self, controller=None)
        self.data_table.pack(expand=True, fill="both")

    def set_controller(self, controller):
        self.controller = controller
        # 컨트롤러가 확정되면 컨트롤 바도 생성 (컨트롤러 전달)
        self.control_bar = ControlBar(self.parent, controller)
        self.data_table.controller = controller
        self.parent.config(menu=MainMenu(self.parent, controller))

    def toggle_control_bar(self):

        if self.control_bar_visible:
            self.control_bar.pack_forget()
        else:
            self.control_bar.pack(fill="x", padx=8, pady=4, before=self)
        self.control_bar_visible = not self.control_bar_visible

    def hide_control_bar(self):
        if self.control_bar_visible:
            self.control_bar.pack_forget()
            self.control_bar_visible = False

    def update_region_list(self, regions):
        # 컨트롤 바에게 위임
        if self.control_bar:
            self.control_bar.update_regions(regions)

    def display_data(self, df):
        self.data_table.update_data(df)

    def show_popup(self, title, msg):
        Popup.info(title, msg)

    def show_error(self, msg):
        Popup.error(msg)

    def show_analysis_table(self, df):
        AnalysisTablePopup(self.parent, df)

    def open_derived_popup(self):
        DerivedVariablePopup(self.parent, self.controller)

    def open_traffic_map(self, value_map):
        TrafficMapPopup(self.parent, value_map)

    def show_graph(self, df, graph_type):
        GraphPopup(self.parent, df, graph_type)

# 그래프 팝업
class GraphPopup(tk.Toplevel):
    def __init__(self, parent, df, graph_type):
        super().__init__(parent)
        self.title(f"그래프 - {graph_type}")
        self.geometry("900x600")

        fig = plt.Figure(figsize=(9, 5))
        ax = fig.add_subplot(111)

        if graph_type == "scatter":
            sns.scatterplot(
                data=df,
                x="주민등록인구수(등록외국인포함)",
                y="총사고발생건수",
                s=60,
                alpha=0.7,
                ax=ax
            )
            ax.set_title("인구수 vs 사고 발생 건수")


        elif graph_type == "bar":
            region_col = "행정구역별(도/특별시/광역시)"
            value_col = "총사고발생건수"

            # 문자열 공백/NaN 정리(지역명 깨짐/중복 방지)
            tmp = df.copy()
            tmp[region_col] = tmp[region_col].astype(str).str.strip()

            # 지역별 합계
            agg = (
                tmp.groupby(region_col, as_index=False)[value_col]
                .sum()
                .sort_values(value_col, ascending=False)
            )

            sns.barplot(
                data=agg,
                x=region_col,
                y=value_col,
                errorbar=None,
                ax=ax
            )
            ax.set_title("지역별 사고 발생 건수(합계)")
            ax.tick_params(axis='x', rotation=45)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        ttk.Button(self, text="닫기", command=self.destroy).pack(pady=8)

#지도 시각화
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
import pandas as pd


class TrafficMapPopup(tk.Toplevel):
    def __init__(self, parent, value_map):
        super().__init__(parent)
        self.title("교통사고 지표 지도 분석")
        self.geometry("800x650")

        self.value_map = value_map
        self.canvas_w, self.canvas_h = 700, 550
        self.padding = 30

        # 지표 선택 및 상태창
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill="x", pady=5)
        self.status_var = tk.StringVar(value="지표를 선택하여 분석을 시작하세요")
        tk.Label(ctrl_frame, textvariable=self.status_var, font=("Malgun Gothic", 12, "bold")).pack()

        self.canvas = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h, bg="white", highlightthickness=0)
        self.canvas.pack()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", pady=10)

        metrics = ["총사고발생건수", "사망자수", "부상자수"]
        for m in metrics:
            ttk.Button(btn_frame, text=m, command=lambda val=m: self.repaint_map(val)).pack(side="left", padx=15)

        self.region_items = {}
        self.render_base_map()

    def render_base_map(self):
        #GeoJSON을 읽어 지도의 기본 형태(시/군/도 경계)를 그림
        try:
            with open("map.geojson", "r", encoding="utf-8") as f:
                gj = json.load(f)
        except:
            messagebox.showerror("에러", "map.geojson 파일을 찾을 수 없습니다.")
            return

        regions_rings, sido_rings = {}, {}
        all_lon, all_lat = [], []

        # 1.링(Ring) 데이터 수집 및 좌표 범위 계산
        for feat in gj.get("features", []):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            sidonm, sggnm = props.get("sidonm"), props.get("sggnm")

            # key 생성 함수 호출 (내부 구현)
            city_key = self._get_geo_key(sidonm, sggnm)
            sido_key = str(sidonm).strip().replace(" ", "")

            coords = geom.get("coordinates")
            rings = coords[0] if geom.get("type") == "Polygon" else [p[0] for p in coords]

            for ring in (rings if geom.get("type") == "MultiPolygon" else [rings]):
                regions_rings.setdefault(city_key, []).append(ring)
                sido_rings.setdefault(sido_key, []).append(ring)
                for lon, lat in ring:
                    all_lon.append(lon);
                    all_lat.append(lat)

        self.min_lon, self.max_lon = min(all_lon), max(all_lon)
        self.min_lat, self.max_lat = min(all_lat), max(all_lat)

        # 2.Shapely 병합 및 그리기
        merged_city = self._merge_rings(regions_rings)
        merged_sido = self._merge_rings(sido_rings)

        for city_key, shape in merged_city.items():
            items = []
            geoms = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
            for g in geoms:
                pts = self._project_shape(g)
                it = self.canvas.create_polygon(pts, fill="#EDEDED", outline="#777777")
                items.append(it)
            self.region_items[city_key] = items

        # 도 경계선 굵게 추가
        for _, shape in merged_sido.items():
            geoms = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
            for g in geoms:
                pts = self._project_shape(g)
                self.canvas.create_polygon(pts, fill="", outline="#444444", width=2)

    def _project_shape(self, shape):
        coords = list(shape.exterior.coords)
        pts = []
        for lon, lat in coords:
            x = (lon - self.min_lon) / (self.max_lon - self.min_lon + 1e-9)
            y = (self.max_lat - lat) / (self.max_lat - self.min_lat + 1e-9)
            pts.extend([self.padding + x * (self.canvas_w - 2 * self.padding),
                        self.padding + y * (self.canvas_h - 2 * self.padding)])
        return pts

    def _merge_rings(self, rings_dict):
        merged = {}
        for key, rings in rings_dict.items():
            polys = [Polygon(r if r[0] == r[-1] else r + [r[0]]) for r in rings]
            u = unary_union([p.buffer(0) if not p.is_valid else p for p in polys])
            if not u.is_empty: merged[key] = u
        return merged

    def _get_geo_key(self, sidonm, sggnm):
        metro = {"서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", "제주특별자치도"}
        sido = str(sidonm).strip().replace(" ", "")
        sgg = str(sggnm).strip()
        if sido in metro: return sido
        if sgg.endswith("군"): return sgg.replace(" ", "")
        if "시" in sgg: return sgg[:sgg.find("시") + 1].replace(" ", "")
        return sgg.replace(" ", "")

    def repaint_map(self, metric):
        vals = [self.value_map.get(ck, {}).get(metric, 0.0) for ck in self.region_items.keys()]
        s = pd.Series(vals)
        q = s.quantile([0.5, 0.75, 0.9, 0.95, 0.99]).tolist() if not s.empty else [0] * 5
        palette = ["#fff5f5", "#ffe3e3", "#ffbdbd", "#ff8a8a", "#ff5c5c", "#e03131", "#a51111"]

        for city_key, items in self.region_items.items():
            v = self.value_map.get(city_key, {}).get(metric, 0.0)
            color = palette[0]
            for i, threshold in enumerate(q):
                if v > threshold: color = palette[i + 1]
            for it in items:
                self.canvas.itemconfig(it, fill=color)
        self.status_var.set(f"분석 지표: {metric}")