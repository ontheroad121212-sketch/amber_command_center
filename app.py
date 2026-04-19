"""
🏨 Amber Command Center v1.0
엠버퓨어힐 통합 수익관리 시스템

[1단계] 기본 요금관리 기능
- 비밀번호 로그인
- 잔여객실 파일 업로드
- BAR 요금 현황
- 예약 변화량 감지
- 판도 변화 감지
- Firebase 저장
- 엑셀 다운로드
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore
import math
import re
import io

# ============================================================
# 1. 페이지 설정 (반드시 최상단)
# ============================================================
st.set_page_config(
    page_title="Amber Command Center",
    page_icon="🏨",
    layout="wide"
)

# ============================================================
# 2. 비밀번호 로그인
# ============================================================
def check_password():
    """비밀번호 확인 - 통과 못하면 아무것도 안 보여줌"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔐 Amber Command Center")
        st.caption("관계자 외 출입 금지")
        pw = st.text_input("접속 암호", type="password")
        if st.button("접속"):
            if pw == "0822":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("암호가 틀렸습니다.")
        return False
    return True

# 비밀번호 통과 못하면 여기서 멈춤
if not check_password():
    st.stop()

# ============================================================
# 3. Firebase 초기화
# ============================================================
if not firebase_admin._apps:
    try:
        fb_dict = st.secrets["firebase"]
        cred = credentials.Certificate(dict(fb_dict))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase 연결 실패: {e}")
        st.stop()

db = firestore.client()

# ============================================================
# 4. 전역 설정 (요금 테이블 등)
# ============================================================
BAR_GRADIENT_COLORS = {
    "BAR0": "#B71C1C",
    "BAR1": "#D32F2F", "BAR2": "#EF5350", "BAR3": "#FF8A65", "BAR4": "#FFB199",
    "BAR5": "#81C784", "BAR6": "#A5D6A7", "BAR7": "#C8E6C9", "BAR8": "#E8F5E9",
}
BAR_LIGHT_COLORS = {
    "BAR0": "#FFCDD2",
    "BAR1": "#FFEBEE", "BAR2": "#FFEBEE", "BAR3": "#FFF3E0", "BAR4": "#FFF3E0",
    "BAR5": "#E8F5E9", "BAR6": "#E8F5E9", "BAR7": "#F1F8E9", "BAR8": "#F1F8E9",
}

WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]
ALL_ROOMS = DYNAMIC_ROOMS + FIXED_ROOMS

PRICE_TABLE = {
    "FDB": {"BAR0": 802000, "BAR8": 315000, "BAR7": 353000, "BAR6": 396000, "BAR5": 445000, "BAR4": 502000, "BAR3": 567000, "BAR2": 642000, "BAR1": 728000},
    "FDE": {"BAR0": 839000, "BAR8": 352000, "BAR7": 390000, "BAR6": 433000, "BAR5": 482000, "BAR4": 539000, "BAR3": 604000, "BAR2": 679000, "BAR1": 765000},
    "HDP": {"BAR0": 759000, "BAR8": 280000, "BAR7": 318000, "BAR6": 361000, "BAR5": 410000, "BAR4": 467000, "BAR3": 532000, "BAR2": 607000, "BAR1": 693000},
    "HDT": {"BAR0": 729000, "BAR8": 250000, "BAR7": 288000, "BAR6": 331000, "BAR5": 380000, "BAR4": 437000, "BAR3": 502000, "BAR2": 577000, "BAR1": 663000},
    "HDF": {"BAR0": 916000, "BAR8": 420000, "BAR7": 458000, "BAR6": 501000, "BAR5": 550000, "BAR4": 607000, "BAR3": 672000, "BAR2": 747000, "BAR1": 833000},
}
FIXED_PRICE_TABLE = {
    "GDB": {"UND1": 298000, "UND2": 298000, "MID1": 298000, "MID2": 298000, "UPP1": 298000, "UPP2": 298000},
    "GDF": {"UND1": 375000, "UND2": 410000, "MID1": 410000, "MID2": 488000, "UPP1": 488000, "UPP2": 578000},
    "FFD": {"UND1": 353000, "UND2": 393000, "MID1": 433000, "MID2": 482000, "UPP1": 539000, "UPP2": 604000},
    "FPT": {"UND1": 500000, "UND2": 550000, "MID1": 600000, "MID2": 650000, "UPP1": 700000, "UPP2": 750000},
    "PPV": {"UND1": 1104000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000},
}
FIXED_BAR0_TABLE = {"GDB": 298000, "GDF": 678000, "FFD": 704000, "FPT": 850000, "PPV": 1704000}

