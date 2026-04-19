"""
🏨 Amber Command Center v2.0
엠버퓨어힐 통합 수익관리 시스템

[2단계] 시뮬레이터 추가
- 비밀번호 로그인
- 잔여객실 파일 업로드
- BAR 요금 현황 / 변화량 / 판도 변화
- 🔮 시뮬레이터 탭 (시장 시그널 반영 BAR)
- Firebase 저장 & 엑셀 다운로드
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import math
import re
import io

# ============================================================
# 1. 페이지 설정
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

if not check_password():
    st.stop()

# ============================================================
# 3. Firebase 초기화 (프로젝트 2개)
# ============================================================
existing_apps = [a.name for a in firebase_admin._apps.values()] if firebase_admin._apps else []

# 호텔 예약용
if "hotel_app" not in existing_apps:
    try:
        cred_h = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred_h, name="hotel_app")
    except Exception as e:
        st.error(f"호텔 Firebase 연결 실패: {e}")
        st.stop()

# 항공/경쟁사용
if "flight_app" not in existing_apps:
    try:
        cred_f = credentials.Certificate(dict(st.secrets["firebase_flight"]))
        firebase_admin.initialize_app(cred_f, name="flight_app")
    except Exception as e:
        st.warning(f"항공 Firebase 연결 실패 (시뮬레이터 기능 제한): {e}")

try:
    db = firestore.client(app=firebase_admin.get_app("hotel_app"))
except:
    st.error("호텔 DB 연결 실패")
    st.stop()

try:
    db_flight = firestore.client(app=firebase_admin.get_app("flight_app"))
except:
    db_flight = None

# ============================================================
# 4. 전역 설정
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
SIM_BAR_COLORS = {
    "BAR0": "#0D47A1",
    "BAR1": "#1565C0", "BAR2": "#1976D2", "BAR3": "#42A5F5", "BAR4": "#90CAF9",
    "BAR5": "#26A69A", "BAR6": "#4DB6AC", "BAR7": "#80CBC4", "BAR8": "#B2DFDB",
}

WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]
ALL_ROOMS = DYNAMIC_ROOMS + FIXED_ROOMS
BAR_LEVELS = ["BAR8", "BAR7", "BAR6", "BAR5", "BAR4", "BAR3", "BAR2", "BAR1", "BAR0"]

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
# 5. 로직 함수
# ============================================================
def get_season_details(date_obj):
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
    else:
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

def bar_to_index(bar_str):
    try:
        return BAR_LEVELS.index(bar_str)
    except:
        return 0

def index_to_bar(idx):
    idx = max(0, min(idx, len(BAR_LEVELS) - 1))
    return BAR_LEVELS[idx]

def get_final_values(room_id, date_obj, avail, total, manual_bar=None):
    type_code, season, is_weekend = get_season_details(date_obj)
    try:
        current_avail = float(avail) if pd.notna(avail) else 0.0
    except:
        current_avail = 0.0
    occ = ((total - current_avail) / total * 100) if total > 0 else 0

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

def get_sim_bar(room_id, date_obj, avail, total,
                josun_price, flight_price, parnas_price,
                josun_threshold, flight_threshold,
                josun_prev_price=None):
    occ, sys_bar, sys_price, _ = get_final_values(room_id, date_obj, avail, total)

    if room_id not in DYNAMIC_ROOMS:
        return occ, sys_bar, sys_price, 0, "고정요금"

    sys_idx = bar_to_index(sys_bar)
    boost = 0
    signals = []

    if josun_price and josun_price >= josun_threshold:
        boost += 1
        signals.append(f"조선 {int(josun_price):,}↑")

    if flight_price and flight_price >= flight_threshold:
        boost += 1
        signals.append(f"항공 {int(flight_price):,}↑")

    if josun_prev_price and josun_price:
        try:
            drop_rate = (josun_prev_price - josun_price) / josun_prev_price
            if drop_rate >= 0.15:
                boost = 0
                signals.append(f"조선급락방어({int(drop_rate*100)}%↓)")
        except:
            pass

    sim_idx = min(sys_idx + boost, len(BAR_LEVELS) - 2)
    sim_bar = index_to_bar(sim_idx)
    sim_price = PRICE_TABLE.get(room_id, {}).get(sim_bar, sys_price)

    signal_str = " + ".join(signals) if signals else "기본"
    return occ, sim_bar, sim_price, boost, signal_str

# ============================================================
# 6. 시장 데이터 로드
# ============================================================
@st.cache_data(ttl=3600)
def load_market_data():
    df_flight = pd.DataFrame()
    df_comp = pd.DataFrame()

    if db_flight is None:
        return df_flight, df_comp

    try:
        flight_docs = db_flight.collection('flight_prices').stream()
        flight_list = [{
            'date': d.to_dict().get('date', ''),
            'min_price': d.to_dict().get('min_price', 0),
            'search_date_str': d.to_dict().get('search_date_str', '')
        } for d in flight_docs]
        df_flight = pd.DataFrame(flight_list)
        if not df_flight.empty:
            df_flight['date'] = pd.to_datetime(df_flight['date'], errors='coerce').dt.date
    except:
        pass

    try:
        comp_docs = db_flight.collection('hotel_comp_prices').stream()
        comp_list = [{
            'date': d.to_dict().get('date', ''),
            'hotel_name': d.to_dict().get('hotel_name', ''),
            'price': d.to_dict().get('price', 0),
            'search_date_str': d.to_dict().get('search_date_str', '')
        } for d in comp_docs]
        df_comp = pd.DataFrame(comp_list)
        if not df_comp.empty:
            df_comp['date'] = pd.to_datetime(df_comp['date'], errors='coerce').dt.date
    except:
        pass

    return df_flight, df_comp

def get_market_price_for_date(target_date, df_flight, df_comp, search_date_str=None):
    josun_price, parnas_price, flight_price = None, None, None

    if not df_flight.empty:
        f_row = df_flight[df_flight['date'] == target_date]
        if search_date_str and 'search_date_str' in f_row.columns:
            f_row = f_row[f_row['search_date_str'] == search_date_str]
        if not f_row.empty:
            flight_price = f_row['min_price'].min()

    if not df_comp.empty:
        c_row = df_comp[df_comp['date'] == target_date]
        if search_date_str and 'search_date_str' in c_row.columns:
            c_row = c_row[c_row['search_date_str'] == search_date_str]
        josun_rows = c_row[c_row['hotel_name'].str.contains('Josun|조선', case=False, na=False)]
        parnas_rows = c_row[c_row['hotel_name'].str.contains('Parnas|파르나스', case=False, na=False)]
        if not josun_rows.empty:
            josun_price = josun_rows['price'].min()
        if not parnas_rows.empty:
            parnas_price = parnas_rows['price'].min()

    return josun_price, parnas_price, flight_price

# ============================================================
# 7. 기본 테이블 렌더러
# ============================================================
def render_master_table(current_df, prev_df, title="", mode="기준"):
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
            occ, bar, base_price, _ = get_final_values(rid, d, avail, total)

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
# 8. 시뮬레이터 비교 테이블
# ============================================================
def render_sim_comparison_table(current_df, df_flight, df_comp,
                                 josun_threshold, flight_threshold,
                                 search_date_str=None):
    if current_df.empty:
        return "<div style='padding:20px;'>데이터를 업로드하세요.</div>"

    dates = sorted(current_df['Date'].unique())

    html = "<div style='overflow-x:auto; white-space:nowrap; border:1px solid #ddd;'>"
    html += "<table style='width:100%; border-collapse:collapse; font-size:11px; min-width:1000px;'>"
    html += "<thead>"
    html += "<tr style='background:#1a1a2e; color:white;'>"
    html += "<th rowspan='3' style='border:1px solid #444; width:70px; padding:5px; position:sticky; left:0; background:#1a1a2e; z-index:2;'>객실</th>"
    for d in dates:
        html += f"<th colspan='2' style='border:1px solid #444; padding:4px; text-align:center;'>{d.strftime('%m-%d')}</th>"
    html += "</tr><tr style='background:#1a1a2e; color:white;'>"
    for d in dates:
        wd = WEEKDAYS_KR[d.weekday()]
        color = "#FF6B6B" if wd == '일' else ("#74B9FF" if wd == '토' else "white")
        html += f"<th colspan='2' style='border:1px solid #444; padding:2px; color:{color};'>{wd}</th>"
    html += "</tr><tr style='background:#2d2d44; color:white;'>"
    for d in dates:
        html += "<th style='border:1px solid #444; padding:3px; color:#FF8A80;'>실제</th>"
        html += "<th style='border:1px solid #444; padding:3px; color:#80D8FF;'>시뮬</th>"
    html += "</tr></thead><tbody>"

    html += "<tr style='background:#f5f5f5;'>"
    html += "<td style='border:1px solid #ddd; padding:4px; font-weight:bold; position:sticky; left:0; background:#f5f5f5; z-index:1; font-size:10px;'>시장 신호</td>"
    for d in dates:
        josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight, df_comp, search_date_str)
        j_color = "#C62828" if (josun_p and josun_p >= josun_threshold) else "#555"
        f_color = "#1565C0" if (flight_p and flight_p >= flight_threshold) else "#555"
        j_txt = f"<span style='color:{j_color}; font-weight:bold;'>조선 {int(josun_p):,}</span>" if josun_p else "<span style='color:#aaa;'>조선 -</span>"
        f_txt = f"<span style='color:{f_color}; font-weight:bold;'>항공 {int(flight_p):,}</span>" if flight_p else "<span style='color:#aaa;'>항공 -</span>"
        p_txt = f"<span style='color:#555;'>파르나스 {int(parnas_p):,}</span>" if parnas_p else ""
        html += f"<td colspan='2' style='border:1px solid #ddd; padding:3px; text-align:center; font-size:10px;'>{j_txt}<br>{f_txt}<br>{p_txt}</td>"
    html += "</tr>"

    for rid in DYNAMIC_ROOMS:
        html += "<tr>"
        html += f"<td style='border:1px solid #ddd; padding:6px; font-weight:bold; background:#fff; position:sticky; left:0; z-index:1;'>{rid}</td>"
        for d in dates:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                html += "<td style='border:1px solid #ddd; text-align:center;'>-</td>"
                html += "<td style='border:1px solid #ddd; text-align:center;'>-</td>"
                continue

            avail = curr_match.iloc[0]['Available']
            total = curr_match.iloc[0]['Total']
            occ, real_bar, real_price, _ = get_final_values(rid, d, avail, total)

            josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight, df_comp, search_date_str)
            prev_week_date = d - timedelta(days=7)
            josun_prev, _, _ = get_market_price_for_date(prev_week_date, df_flight, df_comp, search_date_str)

            _, sim_bar, sim_price, boost, signal_str = get_sim_bar(
                rid, d, avail, total,
                josun_p, flight_p, parnas_p,
                josun_threshold, flight_threshold,
                josun_prev_price=josun_prev
            )

            real_bg = BAR_GRADIENT_COLORS.get(real_bar, "#fff")
            real_style = f"border:1px solid #ddd; padding:5px; text-align:center; background:{real_bg}; font-size:11px;"
            real_content = f"<b>{real_bar}</b><br><span style='font-size:10px;'>{real_price:,}</span>"

            sim_bg = SIM_BAR_COLORS.get(sim_bar, "#fff")
            diff = sim_price - real_price
            sim_style = f"border:1px solid #ddd; padding:5px; text-align:center; background:{sim_bg}; color:white; font-size:11px;"

            if boost > 0:
                sim_style += "border:2px solid #FFD700;"
                diff_txt = f"<span style='color:#FFD700; font-size:9px;'>+{boost}단계 +{diff:,}</span>"
            else:
                diff_txt = ""

            sim_content = f"<b>{sim_bar}</b><br><span style='font-size:10px;'>{sim_price:,}</span><br>{diff_txt}"
            html += f"<td style='{real_style}'>{real_content}</td>"
            html += f"<td style='{sim_style}'>{sim_content}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    return html

# ============================================================
# 9. 파일 파서
# ============================================================
def robust_date_parser(d_val):
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
    docs = db.collection("daily_snapshots").order_by("save_time", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        d_dict = doc.to_dict()
        df = pd.DataFrame(d_dict['data'])
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df, d_dict.get('work_date', '알수없음')
    return pd.DataFrame(), None

# ============================================================
# 10. 세션 초기화
# ============================================================
if 'today_df' not in st.session_state:
    st.session_state.today_df = pd.DataFrame()
if 'prev_df' not in st.session_state:
    st.session_state.prev_df = pd.DataFrame()
if 'compare_label' not in st.session_state:
    st.session_state.compare_label = ""

df_flight_all, df_comp_all = load_market_data()

# ============================================================
# 11. UI
# ============================================================
st.title("🏨 Amber Command Center")
st.caption("v2.0 · 통합 수익관리 + 시뮬레이터")

with st.sidebar:
    st.header("📅 과거 기록 조회")
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

    st.header("🎯 시뮬레이터 기준값")
    st.caption("여기 값을 바꾸면 시뮬레이터가 즉시 갱신됩니다.")

    josun_threshold = st.number_input(
        "그랜드 조선 임계가 (원)",
        min_value=100000, max_value=1000000,
        value=400000, step=10000,
        help="이 가격 이상이면 시장 강세 → BAR +1"
    )
    flight_threshold = st.number_input(
        "항공권 최저가 임계가 (원)",
        min_value=10000, max_value=300000,
        value=70000, step=5000,
        help="이 가격 이상이면 수요 강세 → BAR +1"
    )

    search_date_options = []
    if not df_flight_all.empty and 'search_date_str' in df_flight_all.columns:
        search_date_options = sorted(df_flight_all['search_date_str'].dropna().unique().tolist(), reverse=True)
    search_date_options = [x for x in search_date_options if x]

    selected_search_date = st.selectbox(
        "🗓️ 시장 데이터 수집일",
        ["최신"] + search_date_options
    )
    active_search_date = None if selected_search_date == "최신" else selected_search_date

    st.divider()

    st.header("📂 잔여객실 업로드")
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

# 파일 파싱
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

# 메인 탭
if not st.session_state.today_df.empty:
    curr = st.session_state.today_df
    prev = st.session_state.prev_df

    if st.session_state.compare_label:
        st.info(f"ℹ️ {st.session_state.compare_label}")

    tab1, tab2 = st.tabs(["📊 현황 & 요금관리", "🔮 시뮬레이터"])

    with tab1:
        st.markdown(render_master_table(curr, prev, title="📊 1. BAR 요금 현황", mode="기준"),
                    unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="📈 2. 예약 변화량 (이전 대비)", mode="변화"),
                    unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="🔔 3. 판도 변화 감지", mode="판도변화"),
                    unsafe_allow_html=True)

        st.divider()
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

    with tab2:
        st.subheader("🔮 시장 시그널 반영 BAR 제안")

        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.info(f"🏨 **조선 기준:** {josun_threshold:,}원 이상 → BAR +1")
        with col_info2:
            st.info(f"✈️ **항공 기준:** {flight_threshold:,}원 이상 → BAR +1")
        with col_info3:
            st.info("⚠️ 둘 동시 → +2 | 조선 -15%↓ → 방어")

        if df_flight_all.empty and df_comp_all.empty:
            st.warning("⚠️ 항공/경쟁사 데이터를 불러오지 못했습니다. (점유율 기반 기본 BAR만 표시)")
        else:
            market_status = []
            if not df_flight_all.empty:
                market_status.append(f"항공 {len(df_flight_all):,}건")
            if not df_comp_all.empty:
                market_status.append(f"경쟁사 {len(df_comp_all):,}건")
            st.success(f"✅ 시장 데이터 로드: {' · '.join(market_status)}")

        st.caption("🔴 실제 BAR (현재 시스템) | 🔵 시뮬 BAR (시장 반영 제안) | 🟡 테두리 = 상향 발동")

        sim_html = render_sim_comparison_table(
            curr, df_flight_all, df_comp_all,
            josun_threshold, flight_threshold,
            active_search_date
        )
        st.markdown(sim_html, unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 날짜별 시그널 현황")
        dates_list = sorted(curr['Date'].unique())
        signal_summary = []
        for d in dates_list:
            josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight_all, df_comp_all, active_search_date)
            josun_trigger = "🔴 발동" if (josun_p and josun_p >= josun_threshold) else "⚪ 미발동"
            flight_trigger = "🔴 발동" if (flight_p and flight_p >= flight_threshold) else "⚪ 미발동"
            total_boost = (1 if josun_p and josun_p >= josun_threshold else 0) + \
                          (1 if flight_p and flight_p >= flight_threshold else 0)
            signal_summary.append({
                "날짜": d.strftime('%m/%d'),
                "요일": WEEKDAYS_KR[d.weekday()],
                "그랜드조선": f"{int(josun_p):,}원" if josun_p else "-",
                "조선 시그널": josun_trigger,
                "파르나스": f"{int(parnas_p):,}원" if parnas_p else "-",
                "항공최저가": f"{int(flight_p):,}원" if flight_p else "-",
                "항공 시그널": flight_trigger,
                "BAR 상향": f"+{total_boost}단계" if total_boost > 0 else "-",
            })
        st.dataframe(pd.DataFrame(signal_summary), use_container_width=True, hide_index=True)

        st.divider()
        with st.expander("💡 시뮬레이터는 어떻게 작동하나요?"):
            st.markdown(f"""
            **기본 원리**: 현재 시스템이 계산한 BAR(자사 점유율 기반)에 **시장 시그널을 더해** 제안 BAR을 만듭니다.

            **시그널 규칙**:
            - **그랜드 조선** 가격이 **{josun_threshold:,}원** 이상 → BAR 1단계 상향
            - **항공권 최저가**가 **{flight_threshold:,}원** 이상 → BAR 1단계 상향
            - 두 조건 동시 충족 → BAR 2단계 상향
            - 조선이 전주 대비 15% 이상 **급락** → 방어 (상향 안 함)

            **색상 의미**:
            - 🔴 빨간계열 = 실제 적용된 BAR (오늘 시스템에서 판매 중)
            - 🔵 파란계열 = 시뮬레이터가 제안하는 BAR
            - 🟡 금색 테두리 = 시그널 발동 (높여야 한다는 판단)

            **파르나스는 참고용**입니다. 트리거로는 쓰이지 않지만 시장 천장을 보는 용도로 함께 표시됩니다.
            """)

else:
    st.info("👈 사이드바에서 잔여객실 파일을 업로드하거나 과거 기록을 불러오세요.")
    st.markdown("""
    ### 🎯 사용 방법

    1. **잔여객실 엑셀 파일 업로드** → 자동으로 최근 저장본과 비교
    2. **📊 현황 탭** → 1단계의 기존 기능
    3. **🔮 시뮬레이터 탭** → 시장 시그널 반영 BAR 제안
       - 조선 40만원 / 항공 7만원 기준
       - 사이드바에서 임계값 조정 가능

    ### 🚀 다음 단계 (3단계 예정)
    - 💸 기회비용 분석 (금액 누적)
    - 📊 시장 트렌드 차트
    - 📄 PDF 보고서
    """)
