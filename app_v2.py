import streamlit as st
import sqlite3
import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import linear_sum_assignment, minimize

st.set_page_config(page_title="合租房费计算器", page_icon="🏠", layout="centered")

# =========================
# 数据库管理 (V3 数据引擎)
# =========================
def init_db():
    conn = sqlite3.connect("data_engine_v3.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, created_at TEXT, total_rent REAL, roommate_count INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, room_name TEXT, area REAL, has_bath INTEGER, light_score INTEGER, quiet_score INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, user_name TEXT, valuations_json TEXT, last_submit_time TEXT, modify_count INTEGER)")
    conn.commit()
    conn.close()

init_db()

def create_project(project_id, total_rent, roommate_count, rooms_data):
    conn = sqlite3.connect("data_engine_v3.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", (project_id, datetime.now().isoformat(), total_rent, roommate_count))
    for r in rooms_data:
        cur.execute("INSERT INTO rooms (project_id, room_name, area, has_bath, light_score, quiet_score) VALUES (?, ?, ?, ?, ?, ?)", 
                    (project_id, r['name'], r['area'], r['bath'], r['light'], r['quiet']))
    conn.commit()
    conn.close()

def get_project_info(project_id):
    conn = sqlite3.connect("data_engine_v3.db")
    cur = conn.cursor()
    cur.execute("SELECT total_rent, roommate_count FROM projects WHERE project_id=?", (project_id,))
    proj = cur.fetchone()
    if not proj:
        return None, None, []
    cur.execute("SELECT room_name, area, has_bath, light_score, quiet_score FROM rooms WHERE project_id=?", (project_id,))
    rooms = [{"name": row[0], "area": row[1], "bath": row[2], "light": row[3], "quiet": row[4]} for row in cur.fetchall()]
    conn.close()
    return proj[0], proj[1], rooms

def submit_or_update_bid(project_id, user_name, valuations):
    conn = sqlite3.connect("data_engine_v3.db")
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
    conn = sqlite3.connect("data_engine_v3.db")
    cur = conn.cursor()
    cur.execute("SELECT user_name, valuations_json FROM bids WHERE project_id=?", (project_id,))
    bids = cur.fetchall()
    conn.close()
    return bids

# =========================
# 后台数据获取函数
# =========================
def get_admin_data():
    conn = sqlite3.connect("data_engine_v3.db")
    df_projects = pd.read_sql_query("SELECT * FROM projects", conn)
    df_rooms = pd.read_sql_query("SELECT * FROM rooms", conn)
    df_bids = pd.read_sql_query("SELECT * FROM bids", conn)
    conn.close()
    return df_projects, df_rooms, df_bids

# =========================
# 核心算法
# =========================
def solve_fair_division(users, room_names, valuations, total_rent):
    n = len(users)
    row_ind, col_ind = linear_sum_assignment(-valuations)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}
    avg_price = total_rent / n

    def objective(p): return np.sum((p - avg_price) ** 2)
    constraints = [{"type": "eq", "fun": lambda p: np.sum(p) - total_rent}]
    for i in range(n):
        assigned = assignment_idx[i]
        for j in range(n):
            if j == assigned: continue
            constraints.append({"type": "ineq", "fun": lambda p, u=i, alt=j, ass=assigned: p[alt] - p[ass] + valuations[u, ass] - valuations[u, alt]})

    bounds = [(0, total_rent) for _ in range(n)]
    result = minimize(objective, np.full(n, avg_price), method="SLSQP", bounds=bounds, constraints=constraints)
    
    assignment = {users[i]: room_names[assignment_idx[i]] for i in range(n)}
    prices_map = {room_names[j]: round(float(result.x[j]), 2) for j in range(n)}
    return assignment, prices_map

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
    st.title("📊 数据指挥中心")
    st.caption("仅管理员可见的隐藏入口")
    
    SECRET_PASSWORD = "123" 
    
    pwd = st.text_input("请输入暗号：", type="password")
    if pwd == SECRET_PASSWORD:
        st.success("欢迎回来，主理人。这是你的数据资产。")
        
        df_projects, df_rooms, df_bids = get_admin_data()
        
        st.subheader("1. 房屋特征数据池 (房间属性)", anchor=False)
        st.dataframe(df_rooms, use_container_width=True)
        
        st.subheader("2. 用户行为与决策数据", anchor=False)
        st.dataframe(df_bids, use_container_width=True)
        
        st.subheader("3. 宏观项目数据", anchor=False)
        st.dataframe(df_projects, use_container_width=True)
        
        st.divider()
        csv_data = df_bids.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 一键导出用户出价数据 (CSV)",
            data=csv_data,
            file_name='behavior_data.csv',
            mime='text/csv',
            type="primary"
        )
    elif pwd != "":
        st.error("密码错误！")
        
    st.stop()

