import streamlit as st
import sqlite3
import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import linear_sum_assignment, minimize

# ==========================================
# CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(page_title="Room Allocation System", page_icon="🏠", layout="centered")
DB_NAME = "mechanism_design_lab.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, created_at TEXT, total_rent REAL, roommate_count INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, room_name TEXT, area REAL, has_bath INTEGER, light_score INTEGER, quiet_score INTEGER, fixed_price REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, user_name TEXT, valuations_json TEXT, last_submit_time TEXT, modify_count INTEGER)")
    conn.commit()
    conn.close()

init_db()

# ==========================================
# i18n: TRANSLATION DICTIONARY
# ==========================================
TEXT = {
    "EN": {
        "app_title": "Preference Optimization System",
        "app_desc": "A mechanism design experiment resolving decentralized preference conflicts under rigid pricing constraints.",
        "setup_title": "1. Setup Market Constraints",
        "num_agents": "Number of Agents",
        "room_name": "Room Identifier",
        "fixed_price": "Rigid Lease Price",
        "area": "Area Score",
        "bath": "Private Bath",
        "light": "Light Score",
        "quiet": "Quietness Score",
        "total_rent_calc": "Aggregate Fixed Constraint (Total Rent):",
        "btn_generate": "Generate Experiment Session",
        "invite_title": "🔗 Invite Agents",
        "invite_desc": "Share this secure link for agents to submit subjective valuations.",
        "progress": "Data Collection: {0} / {1} submitted",
        "locked": "Your preference vector is locked. Awaiting other agents...",
        "btn_refresh": "Refresh Status",
        "input_title": "Input Subjective Valuation Vector",
        "agent_name": "Agent Identifier:",
        "val_for": "Value for",
        "btn_submit": "Submit Vector",
        "err_matrix": "Invalid matrix: Check sum constraints and identifier.",
        "success_eq": "✅ Equilibrium Reached! Optimal allocation and side payments calculated.",
        "pays": "Pays Side-Payment:",
        "receives": "Receives Compensation:",
        "no_transfer": "Equilibrium Match (No Transfer)",
        "agent": "Agent:",
        "market_price": "Rigid Market Price (Contract)",
        "theory_price": "Theoretical Envy-Free Price",
        "net_transfer": "Net Private Transfer:"
    },
    "ZH": {
        "app_title": "偏好匹配与分房优化系统",
        "app_desc": "这是一个机制设计实验：在死板的固定租金约束下，解决去中心化的偏好冲突，计算最优分房与私下补偿。",
        "setup_title": "1. 设定市场基础约束 (录入房间)",
        "num_agents": "入住总人数",
        "room_name": "房间名称",
        "fixed_price": "固定合同租金",
        "area": "空间大小评分",
        "bath": "带独立卫浴",
        "light": "采光评分",
        "quiet": "安静度评分",
        "total_rent_calc": "系统计算的总租金约束为:",
        "btn_generate": "生成专属分房链接",
        "invite_title": "🔗 邀请室友",
        "invite_desc": "请复制此链接发送至微信群，让大家填写主观偏好。",
        "progress": "提交进度: {0} / {1} 人已填",
        "locked": "你的偏好已锁定。在所有人提交前，数据对其他人保密...",
        "btn_refresh": "刷新最新进度",
        "input_title": "输入你的主观效用估值",
        "agent_name": "你的名字/昵称:",
        "val_for": "你认为该房值多少钱：",
        "btn_submit": "确认并提交",
        "err_matrix": "金额输入有误或未填名字！",
        "success_eq": "✅ 偏好对齐完成！已计算出最优无嫉妒分配及侧面补偿方案。",
        "pays": "发红包补贴室友:",
        "receives": "收室友红包补偿:",
        "no_transfer": "无需红包补偿",
        "agent": "室友:",
        "market_price": "向房东支付 (合同价)",
        "theory_price": "系统测算公平价 (仅供参考)",
        "net_transfer": "私下差价结算 (微信红包):"
    }
}

# --- Sidebar Language Toggle ---
st.sidebar.title("🌐 Language / 语言")
lang_choice = st.sidebar.radio("", ["English", "中文"])
st.session_state.lang = "EN" if lang_choice == "English" else "ZH"
t = TEXT[st.session_state.lang]