# ============================================================
# 5. 핵심 로직: 시즌 판단 & BAR 결정
# ============================================================
def get_season_details(date_obj):
    """날짜를 받아서 시즌 코드, 시즌명, 주말여부를 반환"""
    m, d = date_obj.month, date_obj.day
    md = f"{m:02d}.{d:02d}"
    actual_is_weekend = date_obj.weekday() in [4, 5]

    if ("02.13" <= md <= "02.18") or ("09.23" <= md <= "09.28"):
        season, is_weekend = "UPP", True
    elif ("12.21" <= md <= "12.31") or ("10.01" <= md <= "10.08"):
        season, is_weekend = "UPP", False
    elif ("05.03" <= md <= "05.05") or ("05.24" <= md <= "05.26") or ("06.05" <= md <= "06.07"):
        season, is_weekend = "MID", True
    elif "07.17" <= md <= "08.29":
        season, is_weekend = "UPP", actual_is_weekend
    elif ("01.04" <= md <= "03.31") or ("11.01" <= md <= "12.20"):
        season, is_weekend = "UND", actual_is_weekend
    else:
        season, is_weekend = "MID", actual_is_weekend

    type_code = f"{season}{'2' if is_weekend else '1'}"
    return type_code, season, is_weekend

def determine_bar(season, is_weekend, occ):
    """점유율로 BAR 결정 (BAR8=가장 낮음, BAR1=가장 높음)"""
    if season == "UPP":
        if is_weekend:
            if occ >= 81: return "BAR1"
            elif occ >= 51: return "BAR2"
            elif occ >= 31: return "BAR3"
            else: return "BAR4"
        else:
            if occ >= 81: return "BAR2"
            elif occ >= 51: return "BAR3"
            elif occ >= 31: return "BAR4"
            else: return "BAR5"
    elif season == "MID":
        if is_weekend:
            if occ >= 81: return "BAR3"
            elif occ >= 51: return "BAR4"
            elif occ >= 31: return "BAR5"
            else: return "BAR6"
        else:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
    else:  # UND
        if is_weekend:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
        else:
            if occ >= 81: return "BAR5"
            elif occ >= 51: return "BAR6"
            elif occ >= 31: return "BAR7"
            else: return "BAR8"

def get_final_values(room_id, date_obj, avail, total, manual_bar=None):
    """객실의 최종 점유율, BAR, 가격을 계산"""
    type_code, season, is_weekend = get_season_details(date_obj)
    try:
        current_avail = float(avail) if pd.notna(avail) else 0.0
    except:
        current_avail = 0.0
    occ = ((total - current_avail) / total * 100) if total > 0 else 0

    # 수동 오버라이드 우선
    if manual_bar:
        bar = manual_bar
        if bar == "BAR0":
            price = PRICE_TABLE.get(room_id, {}).get("BAR0", 0) if room_id in DYNAMIC_ROOMS else FIXED_BAR0_TABLE.get(room_id, 0)
        else:
            price = PRICE_TABLE.get(room_id, {}).get(bar, 0) if room_id in DYNAMIC_ROOMS else FIXED_PRICE_TABLE.get(room_id, {}).get(bar, 0)
        return occ, bar, price, True

    if room_id in DYNAMIC_ROOMS:
        bar = determine_bar(season, is_weekend, occ)
        price = PRICE_TABLE.get(room_id, {}).get(bar, 0)
    else:
        bar = type_code
        price = FIXED_PRICE_TABLE.get(room_id, {}).get(type_code, 0)
    return occ, bar, price, False

