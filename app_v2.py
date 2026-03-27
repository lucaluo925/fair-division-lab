import streamlit as st
import sqlite3
import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import linear_sum_assignment, minimize

st.set_page_config(page_title="合租分房决策系统", page_icon="🏠", layout="centered")

# =========================
# 数据库管理 (V4 机制设计版)
# =========================
def init_db():
    conn = sqlite3.connect("data_engine_v4.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, created_at TEXT, total_rent REAL, roommate_count INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, room_name TEXT, area REAL, has_bath INTEGER, light_score INTEGER, quiet_score INTEGER, fixed_price REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, user_name TEXT, valuations_json TEXT, last_submit_time TEXT, modify_count INTEGER)")
    conn.commit()
    conn.close()

init_db()

def create_project(project_id, total_rent, roommate_count, rooms_data):
    conn = sqlite3.connect("data_engine_v4.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", (project_id, datetime.now().isoformat(), total_rent, roommate_count))
    for r in rooms_data:
        cur.execute("INSERT INTO rooms (project_id, room_name, area, has_bath, light_score, quiet_score, fixed_price) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                    (project_id, r['name'], r['area'], r['bath'], r['light'], r['quiet'], r['fixed_price']))
    conn.commit()
    conn.close()

def get_project_info(project_id):
    conn = sqlite3.connect("data_engine_v4.db")
    cur = conn.cursor()
    cur.execute("SELECT total_rent, roommate_count FROM projects WHERE project_id=?", (project_id,))
    proj = cur.fetchone()
    if not proj:
        return None, None, []
    cur.execute("SELECT room_name, area, has_bath, light_score, quiet_score, fixed_price FROM rooms WHERE project_id=?", (project_id,))
    rooms = [{"name": row[0], "area": row[1], "bath": row[2], "light": row[3], "quiet": row[4], "fixed_price": row[5]} for row in cur.fetchall()]
    conn.close()
    return proj[0], proj[1], rooms

def submit_or_update_bid(project_id, user_name, valuations):
    conn = sqlite3.connect("data_engine_v4.db")
    cur = conn.cursor()
    cur.execute("SELECT modify_count FROM bids WHERE project_id=? AND user_name=?", (project_id, user_name))
    row = cur.fetchone()
    now_str = datetime.now().isoformat()
    if row: 
        new_count = row[0] + 1
        cur.execute("UPDATE bids SET valuations_json=?, last_submit_time=?, modify_count=? WHERE project_id=? AND user_name=?",
                    (json.dumps(valuations), now_str, new_count, project_id, user_name))
    else: 
        cur.execute("INSERT INTO bids (project_id, user_name, valuations_json, last_submit_time, modify_count) VALUES (?, ?, ?, ?, ?)", 
                    (project_id, user_name, json.dumps(valuations), now_str, 0))
    conn.commit()
    conn.close()

def get_all_bids(project_id):
    conn = sqlite3.connect("data_engine_v4.db")
    cur = conn.cursor()
    cur.execute("SELECT user_name, valuations_json FROM bids WHERE project_id=?", (project_id,))
    bids = cur.fetchall()
    conn.close()
    return bids

def get_admin_data():
    conn = sqlite3.connect("data_engine_v4.db")
    df_projects = pd.read_sql_query("SELECT * FROM projects", conn)
    df_rooms = pd.read_sql_query("SELECT * FROM rooms", conn)
    df_bids = pd.read_sql_query("SELECT * FROM bids", conn)
    conn.close()
    return df_projects, df_rooms, df_bids

# =========================
# 核心算法 (引入 Side Payment 机制)
# =========================
def solve_fair_division_with_side_payments(users, rooms_data, valuations, total_rent):
    n = len(users)
    room_names = [r["name"] for r in rooms_data]
    fixed_prices_map = {r["name"]: r["fixed_price"] for r in rooms_data}
    
    # 1. 效用最大化分配 (匹配)
    row_ind, col_ind = linear_sum_assignment(-valuations)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}
    avg_price = total_rent / n

    # 2. 计算无嫉妒均衡价格 (Envy-Free Prices)
    def objective(p): return np.sum((p - avg_price) ** 2)
    constraints = [{"type": "eq", "fun": lambda p: np.sum(p) - total_rent}]
    for i in range(n):
        assigned = assignment_idx[i]
        for j in range(n):
            if j == assigned: continue
            constraints.append({"type": "ineq", "fun": lambda p, u=i, alt=j, ass=assigned: p[alt] - p[ass] + valuations[u, ass] - valuations[u, alt]})

    bounds = [(0, total_rent) for _ in range(n)]
    result = minimize(objective, np.full(n, avg_price), method="SLSQP", bounds=bounds, constraints=constraints)
    
    # 3. 封装结果与计算侧面补偿 (Side Payments)
    assignment = {users[i]: room_names[assignment_idx[i]] for i in range(n)}
    fair_prices_map = {room_names[j]: round(float(result.x[j]), 2) for j in range(n)}
    
    side_payments = {}
    for u in users:
        assigned_room = assignment[u]
        fair_price = fair_prices_map[assigned_room]
        fixed_price = fixed_prices_map[assigned_room]
        # 侧面补偿 = 你理论上应该付的公平价格 - 合同死价格
        side_payments[u] = round(fair_price - fixed_price, 2)
        
    return assignment, fair_prices_map, fixed_prices_map, side_payments

