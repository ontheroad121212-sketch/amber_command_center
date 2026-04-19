"""
🏨 Amber Command Center v7.0
엠버퓨어힐 통합 수익관리 시스템

[7단계] 누적 추적 + 정확도 검증 + 객실 민감도 + Fixed 수기 인상 알림
- 📈 누적 대시보드 (30/60/90일 트렌드)
- 🔄 시뮬레이터 정확도 검증 (A+B+C 3가지 방식)
- 🎯 객실타입별 민감도 커스터마이징
- 🚨 Fixed 객실 수기 인상 알림 (75%/85%)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import math
import re
import io
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import calendar

# ============================================================
# 1. 페이지 설정
# ============================================================
st.set_page_config(page_title="Amber Command Center", page_icon="🏨", layout="wide")

# ============================================================
# 2. 비밀번호
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
# 3. Firebase 초기화
# ============================================================
existing_apps = [a.name for a in firebase_admin._apps.values()] if firebase_admin._apps else []

if "hotel_app" not in existing_apps:
    try:
        cred_h = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred_h, name="hotel_app")
    except Exception as e:
        st.error(f"호텔 Firebase 연결 실패: {e}")
        st.stop()

if "flight_app" not in existing_apps:
    try:
        cred_f = credentials.Certificate(dict(st.secrets["firebase_flight"]))
        firebase_admin.initialize_app(cred_f, name="flight_app")
    except Exception as e:
        st.warning(f"항공 Firebase 연결 실패: {e}")

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
    "BAR0": "#B71C1C", "BAR1": "#D32F2F", "BAR2": "#EF5350", "BAR3": "#FF8A65",
    "BAR4": "#FFB199", "BAR5": "#81C784", "BAR6": "#A5D6A7", "BAR7": "#C8E6C9", "BAR8": "#E8F5E9",
}
BAR_LIGHT_COLORS = {
    "BAR0": "#FFCDD2", "BAR1": "#FFEBEE", "BAR2": "#FFEBEE", "BAR3": "#FFF3E0",
    "BAR4": "#FFF3E0", "BAR5": "#E8F5E9", "BAR6": "#E8F5E9", "BAR7": "#F1F8E9", "BAR8": "#F1F8E9",
}
SIM_BAR_COLORS = {
    "BAR0": "#0D47A1", "BAR1": "#1565C0", "BAR2": "#1976D2", "BAR3": "#42A5F5",
    "BAR4": "#90CAF9", "BAR5": "#26A69A", "BAR6": "#4DB6AC", "BAR7": "#80CBC4", "BAR8": "#B2DFDB",
}

WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]
ALL_ROOMS = DYNAMIC_ROOMS + FIXED_ROOMS
BAR_LEVELS = ["BAR8", "BAR7", "BAR6", "BAR5", "BAR4", "BAR3", "BAR2", "BAR1", "BAR0"]

# 🎯 객실별 민감도 기본값
DEFAULT_SENSITIVITY = {
    "FDB": 1.0,
    "FDE": 1.0,
    "HDP": 1.2,
    "HDT": 1.3,
    "HDF": 0.7,
}

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
    try: return BAR_LEVELS.index(bar_str)
    except: return 0

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

# ============================================================
# 6. 📝 메모 시스템
# ============================================================
@st.cache_data(ttl=60)
def load_all_notes():
    try:
        docs = db.collection("notes").stream()
        notes = {}
        for doc in docs:
            d = doc.to_dict()
            notes[doc.id] = {
                'content': d.get('content', ''),
                'tag': d.get('tag', '일반'),
                'updated_at': d.get('updated_at', ''),
            }
        return notes
    except:
        return {}

def save_note(key, content, tag="일반"):
    try:
        if content.strip():
            db.collection("notes").document(key).set({
                'content': content, 'tag': tag,
                'updated_at': datetime.now().isoformat(),
            })
        else:
            db.collection("notes").document(key).delete()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"메모 저장 실패: {e}")
        return False

def get_note_key(date_obj, room_id=None):
    if room_id:
        return f"{date_obj.strftime('%Y-%m-%d')}_{room_id}"
    return f"{date_obj.strftime('%Y-%m-%d')}_ALL"

# ============================================================
# 7. 🗓️ 이벤트 캘린더
# ============================================================
@st.cache_data(ttl=60)
def load_events():
    try:
        docs = db.collection("events").stream()
        events = []
        for doc in docs:
            d = doc.to_dict()
            events.append({
                'id': doc.id, 'name': d.get('name', ''),
                'start_date': d.get('start_date', ''), 'end_date': d.get('end_date', ''),
                'impact': d.get('impact', 1), 'note': d.get('note', ''),
            })
        return events
    except:
        return []

def save_event(event_id, name, start_d, end_d, impact, note):
    try:
        db.collection("events").document(event_id).set({
            'name': name, 'start_date': start_d.strftime('%Y-%m-%d'),
            'end_date': end_d.strftime('%Y-%m-%d'), 'impact': impact, 'note': note,
        })
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"이벤트 저장 실패: {e}")
        return False

def delete_event(event_id):
    try:
        db.collection("events").document(event_id).delete()
        st.cache_data.clear()
        return True
    except:
        return False

def get_event_boost_for_date(target_date, events):
    total_boost = 0
    active_events = []
    for ev in events:
        try:
            start = datetime.strptime(ev['start_date'], '%Y-%m-%d').date()
            end = datetime.strptime(ev['end_date'], '%Y-%m-%d').date()
            if start <= target_date <= end:
                total_boost += ev.get('impact', 1)
                active_events.append(ev['name'])
        except:
            continue
    return total_boost, active_events

# ============================================================
# 8. 🎯 객실별 민감도 저장/불러오기
# ============================================================
@st.cache_data(ttl=300)
def load_sensitivity():
    try:
        doc = db.collection("settings").document("sensitivity").get()
        if doc.exists:
            return doc.to_dict()
    except:
        pass
    return DEFAULT_SENSITIVITY.copy()

def save_sensitivity(sens_dict):
    try:
        db.collection("settings").document("sensitivity").set(sens_dict)
        st.cache_data.clear()
        return True
    except:
        return False

# ============================================================
# 9. 시뮬레이터 (민감도 반영)
# ============================================================
def get_sim_bar(room_id, date_obj, avail, total,
                josun_price, flight_price, parnas_price,
                josun_threshold, flight_threshold,
                josun_prev_price=None, events=None, sensitivity=None):
    occ, sys_bar, sys_price, _ = get_final_values(room_id, date_obj, avail, total)

    if room_id not in DYNAMIC_ROOMS:
        return occ, sys_bar, sys_price, 0, "고정요금"

    sys_idx = bar_to_index(sys_bar)
    base_boost = 0
    signals = []

    if josun_price and josun_price >= josun_threshold:
        base_boost += 1
        signals.append(f"조선 {int(josun_price):,}↑")

    if flight_price and flight_price >= flight_threshold:
        base_boost += 1
        signals.append(f"항공 {int(flight_price):,}↑")

    if josun_prev_price and josun_price:
        try:
            drop_rate = (josun_prev_price - josun_price) / josun_prev_price
            if drop_rate >= 0.15:
                base_boost = 0
                signals.append(f"조선급락방어({int(drop_rate*100)}%↓)")
        except:
            pass

    if events:
        event_boost, event_names = get_event_boost_for_date(date_obj, events)
        if event_boost > 0:
            base_boost += event_boost
            signals.append(f"이벤트({', '.join(event_names)}) +{event_boost}")

    # 🎯 객실별 민감도 적용
    if sensitivity and room_id in sensitivity:
        sens_factor = sensitivity[room_id]
        final_boost = round(base_boost * sens_factor)
        if sens_factor != 1.0 and base_boost > 0:
            signals.append(f"민감도×{sens_factor}")
    else:
        final_boost = base_boost

    sim_idx = min(sys_idx + final_boost, len(BAR_LEVELS) - 2)
    sim_bar = index_to_bar(sim_idx)
    sim_price = PRICE_TABLE.get(room_id, {}).get(sim_bar, sys_price)

    signal_str = " + ".join(signals) if signals else "기본"
    return occ, sim_bar, sim_price, final_boost, signal_str

# ============================================================
# 10. 🚨 Fixed 객실 수기 인상 알림
# ============================================================
def get_fixed_room_alerts(current_df, events=None):
    """전체 점유율 기준 Fixed 객실 수기 인상 권장 알림"""
    if current_df.empty:
        return []

    alerts = []
    dates = sorted(current_df['Date'].unique())

    for d in dates:
        day_data = current_df[current_df['Date'] == d]
        total_avail = day_data['Available'].sum()
        total_rooms = day_data['Total'].sum()

        if total_rooms == 0:
            continue

        overall_occ = ((total_rooms - total_avail) / total_rooms * 100)

        # 이벤트 여부
        _, event_names = get_event_boost_for_date(d, events or [])
        has_event = len(event_names) > 0

        if overall_occ >= 85:
            alerts.append({
                '날짜': d,
                '요일': WEEKDAYS_KR[d.weekday()],
                '전체점유율': round(overall_occ, 1),
                '단계': '🚨 강력 권장',
                '메시지': 'Fixed 객실 수기 인상 긴급',
                '이벤트': ', '.join(event_names) if has_event else '',
                'level': 'critical'
            })
        elif overall_occ >= 75:
            alerts.append({
                '날짜': d,
                '요일': WEEKDAYS_KR[d.weekday()],
                '전체점유율': round(overall_occ, 1),
                '단계': '🔔 검토 권장',
                '메시지': 'Fixed 객실 수기 인상 검토',
                '이벤트': ', '.join(event_names) if has_event else '',
                'level': 'warning'
            })

    return alerts

# ============================================================
# 11. 시장 데이터
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
# 12. 기회비용 계산
# ============================================================
def calculate_opportunity_cost(current_df, df_flight, df_comp,
                                josun_threshold, flight_threshold,
                                search_date_str=None, events=None, sensitivity=None):
    records = []
    dates = sorted(current_df['Date'].unique())
    for d in dates:
        josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight, df_comp, search_date_str)
        prev_week_date = d - timedelta(days=7)
        josun_prev, _, _ = get_market_price_for_date(prev_week_date, df_flight, df_comp, search_date_str)
        for rid in DYNAMIC_ROOMS:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                continue
            avail = curr_match.iloc[0]['Available']
            total = curr_match.iloc[0]['Total']
            occ, real_bar, real_price, _ = get_final_values(rid, d, avail, total)
            _, sim_bar, sim_price, boost, signal_str = get_sim_bar(
                rid, d, avail, total,
                josun_p, flight_p, parnas_p,
                josun_threshold, flight_threshold,
                josun_prev_price=josun_prev, events=events, sensitivity=sensitivity
            )
            try:
                sold_rooms = max(0, float(total) - (float(avail) if pd.notna(avail) else 0))
            except:
                sold_rooms = 0
            price_diff = sim_price - real_price
            opp_cost = price_diff * sold_rooms
            records.append({
                '날짜': d, '요일': WEEKDAYS_KR[d.weekday()], '객실타입': rid,
                '점유율(%)': round(occ, 1), '판매객실수': int(sold_rooms),
                '실제BAR': real_bar, '실제단가': int(real_price),
                '시뮬BAR': sim_bar, '시뮬단가': int(sim_price),
                '단가차이': int(price_diff), '기회비용': int(opp_cost),
                'BAR상승': boost, '시그널': signal_str,
            })
    return pd.DataFrame(records)

def get_our_avg_price_for_dates(current_df, target_dates):
    result = {}
    for d in target_dates:
        prices = []
        for rid in DYNAMIC_ROOMS:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                continue
            avail = curr_match.iloc[0]['Available']
            total = curr_match.iloc[0]['Total']
            _, _, price, _ = get_final_values(rid, d, avail, total)
            if price > 0:
                prices.append(price)
        result[d] = sum(prices) / len(prices) if prices else None
    return result

def generate_today_alerts(opp_df, notes, events, top_n=5):
    if opp_df.empty:
        return []
    triggered = opp_df[opp_df['BAR상승'] > 0].copy()
    if triggered.empty:
        return []
    daily = triggered.groupby('날짜').agg({
        '기회비용': 'sum', '시그널': lambda x: x.iloc[0], 'BAR상승': 'max'
    }).reset_index()
    daily = daily.sort_values('기회비용', ascending=False).head(top_n)
    alerts = []
    for _, row in daily.iterrows():
        d = row['날짜']
        day_note_key = get_note_key(d)
        has_note = day_note_key in notes
        note_preview = notes[day_note_key]['content'][:30] if has_note else ""
        _, event_names = get_event_boost_for_date(d, events)
        alerts.append({
            '날짜': d, '요일': WEEKDAYS_KR[d.weekday()],
            'BAR상승': int(row['BAR상승']), '시그널': row['시그널'],
            '기회비용': int(row['기회비용']),
            '메모있음': has_note, '메모미리보기': note_preview,
            '이벤트': ', '.join(event_names) if event_names else '',
        })
    return alerts

# ============================================================
# 13. 📈 누적 추적 대시보드 - 스냅샷 히스토리 로드
# ============================================================
@st.cache_data(ttl=300)
def load_all_snapshots_history(days_back=90):
    """지난 N일간의 모든 스냅샷을 불러와서 DataFrame으로 변환"""
    try:
        cutoff = (date.today() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        docs = db.collection("daily_snapshots").where("work_date", ">=", cutoff).stream()
        all_records = []
        for doc in docs:
            d_dict = doc.to_dict()
            work_date = d_dict.get('work_date')
            save_time = d_dict.get('save_time', '')
            if 'data' in d_dict:
                for row in d_dict['data']:
                    row['_work_date'] = work_date
                    row['_save_time'] = save_time
                    all_records.append(row)
        return all_records
    except:
        return []

def calculate_cumulative_metrics(snapshots_list, df_flight, df_comp,
                                  josun_threshold, flight_threshold,
                                  events, sensitivity, search_date_str=None):
    """최근 N일간 누적 기회비용 + 트렌드 계산"""
    if not snapshots_list:
        return pd.DataFrame()

    # work_date별로 스냅샷 집계
    snapshot_df = pd.DataFrame(snapshots_list)
    if snapshot_df.empty or '_work_date' not in snapshot_df.columns:
        return pd.DataFrame()

    results = []
    for work_date, group in snapshot_df.groupby('_work_date'):
        # 해당 work_date의 가장 최신 스냅샷만 사용
        if '_save_time' in group.columns:
            latest_time = group['_save_time'].max()
            group = group[group['_save_time'] == latest_time]

        df = group.copy()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date

        try:
            opp = calculate_opportunity_cost(
                df, df_flight, df_comp,
                josun_threshold, flight_threshold,
                search_date_str, events, sensitivity
            )
            if not opp.empty:
                positive_opp = opp[opp['기회비용'] > 0]['기회비용'].sum()
                trigger_count = (opp['BAR상승'] > 0).sum()
                results.append({
                    'work_date': work_date,
                    'opportunity_cost': int(positive_opp),
                    'trigger_count': int(trigger_count),
                    'affected_days': opp[opp['기회비용'] > 0]['날짜'].nunique()
                })
        except:
            continue

    return pd.DataFrame(results)

# ============================================================
# 14. 🔄 정확도 검증 (A + B + C)
# ============================================================
def verify_simulator_accuracy(snapshots_list, df_flight, df_comp,
                               josun_threshold, flight_threshold,
                               events, sensitivity, search_date_str=None):
    """
    시뮬 제안 후 7일 뒤의 실제 결과와 비교.
    - A: 예약 집중도 (시뮬 상향일의 예약 증가율)
    - B: 마감 매출 (시뮬 상향일의 최종 매출이 평균 이상인가)
    - C: 점유율 일치 (시뮬 BAR 단계와 실제 점유율 단계 일치)
    """
    if not snapshots_list:
        return {'verification_ready': False, 'message': '데이터가 아직 쌓이지 않았습니다.'}

    snapshot_df = pd.DataFrame(snapshots_list)
    if snapshot_df.empty or '_work_date' not in snapshot_df.columns:
        return {'verification_ready': False, 'message': '데이터 없음'}

    # work_date별로 그룹화
    work_dates = sorted(snapshot_df['_work_date'].unique())
    if len(work_dates) < 2:
        return {'verification_ready': False,
                'message': f'최소 2일 이상의 스냅샷이 필요합니다. 현재 {len(work_dates)}일분.'}

    # 각 work_date에서 시뮬 제안했던 날짜들 수집
    a_total, a_correct = 0, 0  # 예약 집중도
    b_total, b_correct = 0, 0  # 마감 매출
    c_total, c_correct = 0, 0  # 점유율 일치

    verification_details = []

    for i, work_date in enumerate(work_dates[:-1]):  # 마지막은 비교 대상 없음
        # 기준일의 스냅샷
        base_data = snapshot_df[snapshot_df['_work_date'] == work_date].copy()
        if '_save_time' in base_data.columns:
            latest = base_data['_save_time'].max()
            base_data = base_data[base_data['_save_time'] == latest]

        if 'Date' in base_data.columns:
            base_data['Date'] = pd.to_datetime(base_data['Date']).dt.date

        # 시뮬 제안 계산
        try:
            base_opp = calculate_opportunity_cost(
                base_data, df_flight, df_comp,
                josun_threshold, flight_threshold,
                search_date_str, events, sensitivity
            )
        except:
            continue

        if base_opp.empty:
            continue

        triggered = base_opp[base_opp['BAR상승'] > 0]
        if triggered.empty:
            continue

        # 이후 스냅샷 중 가장 최신 (현재와 가까운 것)
        later_dates = [wd for wd in work_dates if wd > work_date]
        if not later_dates:
            continue

        later_wd = later_dates[-1]  # 가장 최신
        later_data = snapshot_df[snapshot_df['_work_date'] == later_wd].copy()
        if '_save_time' in later_data.columns:
            latest = later_data['_save_time'].max()
            later_data = later_data[later_data['_save_time'] == latest]

        if 'Date' in later_data.columns:
            later_data['Date'] = pd.to_datetime(later_data['Date']).dt.date

        # 시뮬 제안한 (날짜, 객실) 조합별로 검증
        for _, trig_row in triggered.iterrows():
            check_date = trig_row['날짜']
            check_room = trig_row['객실타입']
            suggested_boost = trig_row['BAR상승']

            base_row = base_data[(base_data['Date'] == check_date) &
                                 (base_data['RoomID'] == check_room)]
            later_row = later_data[(later_data['Date'] == check_date) &
                                   (later_data['RoomID'] == check_room)]

            if base_row.empty or later_row.empty:
                continue

            base_avail = base_row.iloc[0]['Available']
            base_total = base_row.iloc[0]['Total']
            later_avail = later_row.iloc[0]['Available']
            later_total = later_row.iloc[0]['Total']

            try:
                base_avail_f = float(base_avail) if pd.notna(base_avail) else 0
                later_avail_f = float(later_avail) if pd.notna(later_avail) else 0
                base_total_f = float(base_total) if pd.notna(base_total) else 0
                later_total_f = float(later_total) if pd.notna(later_total) else 0
            except:
                continue

            # A: 예약 집중도 (추가 판매량 > 0이면 성공)
            pickup = base_avail_f - later_avail_f
            a_total += 1
            if pickup > 0:
                a_correct += 1

            # B: 최종 점유율이 평균 이상이면 성공 (마감 매출 대용)
            if later_total_f > 0:
                final_occ = ((later_total_f - later_avail_f) / later_total_f) * 100
                b_total += 1
                if final_occ >= 50:  # 평균 50% 이상이면 매출 확보로 간주
                    b_correct += 1

            # C: 점유율 단계 일치
            if later_total_f > 0:
                final_occ = ((later_total_f - later_avail_f) / later_total_f) * 100
                c_total += 1
                # 시뮬이 +1 이상 제안했고 실제 점유율이 50% 이상이면 정확
                if suggested_boost >= 1 and final_occ >= 50:
                    c_correct += 1
                elif suggested_boost >= 2 and final_occ >= 70:
                    c_correct += 1

            verification_details.append({
                '검증일': work_date,
                '대상일': check_date,
                '객실': check_room,
                '시뮬제안': f"+{suggested_boost}",
                '실제픽업': int(pickup),
                '최종점유율': f"{((later_total_f-later_avail_f)/later_total_f*100):.0f}%" if later_total_f > 0 else "-"
            })

    def pct(correct, total):
        return (correct / total * 100) if total > 0 else 0

    return {
        'verification_ready': True,
        'a_score': pct(a_correct, a_total),
        'a_correct': a_correct,
        'a_total': a_total,
        'b_score': pct(b_correct, b_total),
        'b_correct': b_correct,
        'b_total': b_total,
        'c_score': pct(c_correct, c_total),
        'c_correct': c_correct,
        'c_total': c_total,
        'details': verification_details[:50]  # 최근 50건만
    }

# ============================================================
# 15. 파일 파서
# ============================================================
def robust_date_parser(d_val):
    if pd.isna(d_val): return None
    try:
        if isinstance(d_val, (int, float)):
            return (pd.to_datetime('1899-12-30') + pd.to_timedelta(d_val, 'D')).date()
        s = str(d_val).strip().replace('.', '-').replace('/', '-').replace(' ', '')
        match = re.search(r'(\d{1,2})-(\d{1,2})', s)
        if match:
            return date(2026, int(match.group(1)), int(match.group(2)))
    except: pass
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
# 16. 메모 입력 위젯
# ============================================================
def render_note_input(key_id, label="메모", notes=None, show_tag=True):
    if notes is None: notes = {}
    existing = notes.get(key_id, {})
    existing_content = existing.get('content', '')
    existing_tag = existing.get('tag', '일반')
    col1, col2 = st.columns([4, 1]) if show_tag else (st.container(), None)
    with col1:
        new_content = st.text_area(label, value=existing_content, key=f"note_input_{key_id}",
                                    height=80, placeholder="예: 총지배인 지시로 유지")
    if show_tag and col2:
        with col2:
            tag_options = ['일반', '의사결정', '경고', '대기']
            new_tag = st.selectbox("태그", tag_options,
                index=tag_options.index(existing_tag) if existing_tag in tag_options else 0,
                key=f"note_tag_{key_id}")
    else:
        new_tag = existing_tag
    if st.button("💾 저장", key=f"note_save_{key_id}"):
        if save_note(key_id, new_content, new_tag):
            st.success("저장되었습니다!")
            st.rerun()

# ============================================================
# 17. 기본 렌더러들
# ============================================================
def render_master_table(current_df, prev_df, title="", mode="기준"):
    if current_df.empty:
        return "<div style='padding:20px;'>데이터를 업로드하세요.</div>"
    dates = sorted(current_df['Date'].unique())
    row_padding = "8px"; header_padding = "5px"; font_size = "11px"
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
            avail = curr_match.iloc[0]['Available']; total = curr_match.iloc[0]['Total']
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
                else: content = "-"
            elif mode == "판도변화":
                curr_b = str(bar).strip() if bar else ""
                prev_b = str(prev_bar).strip() if prev_bar else ""
                if prev_bar is not None and prev_b != curr_b:
                    bg = BAR_GRADIENT_COLORS.get(bar, "#7000FF")
                    style += f"background-color: {bg}; color: white; font-weight: bold; border: 2.5px solid #000;"
                    content = f"▲ {bar}"
                else: content = bar
            html += f"<td style='{style}'>{content}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

def render_sim_comparison_table(current_df, df_flight, df_comp,
                                 josun_threshold, flight_threshold,
                                 search_date_str=None, events=None, sensitivity=None):
    if current_df.empty:
        return "<div style='padding:20px;'>데이터를 업로드하세요.</div>"
    dates = sorted(current_df['Date'].unique())
    html = "<div style='overflow-x:auto; white-space:nowrap; border:1px solid #ddd;'>"
    html += "<table style='width:100%; border-collapse:collapse; font-size:11px; min-width:1000px;'>"
    html += "<thead><tr style='background:#1a1a2e; color:white;'>"
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
    html += "<td style='border:1px solid #ddd; padding:4px; font-weight:bold; position:sticky; left:0; background:#f5f5f5; z-index:1; font-size:10px;'>시장+이벤트</td>"
    for d in dates:
        josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight, df_comp, search_date_str)
        j_color = "#C62828" if (josun_p and josun_p >= josun_threshold) else "#555"
        f_color = "#1565C0" if (flight_p and flight_p >= flight_threshold) else "#555"
        j_txt = f"<span style='color:{j_color}; font-weight:bold;'>조선 {int(josun_p):,}</span>" if josun_p else "<span style='color:#aaa;'>조선 -</span>"
        f_txt = f"<span style='color:{f_color}; font-weight:bold;'>항공 {int(flight_p):,}</span>" if flight_p else "<span style='color:#aaa;'>항공 -</span>"
        ev_boost, ev_names = get_event_boost_for_date(d, events or [])
        ev_txt = f"<span style='color:#FF6F00; font-weight:bold;'>🎉 {ev_names[0][:6]}</span>" if ev_names else ""
        html += f"<td colspan='2' style='border:1px solid #ddd; padding:3px; text-align:center; font-size:10px;'>{j_txt}<br>{f_txt}<br>{ev_txt}</td>"
    html += "</tr>"

    for rid in DYNAMIC_ROOMS:
        sens_val = (sensitivity or {}).get(rid, 1.0)
        sens_label = f" <span style='font-size:9px; color:#888;'>×{sens_val}</span>" if sens_val != 1.0 else ""
        html += "<tr>"
        html += f"<td style='border:1px solid #ddd; padding:6px; font-weight:bold; background:#fff; position:sticky; left:0; z-index:1;'>{rid}{sens_label}</td>"
        for d in dates:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                html += "<td style='border:1px solid #ddd; text-align:center;'>-</td>"
                html += "<td style='border:1px solid #ddd; text-align:center;'>-</td>"
                continue
            avail = curr_match.iloc[0]['Available']; total = curr_match.iloc[0]['Total']
            occ, real_bar, real_price, _ = get_final_values(rid, d, avail, total)
            josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight, df_comp, search_date_str)
            prev_week_date = d - timedelta(days=7)
            josun_prev, _, _ = get_market_price_for_date(prev_week_date, df_flight, df_comp, search_date_str)
            _, sim_bar, sim_price, boost, signal_str = get_sim_bar(
                rid, d, avail, total, josun_p, flight_p, parnas_p,
                josun_threshold, flight_threshold,
                josun_prev_price=josun_prev, events=events, sensitivity=sensitivity
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
            else: diff_txt = ""
            sim_content = f"<b>{sim_bar}</b><br><span style='font-size:10px;'>{sim_price:,}</span><br>{diff_txt}"
            html += f"<td style='{real_style}'>{real_content}</td>"
            html += f"<td style='{sim_style}'>{sim_content}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# ============================================================
# 18. PDF 생성
# ============================================================
def generate_pdf_report(opp_df, trend_df, period_label,
                         josun_threshold, flight_threshold,
                         start_date, end_date):
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.set_fill_color(26, 42, 68)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(0, 95, 210, 4, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 32)
    pdf.set_xy(20, 115)
    pdf.cell(0, 15, "AMBER PURE HILL", ln=True)
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 12, "Revenue Opportunity", ln=True)
    pdf.cell(0, 12, "Analysis Report", ln=True)
    pdf.set_font("helvetica", "", 11)
    pdf.ln(50)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(0, 8, f"PERIOD: {period_label}", ln=True, align='R')
    pdf.cell(0, 8, f"REPORT DATE: {date.today().strftime('%Y-%m-%d')}", ln=True, align='R')
    pdf.cell(0, 8, f"ANALYSIS RANGE: {start_date} ~ {end_date}", ln=True, align='R')
    pdf.set_y(270)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(166, 138, 86)
    pdf.cell(0, 10, "CONFIDENTIAL | STRATEGIC REVENUE ANALYSIS", 0, 0, 'C')

    pdf.add_page()
    pdf.set_text_color(26, 42, 68)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 12, "01. EXECUTIVE SUMMARY", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 32, 30, 2, 'F')
    pdf.ln(10)
    if not opp_df.empty:
        positive_opp = opp_df[opp_df['기회비용'] > 0]['기회비용'].sum()
        boosted_count = (opp_df['BAR상승'] > 0).sum()
        avg_diff = opp_df[opp_df['기회비용'] > 0]['단가차이'].mean() if len(opp_df[opp_df['기회비용'] > 0]) > 0 else 0
        days_affected = opp_df[opp_df['기회비용'] > 0]['날짜'].nunique()
        pdf.set_fill_color(248, 245, 240)
        pdf.rect(20, pdf.get_y(), 170, 45, 'F')
        pdf.set_xy(20, pdf.get_y() + 5)
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "ESTIMATED ADDITIONAL REVENUE", ln=True, align='C')
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(166, 138, 86)
        pdf.cell(0, 15, f"KRW {int(positive_opp):,}", ln=True, align='C')
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, "Based on simulator-proposed pricing", ln=True, align='C')
        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_fill_color(26, 42, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(95, 10, "METRIC", 1, 0, 'C', True)
        pdf.cell(75, 10, "VALUE", 1, 1, 'C', True)
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)
        rows = [
            ("Signal Trigger Count", f"{boosted_count} cases"),
            ("Days Affected", f"{days_affected} days"),
            ("Avg. Price Gap per Room", f"KRW {int(avg_diff):,}"),
            ("Analysis Period", period_label),
            ("Josun Threshold", f"KRW {josun_threshold:,}"),
            ("Flight Threshold", f"KRW {flight_threshold:,}"),
        ]
        fill_toggle = False
        for label, val in rows:
            fill = fill_toggle
            if fill: pdf.set_fill_color(248, 248, 248)
            pdf.cell(95, 9, f"  {label}", 1, 0, 'L', fill)
            pdf.cell(75, 9, val, 1, 1, 'C', fill)
            fill_toggle = not fill_toggle

        pdf.add_page()
        pdf.set_text_color(26, 42, 68)
        pdf.set_font("helvetica", "B", 20)
        pdf.cell(0, 12, "02. TOP LOSS CASES", ln=True)
        pdf.set_fill_color(166, 138, 86)
        pdf.rect(20, 32, 30, 2, 'F')
        pdf.ln(10)
        top10 = opp_df[opp_df['기회비용'] > 0].nlargest(10, '기회비용')
        if not top10.empty:
            pdf.set_font("helvetica", "B", 9)
            pdf.set_fill_color(26, 42, 68)
            pdf.set_text_color(255, 255, 255)
            headers = [("Date", 25), ("Room", 15), ("Sold", 12), ("Real BAR", 18),
                       ("Sim BAR", 18), ("Gap", 25), ("Lost (KRW)", 30), ("Signal", 27)]
            for h, w in headers:
                pdf.cell(w, 9, h, 1, 0, 'C', True)
            pdf.ln(9)
            pdf.set_font("helvetica", "", 8)
            pdf.set_text_color(0, 0, 0)
            fill_toggle = False
            for _, row in top10.iterrows():
                fill = fill_toggle
                if fill: pdf.set_fill_color(248, 248, 248)
                pdf.cell(25, 8, str(row['날짜']), 1, 0, 'C', fill)
                pdf.cell(15, 8, row['객실타입'], 1, 0, 'C', fill)
                pdf.cell(12, 8, str(int(row['판매객실수'])), 1, 0, 'C', fill)
                pdf.cell(18, 8, row['실제BAR'], 1, 0, 'C', fill)
                pdf.cell(18, 8, row['시뮬BAR'], 1, 0, 'C', fill)
                pdf.cell(25, 8, f"+{int(row['단가차이']):,}", 1, 0, 'R', fill)
                pdf.cell(30, 8, f"{int(row['기회비용']):,}", 1, 0, 'R', fill)
                pdf.cell(27, 8, str(row['시그널'])[:15], 1, 1, 'C', fill)
                fill_toggle = not fill_toggle

    pdf.add_page()
    pdf.set_text_color(26, 42, 68)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 12, "03. METHODOLOGY", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 32, 30, 2, 'F')
    pdf.ln(10)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6,
        f"Simulator adjusts BAR upward when market signals indicate strong demand: "
        f"Grand Josun >= KRW {josun_threshold:,} (+1), flight >= KRW {flight_threshold:,} (+1). "
        "Opportunity cost = (Sim price - Actual price) x Rooms sold.")
    pdf.set_y(275)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "CONFIDENTIAL | AMBER PURE HILL", 0, 0, 'C')
    return bytes(pdf.output())

# ============================================================
# 19. 세션 초기화
# ============================================================
if 'today_df' not in st.session_state: st.session_state.today_df = pd.DataFrame()
if 'prev_df' not in st.session_state: st.session_state.prev_df = pd.DataFrame()
if 'compare_label' not in st.session_state: st.session_state.compare_label = ""

df_flight_all, df_comp_all = load_market_data()
all_notes = load_all_notes()
all_events = load_events()
sensitivity = load_sensitivity()

# ============================================================
# 20. UI
# ============================================================
st.title("🏨 Amber Command Center")
st.caption("v7.0 · 누적 트렌드 + 정확도 검증 + 객실별 민감도")

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
    except: pass

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
        if found: st.success("스냅샷 로드 완료")
        else: st.warning("데이터 없음")

    st.divider()
    st.header("🎯 시뮬레이터 기준값")
    josun_threshold = st.number_input("그랜드 조선 임계가", min_value=100000, max_value=1000000, value=400000, step=10000)
    flight_threshold = st.number_input("항공권 임계가", min_value=10000, max_value=300000, value=70000, step=5000)

    search_date_options = []
    if not df_flight_all.empty and 'search_date_str' in df_flight_all.columns:
        search_date_options = sorted(df_flight_all['search_date_str'].dropna().unique().tolist(), reverse=True)
    search_date_options = [x for x in search_date_options if x]
    selected_search_date = st.selectbox("🗓️ 시장 데이터 수집일", ["최신"] + search_date_options)
    active_search_date = None if selected_search_date == "최신" else selected_search_date

    st.divider()

    # 🎯 객실 민감도 설정
    with st.expander("🎯 객실별 민감도 설정", expanded=False):
        st.caption("1.0 = 기본 / 0.5 = 둔감 / 1.5 = 민감")
        new_sens = {}
        for rid in DYNAMIC_ROOMS:
            new_sens[rid] = st.slider(
                f"{rid}",
                min_value=0.3, max_value=2.0,
                value=float(sensitivity.get(rid, 1.0)),
                step=0.1, key=f"sens_{rid}"
            )
        if st.button("💾 민감도 저장"):
            if save_sensitivity(new_sens):
                st.success("저장 완료!")
                st.rerun()

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

    st.divider()
    st.header("🗓️ 이벤트 캘린더")
    with st.expander("➕ 새 이벤트 추가", expanded=False):
        ev_name = st.text_input("이벤트 이름", placeholder="예: 유채꽃축제")
        ev_start = st.date_input("시작일", value=date.today(), key="ev_start")
        ev_end = st.date_input("종료일", value=date.today() + timedelta(days=3), key="ev_end")
        ev_impact = st.selectbox("BAR 추가 상향", [1, 2, 3], index=0)
        ev_note = st.text_input("메모", placeholder="선택")
        if st.button("이벤트 추가"):
            if ev_name:
                ev_id = f"{ev_start.strftime('%Y%m%d')}_{ev_name.replace(' ', '_')}"
                if save_event(ev_id, ev_name, ev_start, ev_end, ev_impact, ev_note):
                    st.success(f"'{ev_name}' 추가!")
                    st.rerun()

    if all_events:
        st.caption(f"등록된 이벤트: {len(all_events)}개")
        for ev in all_events:
            col_e1, col_e2 = st.columns([4, 1])
            with col_e1:
                st.markdown(f"""
                <div style='background:#FFF3E0; padding:6px 10px; border-radius:6px; border-left:4px solid #FF6F00; margin-bottom:5px; font-size:12px;'>
                    <b>{ev['name']}</b> (+{ev['impact']})<br>
                    <span style='color:#666;'>{ev['start_date']} ~ {ev['end_date']}</span>
                </div>""", unsafe_allow_html=True)
            with col_e2:
                if st.button("🗑️", key=f"del_ev_{ev['id']}"):
                    delete_event(ev['id'])
                    st.rerun()

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
                    if d_obj is None: continue
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
                st.session_state.compare_label = f"자동 DB 병합: {save_dt}"
            else:
                st.session_state.today_df = new_df
                st.session_state.prev_df = pd.DataFrame()
                st.session_state.compare_label = "첫 업로드"
        else:
            combined = pd.concat([new_df, st.session_state.today_df]).drop_duplicates(subset=['Date', 'RoomID'], keep='first')
            st.session_state.today_df = combined.sort_values(by=['Date', 'RoomID'])

# ============================================================
# 메인 영역
# ============================================================
if not st.session_state.today_df.empty:
    curr = st.session_state.today_df
    prev = st.session_state.prev_df

    alert_opp_df = calculate_opportunity_cost(
        curr, df_flight_all, df_comp_all,
        josun_threshold, flight_threshold,
        active_search_date, events=all_events, sensitivity=sensitivity
    )

    # 🚨 상단 Dynamic 알림
    alerts = generate_today_alerts(alert_opp_df, all_notes, all_events, top_n=5)
    if alerts:
        st.markdown("""
        <div style='background: linear-gradient(90deg, #FF6B6B 0%, #FFA500 100%); 
                    padding: 12px 20px; border-radius: 10px; color: white; margin-bottom: 10px;'>
            <div style='font-size: 20px; font-weight: bold;'>🚨 오늘 주목해야 할 날짜 TOP 5</div>
            <div style='font-size: 12px; opacity: 0.9;'>Dynamic 객실 (FDB/FDE/HDP/HDT/HDF) 시그널 발동 중</div>
        </div>
        """, unsafe_allow_html=True)
        alert_cols = st.columns(len(alerts))
        for idx, a in enumerate(alerts):
            with alert_cols[idx]:
                note_icon = "📝" if a['메모있음'] else "⚪"
                ev_icon = f"🎉{a['이벤트'][:5]}" if a['이벤트'] else ""
                bg_color = "#FFEBEE" if a['BAR상승'] >= 2 else "#FFF3E0"
                border_color = "#C62828" if a['BAR상승'] >= 2 else "#FF6F00"
                st.markdown(f"""
                <div style='background:{bg_color}; border:2px solid {border_color}; 
                            border-radius:10px; padding:12px; min-height:130px;'>
                    <div style='font-size:13px; color:#666; font-weight:bold;'>
                        {a['날짜'].strftime('%m/%d')} ({a['요일']}) {note_icon}
                    </div>
                    <div style='font-size:22px; color:{border_color}; font-weight:bold; margin:5px 0;'>
                        BAR +{a['BAR상승']}
                    </div>
                    <div style='font-size:11px; color:#444;'>{a['시그널'][:25]}{ev_icon}</div>
                    <div style='font-size:13px; color:#D32F2F; font-weight:bold; margin-top:6px;'>
                        ₩{a['기회비용']:,}
                    </div>
                    {f"<div style='font-size:10px; color:#888; margin-top:4px;'>📝 {a['메모미리보기']}...</div>" if a['메모있음'] else ""}
                </div>""", unsafe_allow_html=True)
        st.markdown("")

    # 🚨 Fixed 객실 수기 인상 알림
    fixed_alerts = get_fixed_room_alerts(curr, all_events)
    if fixed_alerts:
        critical = [a for a in fixed_alerts if a['level'] == 'critical']
        warning = [a for a in fixed_alerts if a['level'] == 'warning']

        st.markdown("""
        <div style='background: linear-gradient(90deg, #7B1FA2 0%, #9C27B0 100%); 
                    padding: 12px 20px; border-radius: 10px; color: white; margin-bottom: 10px;'>
            <div style='font-size: 18px; font-weight: bold;'>🏨 Fixed 객실 수기 인상 알림</div>
            <div style='font-size: 12px; opacity: 0.9;'>GD/FFD/FPT/PPV - 전체 점유율 기준</div>
        </div>
        """, unsafe_allow_html=True)

        if critical:
            st.markdown("**🚨 강력 권장 (85%↑)**")
            for a in critical:
                ev_txt = f"🎉 {a['이벤트']}" if a['이벤트'] else ""
                st.markdown(f"""
                <div style='background:#FFEBEE; border-left:5px solid #C62828; padding:10px; border-radius:6px; margin-bottom:5px;'>
                    <b>{a['날짜'].strftime('%Y-%m-%d')} ({a['요일']})</b> 
                    · 전체점유율 <b style='color:#C62828;'>{a['전체점유율']}%</b> 
                    · {a['메시지']} {ev_txt}
                </div>""", unsafe_allow_html=True)

        if warning:
            st.markdown("**🔔 검토 권장 (75%↑)**")
            for a in warning:
                ev_txt = f"🎉 {a['이벤트']}" if a['이벤트'] else ""
                st.markdown(f"""
                <div style='background:#FFF3E0; border-left:5px solid #FF6F00; padding:10px; border-radius:6px; margin-bottom:5px;'>
                    <b>{a['날짜'].strftime('%Y-%m-%d')} ({a['요일']})</b> 
                    · 전체점유율 <b style='color:#FF6F00;'>{a['전체점유율']}%</b> 
                    · {a['메시지']} {ev_txt}
                </div>""", unsafe_allow_html=True)

        st.markdown("")

    if st.session_state.compare_label:
        st.info(f"ℹ️ {st.session_state.compare_label}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 현황",
        "🔮 시뮬레이터",
        "💸 기회비용",
        "📈 시장 트렌드",
        "📊 누적 추적",
        "🔄 정확도 검증",
        "📄 PDF 보고서"
    ])

    # =============== TAB 1 ===============
    with tab1:
        st.markdown(render_master_table(curr, prev, title="📊 1. BAR 요금 현황", mode="기준"), unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="📈 2. 예약 변화량", mode="변화"), unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="🔔 3. 판도 변화", mode="판도변화"), unsafe_allow_html=True)

        st.divider()
        st.subheader("📝 날짜별 메모")
        dates_list = sorted(curr['Date'].unique())
        selected_date_memo = st.selectbox(
            "메모할 날짜", dates_list,
            format_func=lambda d: f"{d.strftime('%Y-%m-%d')} ({WEEKDAYS_KR[d.weekday()]})",
            key="tab1_memo_date"
        )
        note_key = get_note_key(selected_date_memo)
        render_note_input(note_key, f"{selected_date_memo.strftime('%m/%d')} 메모", all_notes)

    # =============== TAB 2 ===============
    with tab2:
        st.subheader("🔮 시장 시그널 반영 BAR 제안")
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.info(f"🏨 조선: {josun_threshold:,}원↑ → +1")
        with col_info2:
            st.info(f"✈️ 항공: {flight_threshold:,}원↑ → +1")
        with col_info3:
            st.info(f"🎯 민감도 반영 (사이드바에서 조정)")

        sim_html = render_sim_comparison_table(
            curr, df_flight_all, df_comp_all,
            josun_threshold, flight_threshold,
            active_search_date, events=all_events, sensitivity=sensitivity
        )
        st.markdown(sim_html, unsafe_allow_html=True)

        st.divider()
        st.subheader("📝 시그널 발동 날짜 메모")
        triggered_dates = alert_opp_df[alert_opp_df['BAR상승'] > 0]['날짜'].unique() if not alert_opp_df.empty else []
        if len(triggered_dates) > 0:
            sel_trigger_date = st.selectbox(
                "메모할 날짜", sorted(triggered_dates),
                format_func=lambda d: f"{d.strftime('%Y-%m-%d')} ({WEEKDAYS_KR[d.weekday()]})",
                key="tab2_memo_date"
            )
            note_key = get_note_key(sel_trigger_date)
            render_note_input(note_key, f"{sel_trigger_date.strftime('%m/%d')} 의사결정", all_notes)
        else:
            st.info("현재 시그널 발동 중인 날짜가 없습니다.")

    # =============== TAB 3 ===============
    with tab3:
        st.subheader("💸 기회비용 분석")
        opp_df = alert_opp_df
        if opp_df.empty:
            st.info("분석할 데이터가 없습니다.")
        else:
            positive_opp = opp_df[opp_df['기회비용'] > 0]['기회비용'].sum()
            boosted_count = (opp_df['BAR상승'] > 0).sum()
            days_affected = opp_df[opp_df['기회비용'] > 0]['날짜'].nunique()
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                        padding: 30px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;'>
                <div style='font-size: 16px; color: #80D8FF;'>추정 추가 수익</div>
                <div style='font-size: 42px; font-weight: bold; color: #FFD700;'>₩ {int(positive_opp):,}</div>
            </div>
            """, unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("시그널 발동", f"{boosted_count}건")
            m2.metric("영향 날짜", f"{days_affected}일")
            m3.metric("객실타입", f"{opp_df['객실타입'].nunique()}개")

            st.divider()
            daily_opp = opp_df.groupby(['날짜', '요일'])['기회비용'].sum().reset_index()
            daily_opp['라벨'] = daily_opp['날짜'].apply(lambda x: x.strftime('%m-%d')) + '(' + daily_opp['요일'] + ')'
            fig1 = px.bar(daily_opp, x='라벨', y='기회비용', color='기회비용',
                          color_continuous_scale=['#E8F5E9', '#FF5252'])
            fig1.update_layout(template="plotly_white", height=400, xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("🔥 TOP 10")
            top10 = opp_df[opp_df['기회비용'] > 0].nlargest(10, '기회비용').copy()
            top10['메모'] = top10['날짜'].apply(lambda d: "📝" if get_note_key(d) in all_notes else "⚪")
            top10['날짜'] = top10['날짜'].apply(lambda x: x.strftime('%Y-%m-%d'))
            for col in ['실제단가', '시뮬단가', '단가차이', '기회비용']:
                top10[col] = top10[col].apply(lambda x: f"₩{int(x):,}")
            st.dataframe(top10[['날짜', '요일', '객실타입', '판매객실수', '실제BAR',
                                '시뮬BAR', '기회비용', '시그널', '메모']],
                         use_container_width=True, hide_index=True)

    # =============== TAB 4 ===============
    with tab4:
        st.subheader("📈 시장 가격 트렌드")
        if df_flight_all.empty and df_comp_all.empty:
            st.warning("크롤링 데이터가 없습니다.")
        else:
            dates_list = sorted(curr['Date'].unique())
            trend_data = []
            our_prices = get_our_avg_price_for_dates(curr, dates_list)
            for d in dates_list:
                josun_p, parnas_p, flight_p = get_market_price_for_date(d, df_flight_all, df_comp_all, active_search_date)
                amber_crawl_p = None
                if not df_comp_all.empty:
                    c_row = df_comp_all[df_comp_all['date'] == d]
                    if active_search_date and 'search_date_str' in c_row.columns:
                        c_row = c_row[c_row['search_date_str'] == active_search_date]
                    amber_rows = c_row[c_row['hotel_name'].str.contains('Amber', case=False, na=False)]
                    if not amber_rows.empty:
                        amber_crawl_p = amber_rows['price'].min()
                trend_data.append({
                    '날짜': d, '그랜드조선': josun_p, '파르나스': parnas_p,
                    '엠버_크롤링': amber_crawl_p, '엠버_시스템': our_prices.get(d), '항공권': flight_p,
                })
            trend_df = pd.DataFrame(trend_data)
            trend_df['날짜_dt'] = pd.to_datetime(trend_df['날짜'])

            fig_hotel = go.Figure()
            if trend_df['그랜드조선'].notna().any():
                fig_hotel.add_trace(go.Scatter(x=trend_df['날짜_dt'], y=trend_df['그랜드조선'],
                    mode='lines+markers', name='조선', line=dict(color='#2E7D32', width=3)))
            if trend_df['파르나스'].notna().any():
                fig_hotel.add_trace(go.Scatter(x=trend_df['날짜_dt'], y=trend_df['파르나스'],
                    mode='lines+markers', name='파르나스', line=dict(color='#9C27B0', width=2, dash='dot')))
            if trend_df['엠버_크롤링'].notna().any():
                fig_hotel.add_trace(go.Scatter(x=trend_df['날짜_dt'], y=trend_df['엠버_크롤링'],
                    mode='lines+markers', name='엠버(크롤링)', line=dict(color='#D32F2F', width=3)))
            if trend_df['엠버_시스템'].notna().any():
                fig_hotel.add_trace(go.Scatter(x=trend_df['날짜_dt'], y=trend_df['엠버_시스템'],
                    mode='lines+markers', name='엠버(시스템)', line=dict(color='#1976D2', width=3)))
            fig_hotel.add_hline(y=josun_threshold, line=dict(color='red', dash='dash'))
            fig_hotel.update_layout(template="plotly_white", height=500, hovermode='x unified')
            fig_hotel.update_yaxes(tickformat=",")
            st.plotly_chart(fig_hotel, use_container_width=True)

            fig_flight = go.Figure()
            if trend_df['항공권'].notna().any():
                colors = ['#D32F2F' if (pd.notna(p) and p and p >= flight_threshold) else '#90A4AE'
                          for p in trend_df['항공권']]
                fig_flight.add_trace(go.Bar(x=trend_df['날짜_dt'], y=trend_df['항공권'],
                    marker_color=colors,
                    text=[f"{int(p):,}" if (pd.notna(p) and p) else "" for p in trend_df['항공권']],
                    textposition='outside'))
            fig_flight.add_hline(y=flight_threshold, line=dict(color='red', dash='dash'))
            fig_flight.update_layout(template="plotly_white", height=400, showlegend=False)
            fig_flight.update_yaxes(tickformat=",")
            st.plotly_chart(fig_flight, use_container_width=True)

    # =============== TAB 5: 📊 누적 추적 ===============
    with tab5:
        st.subheader("📊 누적 기회비용 추적")
        st.caption("시간이 쌓일수록 강력해집니다. 매일 저장하면 더 정확한 트렌드가 보여요.")

        days_back = st.radio("조회 기간", [30, 60, 90], index=0, horizontal=True)

        with st.spinner(f"최근 {days_back}일 스냅샷 분석 중..."):
            snapshots_list = load_all_snapshots_history(days_back=days_back)
            cum_df = calculate_cumulative_metrics(
                snapshots_list, df_flight_all, df_comp_all,
                josun_threshold, flight_threshold,
                all_events, sensitivity, active_search_date
            )

        if cum_df.empty:
            st.info(f"📭 최근 {days_back}일 누적 데이터가 부족합니다. 매일 '🚀 오늘 내역 저장'을 눌러 축적하세요!")
        else:
            total_cum = cum_df['opportunity_cost'].sum()
            avg_daily = cum_df['opportunity_cost'].mean()
            total_triggers = cum_df['trigger_count'].sum()

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                        padding: 30px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;'>
                <div style='font-size: 16px; color: #80D8FF;'>최근 {days_back}일 누적 기회비용</div>
                <div style='font-size: 42px; font-weight: bold; color: #FFD700;'>₩ {int(total_cum):,}</div>
                <div style='font-size: 12px; color: #bbb; margin-top: 10px;'>
                    일평균 ₩{int(avg_daily):,} · 총 시그널 {int(total_triggers)}건
                </div>
            </div>""", unsafe_allow_html=True)

            cum_df['work_date_dt'] = pd.to_datetime(cum_df['work_date'])
            cum_df = cum_df.sort_values('work_date_dt')

            # 누적선 그래프
            cum_df['누적_기회비용'] = cum_df['opportunity_cost'].cumsum()

            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=cum_df['work_date_dt'], y=cum_df['누적_기회비용'],
                mode='lines+markers', name='누적 기회비용',
                fill='tozeroy', line=dict(color='#FFD700', width=3),
                fillcolor='rgba(255, 215, 0, 0.15)'
            ))
            fig_cum.update_layout(
                template="plotly_white", height=400,
                title="누적 기회비용 추이",
                yaxis_title="누적 기회비용 (원)",
                hovermode='x unified'
            )
            fig_cum.update_yaxes(tickformat=",")
            st.plotly_chart(fig_cum, use_container_width=True)

            # 일별 막대
            fig_daily = px.bar(
                cum_df, x='work_date_dt', y='opportunity_cost',
                color='opportunity_cost',
                color_continuous_scale=['#E8F5E9', '#FF5252'],
                labels={'work_date_dt': '저장일', 'opportunity_cost': '일 기회비용'}
            )
            fig_daily.update_layout(template="plotly_white", height=350, showlegend=False,
                                     title="일별 기회비용")
            st.plotly_chart(fig_daily, use_container_width=True)

            # 상세 테이블
            with st.expander("📋 일별 상세"):
                display_cum = cum_df.copy()
                display_cum['opportunity_cost'] = display_cum['opportunity_cost'].apply(lambda x: f"₩{int(x):,}")
                display_cum['누적_기회비용'] = display_cum['누적_기회비용'].apply(lambda x: f"₩{int(x):,}")
                display_cum = display_cum[['work_date', 'opportunity_cost', 'trigger_count', 'affected_days', '누적_기회비용']]
                display_cum.columns = ['저장일', '일 기회비용', '시그널 건수', '영향 날짜', '누적']
                st.dataframe(display_cum, use_container_width=True, hide_index=True)

    # =============== TAB 6: 🔄 정확도 검증 ===============
    with tab6:
        st.subheader("🔄 시뮬레이터 정확도 검증")
        st.caption("시뮬 제안 후 시간이 지난 뒤 실제로 맞았는지 3가지 방식으로 자동 검증합니다.")

        with st.spinner("정확도 검증 중..."):
            snapshots_list = load_all_snapshots_history(days_back=90)
            verification = verify_simulator_accuracy(
                snapshots_list, df_flight_all, df_comp_all,
                josun_threshold, flight_threshold,
                all_events, sensitivity, active_search_date
            )

        if not verification.get('verification_ready'):
            st.info(f"📭 {verification.get('message', '검증 불가')}")
            st.markdown("""
            ### 💡 정확도 검증이란?
            시뮬레이터가 'BAR 올려야 한다'고 제안한 날짜에 **실제로 어떻게 됐는지**를 시간이 지난 후에 검증합니다.
            
            **3가지 검증 방식**
            - **A. 예약 집중도**: 그 날짜에 실제 예약이 몰렸는가?
            - **B. 마감 매출**: 최종 점유율이 평균 이상이었는가?
            - **C. 점유율 일치**: 시뮬 상향 단계와 실제 수요가 맞았는가?
            
            **필요한 것**: 최소 2일 이상의 '🚀 오늘 내역 저장' 기록
            """)
        else:
            a_score = verification['a_score']
            b_score = verification['b_score']
            c_score = verification['c_score']
            overall = (a_score + b_score + c_score) / 3

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #0D47A1 0%, #1565C0 100%); 
                        padding: 30px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;'>
                <div style='font-size: 16px; color: #BBDEFB;'>시뮬레이터 종합 정확도</div>
                <div style='font-size: 48px; font-weight: bold; color: #FFD700;'>{overall:.1f}%</div>
                <div style='font-size: 12px; color: #bbb; margin-top: 10px;'>
                    3가지 검증 방식의 평균값
                </div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🎯 A. 예약 집중도",
                          f"{a_score:.1f}%",
                          f"{verification['a_correct']} / {verification['a_total']} 건")
                st.caption("시뮬이 제안한 날짜에 실제로 예약이 들어왔는가?")
            with c2:
                st.metric("💰 B. 마감 매출",
                          f"{b_score:.1f}%",
                          f"{verification['b_correct']} / {verification['b_total']} 건")
                st.caption("시뮬이 제안한 날짜의 최종 점유율이 평균 이상인가?")
            with c3:
                st.metric("📊 C. 점유율 일치",
                          f"{c_score:.1f}%",
                          f"{verification['c_correct']} / {verification['c_total']} 건")
                st.caption("시뮬 상향 단계와 실제 수요가 일치하는가?")

            st.divider()

            # 상세 검증 내역
            with st.expander(f"📋 최근 검증 상세 ({len(verification['details'])}건)"):
                if verification['details']:
                    detail_df = pd.DataFrame(verification['details'])
                    detail_df['검증일'] = detail_df['검증일'].astype(str)
                    detail_df['대상일'] = detail_df['대상일'].astype(str)
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                else:
                    st.info("상세 내역 없음")

            st.success(f"""
            💡 **회장님 보고용 멘트**: 
            "엠버퓨어힐 자체 수익관리 시뮬레이터는 현재 **{overall:.0f}%의 종합 정확도**를 보이고 있으며, 
            검증 횟수가 쌓일수록 정확도가 더욱 개선될 예정입니다."
            """)

    # =============== TAB 7: PDF ===============
    with tab7:
        st.subheader("📄 회장님 보고용 PDF")
        period_mode = st.radio("기간", ["📅 월별", "📆 전체", "🎯 커스텀"], horizontal=True)
        all_dates = sorted(curr['Date'].unique())
        data_min = min(all_dates); data_max = max(all_dates)

        if period_mode == "📅 월별":
            available_months = sorted(set((d.year, d.month) for d in all_dates))
            month_options = [f"{y}년 {m}월" for y, m in available_months]
            if not month_options:
                st.warning("데이터 없음")
                st.stop()
            sel_str = st.selectbox("월", month_options)
            sel_y = int(sel_str.split("년")[0])
            sel_m = int(sel_str.split("년")[1].replace("월", "").strip())
            _, ld = calendar.monthrange(sel_y, sel_m)
            pdf_start = max(date(sel_y, sel_m, 1), data_min)
            pdf_end = min(date(sel_y, sel_m, ld), data_max)
            period_label = f"{sel_y}년 {sel_m}월"
        elif period_mode == "📆 전체":
            pdf_start, pdf_end = data_min, data_max
            period_label = f"{pdf_start} ~ {pdf_end}"
        else:
            c1, c2 = st.columns(2)
            with c1: pdf_start = st.date_input("시작", value=data_min, min_value=data_min, max_value=data_max)
            with c2: pdf_end = st.date_input("종료", value=data_max, min_value=data_min, max_value=data_max)
            period_label = f"{pdf_start} ~ {pdf_end}"

        filtered = curr[(curr['Date'] >= pdf_start) & (curr['Date'] <= pdf_end)]
        if filtered.empty:
            st.warning("해당 기간 데이터 없음")
        else:
            preview_opp = calculate_opportunity_cost(
                filtered, df_flight_all, df_comp_all,
                josun_threshold, flight_threshold,
                active_search_date, events=all_events, sensitivity=sensitivity
            )
            if not preview_opp.empty:
                prev_positive = preview_opp[preview_opp['기회비용'] > 0]['기회비용'].sum()
                prev_boosted = (preview_opp['BAR상승'] > 0).sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("기간", period_label)
                c2.metric("추가 수익", f"₩{int(prev_positive):,}")
                c3.metric("시그널", f"{prev_boosted}건")

                if st.button("📄 PDF 생성", type="primary", use_container_width=True):
                    with st.spinner("생성 중..."):
                        try:
                            pdf_bytes = generate_pdf_report(
                                preview_opp, None, period_label,
                                josun_threshold, flight_threshold,
                                pdf_start.strftime('%Y-%m-%d'),
                                pdf_end.strftime('%Y-%m-%d')
                            )
                            file_label = period_label.replace(" ", "_").replace("년", "").replace("월", "")
                            st.download_button("📥 다운로드", data=pdf_bytes,
                                file_name=f"Amber_Report_{file_label}.pdf",
                                mime="application/pdf", use_container_width=True)
                            st.success("✅ 생성 완료!")
                        except Exception as e:
                            st.error(f"실패: {e}")

else:
    st.info("👈 사이드바에서 잔여객실 파일을 업로드하세요.")
    st.markdown("""
    ### 🎯 v7.0 새 기능
    - 🚨 **Fixed 객실 수기 인상 알림** (전체 75%/85%)
    - 📊 **누적 추적**: 30/60/90일 기회비용 트렌드
    - 🔄 **정확도 검증**: A+B+C 3가지 방식 자동 체크
    - 🎯 **객실별 민감도** 커스터마이징 (사이드바)
    """)