# ============================================================
# 6. HTML 테이블 렌더러
# ============================================================
def render_master_table(current_df, prev_df, title="", mode="기준"):
    """객실 × 날짜 매트릭스 테이블 생성"""
    if current_df.empty:
        return "<div style='padding:20px;'>데이터를 업로드하세요.</div>"

    dates = sorted(current_df['Date'].unique())
    row_padding = "8px"
    header_padding = "5px"
    font_size = "11px"

    html = f"<div style='margin-top:40px; margin-bottom:10px; font-weight:bold; font-size:18px; padding:10px; background:#f0f2f6; border-left:10px solid #000;'>{title}</div>"
    html += "<div style='overflow-x: auto; white-space: nowrap; border: 1px solid #ddd;'>"
    html += f"<table style='width:100%; border-collapse:collapse; font-size:{font_size}; min-width:1000px;'>"
    html += "<thead><tr style='background:#f9f9f9;'>"
    html += f"<th rowspan='2' style='border:1px solid #ddd; width:120px; position:sticky; left:0; background:#f9f9f9; z-index:2; padding:{header_padding};'>객실</th>"

    for d in dates:
        html += f"<th style='border:1px solid #ddd; padding:{header_padding};'>{d.strftime('%m-%d')}</th>"
    html += "</tr><tr style='background:#f9f9f9;'>"
    for d in dates:
        wd = WEEKDAYS_KR[d.weekday()]
        color = "red" if wd == '일' else ("blue" if wd == '토' else "black")
        html += f"<th style='border:1px solid #ddd; padding:{header_padding}; color:{color};'>{wd}</th>"
    html += "</tr></thead><tbody>"

    for rid in ALL_ROOMS:
        label = f"<b>{rid}</b>" if rid in ["HDF", "PPV"] else rid
        border_thick = "border-bottom:3.4px solid #000;" if rid in ["HDF", "PPV"] else ""
        html += f"<tr style='{border_thick}'><td style='border:1px solid #ddd; padding:{row_padding}; background:#fff; border-right:4px solid #000; position:sticky; left:0; z-index:1;'>{label}</td>"

        for d in dates:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                html += f"<td style='border:1px solid #ddd; padding:{row_padding}; text-align:center;'>-</td>"
                continue

            avail = curr_match.iloc[0]['Available']
            total = curr_match.iloc[0]['Total']
            occ, bar, base_price, is_manual = get_final_values(rid, d, avail, total)

            # 이전 데이터와 비교
            prev_bar, prev_avail = None, None
            if not prev_df.empty:
                prev_m = prev_df[(prev_df['RoomID'] == rid) & (prev_df['Date'] == d)]
                if not prev_m.empty:
                    prev_avail = prev_m.iloc[0]['Available']
                    _, prev_bar, _, _ = get_final_values(rid, d, prev_avail, prev_m.iloc[0]['Total'])

            style = f"border:1px solid #ddd; padding:{row_padding}; text-align:center; background-color:white;"

            if mode == "기준":
                bg = BAR_GRADIENT_COLORS.get(bar, "#FFFFFF") if rid in DYNAMIC_ROOMS or bar == "BAR0" else "#F1F1F1"
                style += f"background-color: {bg};"
                content = f"<b>{bar}</b><br>{base_price:,}<br>{occ:.0f}%"

            elif mode == "변화":
                curr_av = float(avail) if pd.notna(avail) else 0.0
                prev_av = float(prev_avail) if (prev_avail is not None and pd.notna(prev_avail)) else 0.0
                pickup = (prev_av - curr_av) if prev_avail is not None else 0
                bg = BAR_LIGHT_COLORS.get(bar, "#FFFFFF") if rid in DYNAMIC_ROOMS or bar == "BAR0" else "#FFFFFF"
                style += f"background-color: {bg};"
                if pickup > 0:
                    style += "color:red; font-weight:bold; border: 1.5px solid red;"
                    content = f"+{pickup:.0f}"
                elif pickup < 0:
                    style += "color:blue; font-weight:bold;"
                    content = f"{pickup:.0f}"
                else:
                    content = "-"

            elif mode == "판도변화":
                curr_b = str(bar).strip() if bar else ""
                prev_b = str(prev_bar).strip() if prev_bar else ""
                if prev_bar is not None and prev_b != curr_b:
                    bg = BAR_GRADIENT_COLORS.get(bar, "#7000FF")
                    style += f"background-color: {bg}; color: white; font-weight: bold; border: 2.5px solid #000;"
                    content = f"▲ {bar}"
                else:
                    content = bar

            html += f"<td style='{style}'>{content}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# ============================================================
# 7. 파일 파서 & DB 유틸
# ============================================================
def robust_date_parser(d_val):
    """엑셀의 다양한 날짜 형식을 date 객체로 변환"""
    if pd.isna(d_val):
        return None
    try:
        if isinstance(d_val, (int, float)):
            return (pd.to_datetime('1899-12-30') + pd.to_timedelta(d_val, 'D')).date()
        s = str(d_val).strip().replace('.', '-').replace('/', '-').replace(' ', '')
        match = re.search(r'(\d{1,2})-(\d{1,2})', s)
        if match:
            return date(2026, int(match.group(1)), int(match.group(2)))
    except:
        pass
    return None