# =========================
# 前端界面与路由
# =========================
query_params = st.query_params
project_id = query_params.get("project_id")
is_admin = query_params.get("admin")

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ----------------- 🌟 隐藏场景：上帝视角的后台大盘 -----------------
if is_admin == "true":
    st.title("📊 机制设计数据实验室")
    st.caption("研究平台后台管理中心")
    
    SECRET_PASSWORD = "123" 
    
    pwd = st.text_input("请输入暗号：", type="password")
    if pwd == SECRET_PASSWORD:
        st.success("欢迎回来，主理人。这是你的数据资产。")
        df_projects, df_rooms, df_bids = get_admin_data()
        
        st.subheader("1. 房屋特征数据池 (包含固定合同价)", anchor=False)
        st.dataframe(df_rooms, use_container_width=True)
        
        st.subheader("2. 用户行为与决策数据", anchor=False)
        st.dataframe(df_bids, use_container_width=True)
        
        st.divider()
        csv_data = df_bids.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 一键导出用户出价数据 (CSV)", data=csv_data, file_name='behavior_data.csv', mime='text/csv', type="primary")
    elif pwd != "":
        st.error("密码错误！")
    st.stop()

# ----------------- 场景 1：发起项目 -----------------
if not project_id:
    st.title("偏好匹配与分房优化系统", anchor=False)
    st.markdown("现实中的合同租金是死板的，但主观效用是自由的。本系统在固定租金约束下，通过补偿机制为你寻找最优分配方案。")
    st.write("")
    
    with st.container(border=True):
        st.subheader("基础信息录入", anchor=False)
        roommate_count = st.selectbox("入住总人数", [2, 3, 4], index=1)
        
        st.divider()
        st.markdown("📝 **录入房间特征与合同定价**")
        st.caption("无论合同上的 Individual Lease 怎么定价，请如实填写。")
        
        rooms_data = []
        default_names = ["主卧", "次卧", "小次卧", "客厅"]
        total_rent_calculated = 0.0
        
        for i in range(roommate_count):
            with st.expander(f"🚪 设置 {default_names[i]}", expanded=(i==0)):
                r_name = st.text_input("房间名称", default_names[i], key=f"name_{i}")
                r_fixed_price = st.number_input("💸 该房间的固定合同租金 (元)", value=1000.0, step=50.0, key=f"fixed_price_{i}")
                total_rent_calculated += r_fixed_price
                
                col1, col2 = st.columns(2)
                with col1:
                    area_options = {5: "极大", 4: "较大", 3: "中等", 2: "较小", 1: "极小"}
                    r_area = st.selectbox("📏 房间大小", options=[5, 4, 3, 2, 1], index=2, format_func=lambda x: area_options[x], key=f"area_{i}")
                    r_bath = st.checkbox("✅ 带独立卫浴", value=(i==0), key=f"bath_{i}")
                    
                with col2:
                    light_options = {5: "全天有阳光", 4: "半天直射光", 3: "正常窗户", 2: "采光较差", 1: "无窗/极暗"}
                    quiet_options = {5: "极安静", 4: "较安静", 3: "一般", 2: "较吵", 1: "很吵"}
                    r_light = st.selectbox("☀️ 采光情况", options=[5, 4, 3, 2, 1], index=1, format_func=lambda x: light_options[x], key=f"light_{i}")
                    r_quiet = st.selectbox("🤫 安静程度", options=[5, 4, 3, 2, 1], index=2, format_func=lambda x: quiet_options[x], key=f"quiet_{i}")
                
                rooms_data.append({
                    "name": r_name, "area": r_area, "bath": 1 if r_bath else 0, 
                    "light": r_light, "quiet": r_quiet, "fixed_price": r_fixed_price
                })
        
        st.info(f"💡 系统已自动计算整租总额为: **{total_rent_calculated} 元**")
            
    st.write("") 
    if st.button("生成专属分房链接", type="primary", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        create_project(new_id, total_rent_calculated, roommate_count, rooms_data)
        st.query_params["project_id"] = new_id
        st.rerun()

# ----------------- 场景 2 & 3：填写与结果 -----------------
else:
    with st.container(border=True):
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.markdown("### 分房决策进行中...")
        with col_btn:
            if st.button("⬅️ 重新开局", use_container_width=True):
                st.query_params.clear()
                st.session_state.current_user = None
                st.rerun()

    total_rent, roommate_count, rooms_data = get_project_info(project_id)
    if not total_rent:
        st.error("项目不存在或已失效。")
        st.stop()

    room_names = [r["name"] for r in rooms_data]
    current_bids = get_all_bids(project_id)
    submitted_users = [b[0] for b in current_bids]
    
    # 🌟 这里的链接已经完全替换为你专属的线上域名了！
    share_link = f"https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/?project_id={project_id}"
    
    if len(current_bids) < roommate_count:
        st.info("👇 **第一步：邀请室友** \n\n请复制链接发送至微信群。")
        st.code(share_link, language="text")
        st.progress(len(current_bids) / roommate_count, text=f"提交进度: {len(current_bids)} / {roommate_count} 人已填")
        
        if st.session_state.current_user in submitted_users:
            with st.container(border=True):
                st.success(f"**{st.session_state.current_user}**，你的预期已锁定。")
                st.caption("在所有人提交前，你的估值向量对其他室友不可见。")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("刷新最新进度", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("我要重新出价", type="secondary", use_container_width=True):
                    st.session_state.current_user = None
                    st.rerun()
                
        else:
            with st.container(border=True):
                st.subheader("📝 输入你的主观效用估值", anchor=False)
                st.markdown(f"总租金为 **{total_rent} 元**。**请暂时忘记合同上的死板定价**，仅根据房间的物理属性，填写你认为这些房间在心理上值多少钱。")
                
                st.caption("🔍 各房间参数与当前合同价参考：")
                for r in rooms_data:
                    bath_txt = "带独卫" if r['bath'] else "公用卫浴"
                    area_desc_map = {5: "极大", 4: "较大", 3: "中等", 2: "较小", 1: "极小"}
                    area_desc = area_desc_map.get(r['area'], f"{r['area']}")
                    light_desc_map = {5: "极佳", 4: "较好", 3: "正常", 2: "较差", 1: "极暗"}
                    quiet_desc_map = {5: "极静", 4: "较静", 3: "一般", 2: "较吵", 1: "很吵"}
                    
                    st.markdown(f"- **{r['name']}** (合同价: `{r['fixed_price']}元`): 大小**{area_desc}** | {bath_txt} | 采光**{light_desc_map.get(r['light'])}** | 噪音**{quiet_desc_map.get(r['quiet'])}**")
                
                st.divider()
                user_name = st.text_input("你的名字/昵称：")
                
                vals = []
                cols = st.columns(roommate_count)
                
                for i in range(roommate_count - 1):
                    r_name = room_names[i]
                    val = cols[i].number_input(f"对 {r_name} 的估值", value=float(total_rent/roommate_count), step=50.0, key=f"val_{i}")
                    vals.append(val)
                    
                last_room_name = room_names[-1]
                sum_previous = sum(vals)
                last_val = total_rent - sum_previous
                
                cols[-1].number_input(f"{last_room_name} 估值 (自动)", value=float(last_val), disabled=True)
                vals.append(last_val)
                
            if st.button("确认并提交", type="primary", use_container_width=True):
                if last_val < 0:
                    st.error("前面房间的金额太高，导致最后一个房间出现负数！")
                elif not user_name.strip():
                    st.error("别忘了填名字！")
                else:
                    submit_or_update_bid(project_id, user_name, vals)
                    st.session_state.current_user = user_name
                    st.rerun()

    # --- 场景 3：展示 Side Payment 结果 ---
    else:
        st.balloons()
        st.success("🎉 偏好对齐完成！已计算出最优无嫉妒分配及侧面补偿方案。")
        st.markdown("由于合同租金无法更改，系统已计算出**室友间私下转账（微信红包）补偿金**，以确保绝对公平：")
        
        users = [b[0] for b in current_bids]
        valuations = np.array([json.loads(b[1]) for b in current_bids])
        
        try:
            assignment, fair_prices, fixed_prices, side_payments = solve_fair_division_with_side_payments(users, rooms_data, valuations, total_rent)
            
            for i, u in enumerate(users):
                assigned_room = assignment[u]
                fair_p = fair_prices[assigned_room]
                fixed_p = fixed_prices[assigned_room]
                sp = side_payments[u]
                
                # 判断红包逻辑
                if sp > 0:
                    sp_text = f"<span style='color: #ff3b30; font-weight: 600;'>发红包补贴室友: ¥{sp}</span>"
                    sp_desc = "你的理论应付金额高于合同租金，你赚到了！请把差价补贴给其他室友。"
                elif sp < 0:
                    sp_text = f"<span style='color: #34c759; font-weight: 600;'>收室友红包补偿: ¥{abs(sp)}</span>"
                    sp_desc = "你的理论应付金额低于合同租金，你吃亏了，理应获得室友的资金补偿。"
                else:
                    sp_text = f"<span style='color: #8e8e93; font-weight: 600;'>无需红包补偿</span>"
                    sp_desc = "你的合同租金正好等于你的理论应付价格。"

                # 高级回执单 UI
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 12px; background-color: #fbfbfd; margin-bottom: 16px; border: 1px solid #d2d2d7; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="font-size: 20px; font-weight: 600; color: #1d1d1f;">{u}</span>
                        <span style="font-size: 16px; font-weight: 500; color: #0071e3; background: #e8f0fe; padding: 4px 12px; border-radius: 20px;">分得: {assigned_room}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e5e5ea; padding-bottom: 8px; margin-bottom: 8px;">
                        <span style="font-size: 14px; color: #86868b;">向房东支付 (合同价)</span>
                        <span style="font-size: 14px; color: #1d1d1f; font-family: monospace;">¥ {fixed_p}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e5e5ea; padding-bottom: 8px; margin-bottom: 12px;">
                        <span style="font-size: 14px; color: #86868b;">系统测算公平价 (仅供参考)</span>
                        <span style="font-size: 14px; color: #1d1d1f; font-family: monospace;">¥ {fair_p}</span>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; background: #ffffff; padding: 12px; border-radius: 8px; border: 1px dashed #c7c7cc;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-size: 15px; font-weight: 500; color: #1d1d1f;">💸 私下差价结算：</span>
                            <span style="font-size: 16px;">{sp_text}</span>
                        </div>
                        <span style="font-size: 12px; color: #86868b; line-height: 1.4;">{sp_desc}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error("数据计算异常，可能是大家对房间的估价过于极端或存在数学无解情况。")
