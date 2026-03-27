import streamlit as st
import sqlite3
import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import linear_sum_assignment, minimize

DB_NAME = "mechanism_design_lab.db"

# ==========================================
# 1. 基础配置 & 数据库初始化
# ==========================================
st.set_page_config(page_title="FairShare | 科学合租决策", page_icon="🏠", layout="centered")

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
# 2. 国际化文案字典
# ==========================================
TEXT = {
    "EN": {
        "title": "FairShare",
        "subtitle": "An interactive tool to help roommates allocate rooms and find a fair pricing baseline.",
        "step1_title": "Step 1: Apartment Details",
        "num_agents": "How many roommates?",
        "room_name": "Room Name",
        "fixed_price": "Lease Price ($)",
        "area": "Space & Size",
        "bath": "Private Bathroom",
        "light": "Natural Light",
        "quiet": "Quietness",
        "total_rent_calc": "Total Monthly Rent:",
        "btn_generate": "Create FairShare Link",
        "invite_title": "Invite your roommates",
        "invite_desc": "Share this link in your group chat. Everyone will submit their own preferences privately.",
        "progress": "Waiting for submissions: {0} / {1} ready",
        "locked": "Your preferences are securely locked. Awaiting others...",
        "btn_refresh": "Refresh Status",
        "btn_edit": "Withdraw & Edit Bid",
        "input_title": "How much is each room worth to you?",
        "input_desc": "Don't worry about the contract price right now. Just tell us how much you'd personally pay for each room's physical features.",
        "agent_name": "Your Name / Nickname:",
        "val_for": "Value of",
        "btn_submit": "Submit Preferences",
        "err_matrix": "Oops! Please check your numbers and make sure you entered a name.",
        
        # 结果页分层文案
        "success_title": "Allocation Results Ready",
        "layer1_title": "📌 Layer 1: Recommended Assignment",
        "layer1_desc": "Based on everyone's subjective valuations, here is the most efficient room matching under the current fixed lease prices.",
        "layer2_title": "⚖️ Layer 2: Optional Fairness Adjustment",
        "layer2_desc": "If you wish to further balance perceived fairness, the algorithm suggests the following side payments as a reference for negotiation.",
        "disclaimer": "⚠️ Note: Side payments are optional recommendations to help you negotiate, not enforced transfers. This tool does not change your actual lease.",
        
        # 结算文案 
        "pays": "Suggested compensation to roommates:",
        "receives": "Suggested compensation from roommates:",
        "no_transfer": "No adjustment needed",
        "market_price": "Contract Price",
        "theory_price": "Algorithmic Fair Price",
        "net_transfer": "Optional Side Payment",
        
        # 结果锁定提示
        "regret_tip": "💡 Note on Pricing: If your suggested compensation is high, it is because your submitted valuation for this room was significantly higher than others. The algorithm ensures you secure the room you value most, while compensating others to maintain fairness."
    },
    "ZH": {
        "title": "FairShare 科学分房",
        "subtitle": "为合租室友提供基于算法的选房建议与公平差价参考。",
        "step1_title": "第一步：定制公寓信息",
        "num_agents": "合租人数",
        "room_name": "房间名称",
        "fixed_price": "合同上的房间租金 (¥)",
        "area": "空间大小",
        "bath": "带独立卫浴",
        "light": "采光情况",
        "quiet": "安静程度",
        "total_rent_calc": "系统计算的公寓总租金:",
        "btn_generate": "生成专属分房邀请",
        "invite_title": "邀请你的室友",
        "invite_desc": "请复制此链接发送至微信群。大家将互不干扰地填写自己的真实偏好。",
        "progress": "提交进度: {0} / {1} 人已准备就绪",
        "locked": "你的偏好已加密锁定。正在等待其他室友提交...",
        "btn_refresh": "刷新进度",
        "btn_edit": "撤回并修改估值",
        "input_title": "你觉得每个房间值多少钱？",
        "input_desc": "请暂时忘掉房东的定价。仅凭你的主观感觉：为了住进这个房间，你最多愿意承担多少房租？",
        "agent_name": "你的称呼:",
        "val_for": "对该房的心理估值：",
        "btn_submit": "确认提交",
        "err_matrix": "哎呀，金额填写似乎有误，或者忘记填名字了哦。",
        
        # 结果页分层文案
        "success_title": "匹配结果已生成",
        "layer1_title": "📌 推荐分配方案 (不含补偿)",
        "layer1_desc": "基于大家的真实心理估值，这是当前固定租金下效用最大化的房间分配方案。",
        "layer2_title": "⚖️ 公平增强版 (含可选补偿)",
        "layer2_desc": "如果大家希望进一步平衡心里的“公平感”，可以参考以下差价补偿金额进行私下协商。",
        "disclaimer": "⚠️ 免责声明：补偿金额仅作为协商的公平参考基准，不是强制执行方案。本系统不改变实际合同的房租定价。",
        
        # 结算文案 
        "pays": "建议私下补偿给室友:",
        "receives": "建议收取室友补偿:",
        "no_transfer": "无需差价调整",
        "market_price": "合同固定定价",
        "theory_price": "系统推算公平价",
        "net_transfer": "建议私下补偿",
        
        # 结果锁定提示
        "regret_tip": "💡 差价说明：如果系统建议你支付较高的补偿金，是因为你对该房间的心理估值明显高于其他人。算法确保你优先获得了最心仪的房间，并通过补偿机制让所有人实现公平。"
    }
}