# ==========================================
# DATA ENGINE (CRUD Operations)
# ==========================================
def create_project(project_id, total_rent, roommate_count, rooms_data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", (project_id, datetime.now().isoformat(), total_rent, roommate_count))
    for r in rooms_data:
        cur.execute("INSERT INTO rooms (project_id, room_name, area, has_bath, light_score, quiet_score, fixed_price) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                    (project_id, r['name'], r['area'], r['bath'], r['light'], r['quiet'], r['fixed_price']))
    conn.commit()
    conn.close()

def get_project_info(project_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT total_rent, roommate_count FROM projects WHERE project_id=?", (project_id,))
    proj = cur.fetchone()
    if not proj: return None, None, []
    
    cur.execute("SELECT room_name, area, has_bath, light_score, quiet_score, fixed_price FROM rooms WHERE project_id=?", (project_id,))
    rooms = [{"name": row[0], "area": row[1], "bath": row[2], "light": row[3], "quiet": row[4], "fixed_price": row[5]} for row in cur.fetchall()]
    conn.close()
    return proj[0], proj[1], rooms

def submit_or_update_bid(project_id, user_name, valuations):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT modify_count FROM bids WHERE project_id=? AND user_name=?", (project_id, user_name))
    row = cur.fetchone()
    now_str = datetime.now().isoformat()
    if row: 
        cur.execute("UPDATE bids SET valuations_json=?, last_submit_time=?, modify_count=? WHERE project_id=? AND user_name=?",
                    (json.dumps(valuations), now_str, row[0] + 1, project_id, user_name))
    else: 
        cur.execute("INSERT INTO bids (project_id, user_name, valuations_json, last_submit_time, modify_count) VALUES (?, ?, ?, ?, ?)", 
                    (project_id, user_name, json.dumps(valuations), now_str, 0))
    conn.commit()
    conn.close()

def get_all_bids(project_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_name, valuations_json FROM bids WHERE project_id=?", (project_id,))
    bids = cur.fetchall()
    conn.close()
    return bids

# ==========================================
# CORE ALGORITHM: MECHANISM DESIGN & OPTIMIZATION
# ==========================================
def compute_envy_free_allocation_with_side_payments(users, rooms_data, valuations_matrix, total_rent):
    n = len(users)
    room_names = [r["name"] for r in rooms_data]
    fixed_prices_map = {r["name"]: r["fixed_price"] for r in rooms_data}
    
    row_ind, col_ind = linear_sum_assignment(-valuations_matrix)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}
    avg_price = total_rent / n

    def objective(p): return np.sum((p - avg_price) ** 2)
    constraints = [{"type": "eq", "fun": lambda p: np.sum(p) - total_rent}]
    for i in range(n):
        assigned_room = assignment_idx[i]
        for j in range(n):
            if j == assigned_room: continue
            constraints.append({
                "type": "ineq", 
                "fun": lambda p, u=i, alt=j, ass=assigned_room: p[alt] - p[ass] + valuations_matrix[u, ass] - valuations_matrix[u, alt]
            })

    bounds = [(0, total_rent) for _ in range(n)]
    result = minimize(objective, np.full(n, avg_price), method="SLSQP", bounds=bounds, constraints=constraints)
    
    assignment_result = {users[i]: room_names[assignment_idx[i]] for i in range(n)}
    theoretical_prices = {room_names[j]: round(float(result.x[j]), 2) for j in range(n)}
    
    side_payments = {}
    for user in users:
        assigned_room = assignment_result[user]
        side_payments[user] = round(theoretical_prices[assigned_room] - fixed_prices_map[assigned_room], 2)
        
    return assignment_result, theoretical_prices, fixed_prices_map, side_payments

# ==========================================
# USER INTERFACE (STREAMLIT ROUTING)
# ==========================================
query_params = st.query_params
project_id = query_params.get("project_id")

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# --- View 1: Project Initialization ---
if not project_id:
    st.title(t["app_title"], anchor=False)
    st.markdown(t["app_desc"])
    
    with st.container(border=True):
        st.subheader(t["setup_title"], anchor=False)
        roommate_count = st.selectbox(t["num_agents"], [2, 3, 4], index=1)
        st.divider()
        
        rooms_data = []
        default_names = ["Room A", "Room B", "Room C", "Room D"] if st.session_state.lang == "EN" else ["主卧", "次卧", "小次卧", "客厅"]
        total_rent_calculated = 0.0
        
        for i in range(roommate_count):
            with st.expander(f"🚪 {default_names[i]}", expanded=(i==0)):
                r_name = st.text_input(t["room_name"], default_names[i], key=f"name_{i}")
                r_fixed_price = st.number_input(f"{t['fixed_price']} ({'¥' if st.session_state.lang == 'ZH' else '$'})", value=1000.0, step=50.0, key=f"fixed_price_{i}")
                total_rent_calculated += r_fixed_price
                
                col1, col2 = st.columns(2)
                with col1:
                    r_area = st.selectbox(t["area"], options=[5, 4, 3, 2, 1], index=2, key=f"area_{i}")
                    r_bath = st.checkbox(t["bath"], value=(i==0), key=f"bath_{i}")
                with col2:
                    r_light = st.selectbox(t["light"], options=[5, 4, 3, 2, 1], index=1, key=f"light_{i}")
                    r_quiet = st.selectbox(t["quiet"], options=[5, 4, 3, 2, 1], index=2, key=f"quiet_{i}")
                
                rooms_data.append({"name": r_name, "area": r_area, "bath": 1 if r_bath else 0, "light": r_light, "quiet": r_quiet, "fixed_price": r_fixed_price})
        
        st.info(f"{t['total_rent_calc']} **{total_rent_calculated}**")
            
    if st.button(t["btn_generate"], type="primary", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        create_project(new_id, total_rent_calculated, roommate_count, rooms_data)
        st.query_params["project_id"] = new_id
        st.rerun()

# --- View 2: Data Collection & Assignment Output ---
else:
    total_rent, roommate_count, rooms_data = get_project_info(project_id)
    if not total_rent:
        st.error("Session expired or invalid. / 链接失效")
        st.stop()

    current_bids = get_all_bids(project_id)
    submitted_users = [b[0] for b in current_bids]
    
    # 请确保这里是你真实的域名！！！
    share_link = f"https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/?project_id={project_id}"
    
    # State A: Collecting Preference Vectors
    if len(current_bids) < roommate_count:
        st.info(f"**{t['invite_title']}** \n\n{t['invite_desc']}")
        st.code(share_link, language="text")
        st.progress(len(current_bids) / roommate_count, text=t["progress"].format(len(current_bids), roommate_count))
        
        if st.session_state.current_user in submitted_users:
            st.success(t["locked"])
            if st.button(t["btn_refresh"], use_container_width=True): st.rerun()
                
        else:
            with st.container(border=True):
                st.subheader(t["input_title"])
                user_name = st.text_input(t["agent_name"])
                vals = []
                cols = st.columns(roommate_count)
                
                for i in range(roommate_count - 1):
                    val = cols[i].number_input(f"{t['val_for']} {rooms_data[i]['name']}", value=float(total_rent/roommate_count), step=50.0, key=f"val_{i}")
                    vals.append(val)
                    
                last_val = total_rent - sum(vals)
                cols[-1].number_input(f"{t['val_for']} {rooms_data[-1]['name']}", value=float(last_val), disabled=True)
                vals.append(last_val)
                
            if st.button(t["btn_submit"], type="primary", use_container_width=True):
                if last_val < 0 or not user_name.strip():
                    st.error(t["err_matrix"])
                else:
                    submit_or_update_bid(project_id, user_name, vals)
                    st.session_state.current_user = user_name
                    st.rerun()

    # State B: Resolution & Side Payment Calculation
    else:
        st.success(t["success_eq"])
        
        users = [b[0] for b in current_bids]
        valuations = np.array([json.loads(b[1]) for b in current_bids])
        
        try:
            assignment, theoretical_prices, fixed_prices, side_payments = compute_envy_free_allocation_with_side_payments(users, rooms_data, valuations, total_rent)
            
            for u in users:
                assigned_room = assignment[u]
                fair_p = theoretical_prices[assigned_room]
                fixed_p = fixed_prices[assigned_room]
                sp = side_payments[u]
                
                if sp > 0:
                    sp_text = f"<span style='color: #ff3b30; font-weight: 600;'>{t['pays']} {sp}</span>"
                elif sp < 0:
                    sp_text = f"<span style='color: #34c759; font-weight: 600;'>{t['receives']} {abs(sp)}</span>"
                else:
                    sp_text = f"<span style='color: #8e8e93; font-weight: 600;'>{t['no_transfer']}</span>"

                st.markdown(f"""
                <div style="padding: 20px; border-radius: 12px; background-color: #fbfbfd; margin-bottom: 16px; border: 1px solid #d2d2d7;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-size: 20px; font-weight: 600; color: #1d1d1f;">{t['agent']} {u}</span>
                        <span style="font-size: 16px; font-weight: 500; color: #0071e3; background: #e8f0fe; padding: 4px 12px; border-radius: 20px;">{assigned_room}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e5e5ea; padding-bottom: 8px; margin-bottom: 8px;">
                        <span style="font-size: 14px; color: #86868b;">{t['market_price']}</span>
                        <span style="font-size: 14px; color: #1d1d1f; font-family: monospace;">{fixed_p}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e5e5ea; padding-bottom: 8px; margin-bottom: 12px;">
                        <span style="font-size: 14px; color: #86868b;">{t['theory_price']}</span>
                        <span style="font-size: 14px; color: #1d1d1f; font-family: monospace;">{fair_p}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 12px; border-radius: 8px; border: 1px dashed #c7c7cc;">
                        <span style="font-size: 15px; font-weight: 500; color: #1d1d1f;">{t['net_transfer']}</span>
                        <span style="font-size: 16px;">{sp_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Optimization failure. Error: {e}")