# ----------------- 场景 1：发起项目 -----------------
if not project_id:
    # 🌟 更新：更亲切的标题和副标题
    st.title("合租分房小助手", anchor=False)
    st.markdown("用最公平的方式，算出谁住哪间房，该付多少钱。告别因为房租分配产生的尴尬。")
    st.write("")
    
    with st.container(border=True):
        st.subheader("基础信息", anchor=False)
        total_rent = st.number_input("房屋总租金 (元)", value=3000.0, step=100.0)
        roommate_count = st.selectbox("入住总人数", [2, 3, 4], index=1)
        
        st.divider()
        st.markdown("📝 **录入房间特征**")
        st.caption("准确的描述能帮助室友给出最真实的心理价位。")
        
        rooms_data = []
        default_names = ["主卧", "次卧", "小次卧", "客厅"]
        
        for i in range(roommate_count):
            with st.expander(f"🚪 设置 {default_names[i]} 的具体细节", expanded=(i==0)):
                r_name = st.text_input("房间名称", default_names[i], key=f"name_{i}")
                
                col1, col2 = st.columns(2)
                with col1:
                    # 🌟 体验更新：面积改为直观的相对大小下拉菜单，收集1-5的分数
                    area_options = {
                        5: "极大 (主卧/非常宽敞)",
                        4: "较大 (大次卧)",
                        3: "中等 (标准房间)",
                        2: "较小 (小次卧/书房)",
                        1: "极小 (仅能放一张床)"
                    }
                    r_area = st.selectbox("📏 房间大小", options=[5, 4, 3, 2, 1], index=2, format_func=lambda x: area_options[x], key=f"area_{i}")
                    r_bath = st.checkbox("✅ 带独立卫浴", value=(i==0), key=f"bath_{i}")
                    
                with col2:
                    light_options = {
                        5: "5分 - 朝南大窗，全天有阳光",
                        4: "4分 - 朝东/西，半天有直射光",
                        3: "3分 - 有正常窗户，无直射光",
                        2: "2分 - 窗户较小或采光被遮挡",
                        1: "1分 - 无窗/极暗，白天需开灯"
                    }
                    quiet_options = {
                        5: "5分 - 极安静，隔音好不临街",
                        4: "4分 - 较安静，偶尔有轻微声音",
                        3: "3分 - 一般，关门后不影响睡眠",
                        2: "2分 - 较吵，紧邻客厅/卫生间",
                        1: "1分 - 很吵，临街马路/隔音极差"
                    }
                    
                    r_light = st.selectbox("☀️ 采光情况", options=[5, 4, 3, 2, 1], index=1, format_func=lambda x: light_options[x], key=f"light_{i}")
                    r_quiet = st.selectbox("🤫 安静程度", options=[5, 4, 3, 2, 1], index=2, format_func=lambda x: quiet_options[x], key=f"quiet_{i}")
                
                rooms_data.append({
                    "name": r_name, "area": r_area, "bath": 1 if r_bath else 0, 
                    "light": r_light, "quiet": r_quiet
                })
            
    st.write("") 
    if st.button("生成专属分房链接", type="primary", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        create_project(new_id, total_rent, roommate_count, rooms_data)
        st.query_params["project_id"] = new_id
        st.rerun()

# ----------------- 场景 2 & 3：填写与结果 -----------------
else:
    with st.container(border=True):
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.markdown("### 分房进行中...")
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
    share_link = f"http://localhost:8507/?project_id={project_id}"
    
    if len(current_bids) < roommate_count:
        st.info("👇 **第一步：邀请室友** \n\n请点击下方框内右上角的复制按钮，将链接发送到你们的微信群。")
        st.code(share_link, language="text")
        st.progress(len(current_bids) / roommate_count, text=f"提交进度: {len(current_bids)} / {roommate_count} 人已填")
        
        if st.session_state.current_user in submitted_users:
            with st.container(border=True):
                st.success(f"**{st.session_state.current_user}**，你的预期价格已锁定。")
                st.caption("在所有人提交前，你的出价对其他室友不可见。")
                
                my_bid_json = next((b[1] for b in current_bids if b[0] == st.session_state.current_user), None)
                if my_bid_json:
                    my_vals = json.loads(my_bid_json)
                    st.divider()
                    st.markdown("**你的出价清单：**")
                    for r_name, v in zip(room_names, my_vals):
                        st.markdown(f"- {r_name}: `{v} 元`")
            
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
                st.subheader("📝 填写你的心理预期", anchor=False)
                st.markdown(f"假设这个房子你一个人租（总租金 **{total_rent} 元**），你愿意为每个房间分配多少钱？")
                
                st.caption("🔍 各房间参数参考：")
                for r in rooms_data:
                    bath_txt = "独立卫浴" if r['bath'] else "公用卫浴"
                    
                    # 向下兼容：如果旧数据是填的平米数(如15.0)，就直接显示；如果是新数据的1-5，则显示中文描述
                    area_desc_map = {5: "极大", 4: "较大", 3: "中等", 2: "较小", 1: "极小"}
                    area_val = r['area']
                    if area_val in [1, 2, 3, 4, 5]:
                        area_desc = area_desc_map[int(area_val)]
                    else:
                        area_desc = f"约 {area_val}平米"
                        
                    light_desc_map = {5: "全天有阳光", 4: "半天直射光", 3: "正常窗户", 2: "采光较差", 1: "无窗/极暗"}
                    quiet_desc_map = {5: "极安静", 4: "较安静", 3: "一般", 2: "较吵", 1: "很吵"}
                    
                    light_desc = light_desc_map.get(r['light'], f"{r['light']}分")
                    quiet_desc = quiet_desc_map.get(r['quiet'], f"{r['quiet']}分")
                    
                    # 🌟 更新显示的文案格式
                    st.markdown(f"- **{r['name']}**: 大小: **{area_desc}** | {bath_txt} | 采光: **{light_desc}** | 安静: **{quiet_desc}**")
                
                st.divider()
                user_name = st.text_input("你是哪位室友？ (填入你的名字)")
                
                vals = []
                cols = st.columns(roommate_count)
                
                for i in range(roommate_count - 1):
                    r_name = room_names[i]
                    val = cols[i].number_input(r_name, value=float(total_rent/roommate_count), step=50.0, key=f"val_{i}")
                    vals.append(val)
                    
                last_room_name = room_names[-1]
                sum_previous = sum(vals)
                last_val = total_rent - sum_previous
                
                cols[-1].number_input(f"{last_room_name} (自动计算)", value=float(last_val), disabled=True)
                vals.append(last_val)
                
            if st.button("确认并提交", type="primary", use_container_width=True):
                if last_val < 0:
                    st.error("前面房间的金额太高，导致最后一个房间出现负数！")
                elif not user_name.strip():
                    st.error("别忘了填你的名字！")
                else:
                    submit_or_update_bid(project_id, user_name, vals)
                    st.session_state.current_user = user_name
                    st.rerun()

    else:
        st.balloons()
        st.success("🎉 所有室友已就位！")
        st.markdown("最优无嫉妒分配方案已永久生成：")
        
        users = [b[0] for b in current_bids]
        valuations = np.array([json.loads(b[1]) for b in current_bids])
        
        try:
            assignment, prices = solve_fair_division(users, room_names, valuations, total_rent)
            
            for i, u in enumerate(users):
                assigned_room = assignment[u]
                room_price = prices[assigned_room]
                
                st.markdown(f"""
                <div style="padding: 16px 20px; border-radius: 12px; background-color: #f5f5f7; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #e5e5ea;">
                    <div style="display: flex; flex-direction: column;">
                        <span style="font-size: 14px; color: #86868b; margin-bottom: 4px;">室友</span>
                        <span style="font-size: 18px; font-weight: 500; color: #1d1d1f;">{u}</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <span style="font-size: 14px; color: #86868b; margin-bottom: 4px;">分得房间</span>
                        <span style="font-size: 16px; font-weight: 500; color: #1d1d1f;">{assigned_room}</span>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end;">
                        <span style="font-size: 14px; color: #86868b; margin-bottom: 4px;">应付房租</span>
                        <span style="font-size: 20px; font-weight: 600; color: #0071e3;">¥ {room_price}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error("数据计算异常。")