OPTIONS = {
    "EN": {
        "area": {5: "5 - Extremely Spacious", 4: "4 - Spacious", 3: "3 - Average", 2: "2 - Small", 1: "1 - Tiny"},
        "light": {5: "5 - Full day direct sun", 4: "4 - Half day sun", 3: "3 - Standard window", 2: "2 - Poor lighting", 1: "1 - Windowless/Dark"},
        "quiet": {5: "5 - Pin drop quiet", 4: "4 - Mostly quiet", 3: "3 - Average", 2: "2 - Occasional noise", 1: "1 - Very noisy"}
    },
    "ZH": {
        "area": {5: "5 - 极大 (可放沙发/书桌)", 4: "4 - 较大 (活动空间充裕)", 3: "3 - 中等 (标准大小)", 2: "2 - 较小 (仅容床和衣柜)", 1: "1 - 极小 (转不开身)"},
        "light": {5: "5 - 极佳 (全天有阳光)", 4: "4 - 良好 (大半天直射)", 3: "3 - 正常 (有窗户/无直射)", 2: "2 - 较差 (采光受挡)", 1: "1 - 极暗 (无窗/常年开灯)"},
        "quiet": {5: "5 - 极静 (隔音极佳)", 4: "4 - 较静 (偶尔有声音)", 3: "3 - 一般 (正常生活音)", 2: "2 - 较吵 (临街/隔音差)", 1: "1 - 极吵 (严重影响睡眠)"}
    }
}

col_space, col_lang = st.columns([5, 1])
with col_lang:
    is_zh = st.toggle("中 / EN", value=True, help="Switch Language")
    st.session_state.lang = "ZH" if is_zh else "EN"

t = TEXT[st.session_state.lang]
opt = OPTIONS[st.session_state.lang]

# ==========================================
# 3. 核心功能函数
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