def get_latest_snapshot():
    """가장 최근 저장된 스냅샷 불러오기"""
    docs = db.collection("daily_snapshots").order_by("save_time", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        d_dict = doc.to_dict()
        df = pd.DataFrame(d_dict['data'])
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df, d_dict.get('work_date', '알수없음')
    return pd.DataFrame(), None

# ============================================================
# 8. 세션 초기화
# ============================================================
if 'today_df' not in st.session_state:
    st.session_state.today_df = pd.DataFrame()
if 'prev_df' not in st.session_state:
    st.session_state.prev_df = pd.DataFrame()
if 'compare_label' not in st.session_state:
    st.session_state.compare_label = ""

# ============================================================
# 9. 메인 UI
# ============================================================
st.title("🏨 Amber Command Center")
st.caption("v1.0 - 엠버퓨어힐 통합 수익관리 시스템")

# -------------------- 사이드바 --------------------
with st.sidebar:
    st.header("📅 과거 기록 조회")

    # 저장된 날짜 태그 표시
    try:
        all_docs = db.collection("daily_snapshots").select(["work_date"]).stream()
        saved_dates = sorted(list(set([d.to_dict().get('work_date', '') for d in all_docs if d.to_dict().get('work_date')])))
        if saved_dates:
            st.markdown("**📌 저장된 날짜 (최근 14일)**")
            tags = "".join([
                f"<span style='background:#E8F5E9; border:1px solid #4CAF50; color:#2E7D32; padding:3px 8px; border-radius:12px; margin:2px; font-size:12px; display:inline-block;'>{d[5:]} ✅</span>"
                for d in saved_dates[-14:]
            ])
            st.markdown(f"<div style='margin-bottom:10px;'>{tags}</div>", unsafe_allow_html=True)
    except:
        pass

    work_day = st.date_input("조회 날짜", value=date.today())
    if st.button("📂 과거 기록 불러오기"):
        docs = db.collection("daily_snapshots").where("work_date", "==", work_day.strftime("%Y-%m-%d")).limit(1).stream()
        found = False
        for doc in docs:
            d_dict = doc.to_dict()
            st.session_state.today_df = pd.DataFrame(d_dict['data'])
            if not st.session_state.today_df.empty and 'Date' in st.session_state.today_df.columns:
                st.session_state.today_df['Date'] = pd.to_datetime(st.session_state.today_df['Date']).dt.date

            if 'prev_data' in d_dict and d_dict['prev_data']:
                st.session_state.prev_df = pd.DataFrame(d_dict['prev_data'])
                if not st.session_state.prev_df.empty and 'Date' in st.session_state.prev_df.columns:
                    st.session_state.prev_df['Date'] = pd.to_datetime(st.session_state.prev_df['Date']).dt.date
            else:
                st.session_state.prev_df = pd.DataFrame()

            st.session_state.compare_label = f"불러온 과거 기록: {work_day}"
            found = True
        if found:
            st.success("스냅샷 로드 완료")
        else:
            st.warning("해당 날짜의 데이터가 없습니다.")

    st.divider()

    # 파일 업로더
    st.header("📂 잔여객실 파일 업로드")
    files = st.file_uploader("엑셀/CSV 파일", accept_multiple_files=True, type=['xlsx', 'xls', 'csv'])

    st.divider()

    if st.button("🚀 오늘 내역 저장", type="primary", use_container_width=True):
        if not st.session_state.today_df.empty:
            t_df = st.session_state.today_df.copy()
            t_df['Date'] = t_df['Date'].apply(lambda x: x.isoformat())
            p_df_dict = []
            if not st.session_state.prev_df.empty:
                p_df = st.session_state.prev_df.copy()
                p_df['Date'] = p_df['Date'].apply(lambda x: x.isoformat())
                p_df_dict = p_df.to_dict(orient='records')

            db.collection("daily_snapshots").add({
                "work_date": date.today().strftime("%Y-%m-%d"),
                "save_time": datetime.now().isoformat(),
                "data": t_df.to_dict(orient='records'),
                "prev_data": p_df_dict
            })
            st.success("저장 완료!")
        else:
            st.warning("저장할 데이터가 없습니다.")

# -------------------- 파일 파싱 --------------------
if files:
    new_extracted = []
    ROW_MAP = {4: "GDB", 5: "GDF", 6: "FDB", 7: "FDE", 8: "FPT",
               9: "FFD", 10: "HDP", 11: "HDT", 12: "HDF", 13: "PPV"}

    for f in files:
        date_tag = re.search(r'\d{8}', f.name).group() if re.search(r'\d{8}', f.name) else f.name
        df_raw = pd.read_excel(f, header=None)
        dates_raw = df_raw.iloc[2, 2:].values

        for r_idx, rid in ROW_MAP.items():
            if r_idx < len(df_raw):
                tot = pd.to_numeric(df_raw.iloc[r_idx, 1], errors='coerce')
                for d_val, av in zip(dates_raw, df_raw.iloc[r_idx, 2:].values):
                    d_obj = robust_date_parser(d_val)
                    if d_obj is None:
                        continue
                    new_extracted.append({
                        "Date": d_obj, "RoomID": rid,
                        "Available": pd.to_numeric(av, errors='coerce'),
                        "Total": tot, "Tag": date_tag
                    })

    if new_extracted:
        new_df = pd.DataFrame(new_extracted)

        if st.session_state.prev_df.empty:
            latest_db, save_dt = get_latest_snapshot()
            if not latest_db.empty:
                combined = pd.concat([new_df, latest_db]).drop_duplicates(subset=['Date', 'RoomID'], keep='first')
                st.session_state.today_df = combined.sort_values(by=['Date', 'RoomID'])
                st.session_state.prev_df = latest_db
                st.session_state.compare_label = f"자동 DB 병합: {save_dt} 기준과 비교"
            else:
                st.session_state.today_df = new_df
                st.session_state.prev_df = pd.DataFrame()
                st.session_state.compare_label = "비교 대상 없음 (첫 업로드)"
        else:
            combined = pd.concat([new_df, st.session_state.today_df]).drop_duplicates(subset=['Date', 'RoomID'], keep='first')
            st.session_state.today_df = combined.sort_values(by=['Date', 'RoomID'])

# -------------------- 메인 화면 --------------------
if not st.session_state.today_df.empty:
    curr = st.session_state.today_df
    prev = st.session_state.prev_df

    if st.session_state.compare_label:
        st.info(f"ℹ️ {st.session_state.compare_label}")

    # 3개 테이블 순차 출력
    st.markdown(render_master_table(curr, prev, title="📊 1. BAR 요금 현황", mode="기준"),
                unsafe_allow_html=True)
    st.markdown(render_master_table(curr, prev, title="📈 2. 예약 변화량 (이전 대비)", mode="변화"),
                unsafe_allow_html=True)
    st.markdown(render_master_table(curr, prev, title="🔔 3. 판도 변화 감지", mode="판도변화"),
                unsafe_allow_html=True)

    st.divider()

    # 엑셀 다운로드
    st.subheader("📥 엑셀 다운로드")

    def generate_excel():
        output = io.BytesIO()
        export_data = []
        for _, row in st.session_state.today_df.iterrows():
            d = row['Date']
            rid = row['RoomID']
            occ, bar, b_price, _ = get_final_values(rid, d, row['Available'], row['Total'])
            export_data.append({
                "날짜": d.strftime('%Y-%m-%d'),
                "객실타입": rid,
                "잔여객실": row['Available'],
                "전체객실": row['Total'],
                "점유율(%)": round(occ, 1),
                "적용BAR": bar,
                "판매가": b_price
            })
        df_export = pd.DataFrame(export_data)
        with pd.ExcelWriter(output) as writer:
            df_export.to_excel(writer, index=False, sheet_name='요금현황')
        return output.getvalue()

    st.download_button(
        "📊 엑셀 다운로드",
        data=generate_excel(),
        file_name=f"Amber_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    # 초기 안내 화면
    st.info("👈 사이드바에서 잔여객실 파일을 업로드하거나 과거 기록을 불러오세요.")

    st.markdown("""
    ### 🎯 사용 방법

    1. **잔여객실 엑셀 파일을 사이드바에서 업로드**
    2. **자동으로 가장 최근 저장본과 비교**되어 3개 표가 표시됩니다
       - 📊 BAR 요금 현황
       - 📈 예약 변화량
       - 🔔 판도 변화 감지
    3. **"🚀 오늘 내역 저장"** 버튼을 눌러 Firebase에 기록
    4. **엑셀로 다운로드** 가능

    ---

    ### 🔮 다음 단계 (곧 추가될 기능)

    - 시장 시그널 반영 시뮬레이터 (조선 40만원 / 항공 7만원 기준)
    - 기회비용 누적 분석
    - 경쟁사 & 항공권 실시간 모니터링
    - PDF 보고서 생성
    """)