def delete_bid(project_id, user_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM bids WHERE project_id=? AND user_name=?", (project_id, user_name))
    conn.commit()
    conn.close()

def compute_envy_free_allocation_with_side_payments(users, rooms_data, valuations_matrix, total_rent):
    n = len(users)
    room_names = [r["name"] for r in rooms_data]
    fixed_prices_map = {r["name"]: r["fixed_price"] for r in rooms_data}
    
    # 匈牙利算法求最大效用分配
    row_ind, col_ind = linear_sum_assignment(-valuations_matrix)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}
    avg_price = total_rent / n

    # SLSQP 约束优化求无嫉妒理论价格
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
# 4. 路由与前端渲染
# ==========================================
query_params = st.query_params
project_id = query_params.get("project_id")

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# --- 场景 1：发起项目 ---
if not project_id:
    st.title(t["title"], anchor=False)
    st.markdown(f"<p style='color:#86868b; font-size: 16px;'>{t['subtitle']}</p>", unsafe_allow_html=True)
    st.write("")
    
    with st.container(border=True):
        st.subheader(t["step1_title"], anchor=False)
        roommate_count = st.selectbox(t["num_agents"], [2, 3, 4], index=1)
        st.divider()
        
        rooms_data = []
        default_names = ["Master Bedroom", "Room B", "Room C", "Living Room"] if st.session_state.lang == "EN" else ["主卧", "次卧", "小次卧", "客厅"]
        total_rent_calculated = 0.0
        
        for i in range(roommate_count):
            with st.expander(f"🚪 {default_names[i]}", expanded=(i==0)):
                r_name = st.text_input(t["room_name"], default_names[i], key=f"name_{i}")
                r_fixed_price = st.number_input(t["fixed_price"], value=1000.0, step=50.0, key=f"fixed_price_{i}")
                total_rent_calculated += r_fixed_price
                
                col1, col2 = st.columns(2)
                with col1:
                    r_area = st.selectbox(t["area"], options=[5, 4, 3, 2, 1], format_func=lambda x: opt["area"][x], index=2, key=f"area_{i}")
                    r_bath = st.checkbox(t["bath"], value=(i==0), key=f"bath_{i}")
                with col2:
                    r_light = st.selectbox(t["light"], options=[5, 4, 3, 2, 1], format_func=lambda x: opt["light"][x], index=1, key=f"light_{i}")
                    r_quiet = st.selectbox(t["quiet"], options=[5, 4, 3, 2, 1], format_func=lambda x: opt["quiet"][x], index=2, key=f"quiet_{i}")
                
                rooms_data.append({"name": r_name, "area": r_area, "bath": 1 if r_bath else 0, "light": r_light, "quiet": r_quiet, "fixed_price": r_fixed_price})
        
        st.info(f"{t['total_rent_calc']} **{total_rent_calculated}**")
            
    if st.button(t["btn_generate"], type="primary", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        create_project(new_id, total_rent_calculated, roommate_count, rooms_data)
        st.query_params["project_id"] = new_id
        st.rerun()

# --- 场景 2：数据收集与展示 ---
else:
    total_rent, roommate_count, rooms_data = get_project_info(project_id)
    if not total_rent:
        st.error("Session expired or invalid. / 链接失效")
        st.stop()

    current_bids = get_all_bids(project_id)
    submitted_users = [b[0] for b in current_bids]
    
    # 获取当前应用的 URL 作为分享链接
    # 注意：部署到云端后，请确保这里的链接与您实际的域名相符
    share_link = f"https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/?project_id={project_id}"
    
    # --- 状态 A：收集出价 ---
    if len(current_bids) < roommate_count:
        st.markdown(f"### {t['invite_title']}")
        st.markdown(f"<p style='color:#86868b;'>{t['invite_desc']}</p>", unsafe_allow_html=True)
        st.code(share_link, language="text")
        st.progress(len(current_bids) / roommate_count, text=t["progress"].format(len(current_bids), roommate_count))
        
        if st.session_state.current_user in submitted_users:
            st.success(t["locked"])
            # 状态 A 允许撤回和修改，确保填错可以修正
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(t["btn_refresh"], use_container_width=True): st.rerun()
            with col_btn2:
                if st.button(t["btn_edit"], use_container_width=True):
                    delete_bid(project_id, st.session_state.current_user)
                    st.session_state.current_user = None
                    st.rerun()
                
        else:
            with st.container(border=True):
                st.subheader(t["input_title"], anchor=False)
                st.markdown(f"<p style='color:#86868b; font-size: 14px;'>{t['input_desc']}</p>", unsafe_allow_html=True)
                st.divider()
                
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

    # --- 状态 B：展示分配结果 ---
    else:
        st.balloons()
        st.markdown(f"### {t['success_title']}")
        st.write("")
        
        users = [b[0] for b in current_bids]
        valuations = np.array([json.loads(b[1]) for b in current_bids])
        
        try:
            assignment, theoretical_prices, fixed_prices, side_payments = compute_envy_free_allocation_with_side_payments(users, rooms_data, valuations, total_rent)
            
            # --- 第一层：仅推荐分配 ---
            st.markdown(f"#### {t['layer1_title']}")
            st.markdown(f"<p style='color:#86868b; font-size:14px;'>{t['layer1_desc']}</p>", unsafe_allow_html=True)
            
            layer1_cols = st.columns(roommate_count)
            for i, u in enumerate(users):
                assigned_room = assignment[u]
                with layer1_cols[i]:
                    st.markdown(f"""
                    <div style="padding: 15px; border-radius: 10px; background-color: #f0f4f8; border: 1px solid #d9e2ec; text-align: center;">
                        <div style="font-size: 18px; font-weight: 600; color: #102a43;">{u}</div>
                        <div style="color: #627d98; font-size: 14px; margin-top: 5px;">⬇️</div>
                        <div style="font-size: 16px; font-weight: 500; color: #0071e3; margin-top: 5px;">{assigned_room}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.divider()
            
            # --- 第二层：带补偿的公平增强版 ---
            st.markdown(f"#### {t['layer2_title']}")
            st.markdown(f"<p style='color:#86868b; font-size:14px;'>{t['layer2_desc']}</p>", unsafe_allow_html=True)
            
            st.warning(t["disclaimer"], icon="⚠️")
            
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
                <div style="padding: 20px; border-radius: 16px; background-color: #fbfbfd; margin-bottom: 20px; border: 1px solid #d2d2d7;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 20px; font-weight: 600; color: #1d1d1f;">{u} ➡️ {assigned_room}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e5e5ea; padding-bottom: 10px; margin-bottom: 10px;">
                        <span style="font-size: 14px; color: #86868b;">{t['market_price']}</span>
                        <span style="font-size: 15px; color: #1d1d1f; font-family: monospace;">{fixed_p}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 14px 16px; border-radius: 10px; border: 1px solid #e5e5ea;">
                        <span style="font-size: 15px; font-weight: 600; color: #1d1d1f;">{t['net_transfer']}</span>
                        <span style="font-size: 16px;">{sp_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- 人性化防反悔提示 (结果已锁定，维护 Incentive Compatibility) ---
            st.info(t["regret_tip"])
                
        except Exception as e:
            st.error(f"Calculation Error / 计算出错: {e}")
