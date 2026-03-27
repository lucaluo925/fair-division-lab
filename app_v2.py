import os
import json
import uuid
import sqlite3
from datetime import datetime

import numpy as np
import streamlit as st
from scipy.optimize import linear_sum_assignment, minimize

DB_NAME = "/tmp/fairshare_v3.db" if os.path.exists("/mount/src") else "fairshare_v3.db"


# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(
    page_title="FairShare",
    page_icon="🏠",
    layout="centered"
)


# ==========================================
# 2. 数据库初始化（当前阶段：强制重建）
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS projects")
    cur.execute("DROP TABLE IF EXISTS rooms")
    cur.execute("DROP TABLE IF EXISTS bids")

    cur.execute("""
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            created_at TEXT,
            mode TEXT,
            total_rent REAL,
            roommate_count INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            room_name TEXT,
            area INTEGER,
            has_bath INTEGER,
            light_score INTEGER,
            quiet_score INTEGER,
            fixed_price REAL
        )
    """)

    cur.execute("""
        CREATE TABLE bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            user_name TEXT,
            valuations_json TEXT,
            last_submit_time TEXT,
            modify_count INTEGER
        )
    """)

    conn.commit()
    conn.close()


# 只在本次进程首次运行时初始化，避免每次交互都清空
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True


# ==========================================
# 3. 文案
# ==========================================
TEXT = {
    "EN": {
        "title": "FairShare",
        "subtitle": "An interactive tool for room allocation under real-world pricing constraints.",
        "step1_title": "Step 1: Apartment Setup",
        "mode_select": "Choose pricing mode",
        "mode_a": "Mode A: Total budget split",
        "mode_b": "Mode B: Fixed room prices + optional compensation",
        "mode_a_desc": "Use this when you only know the apartment's total rent and want the algorithm to determine a fair split.",
        "mode_b_desc": "Use this when each room already has a fixed lease price, but you still want a fair assignment and optional compensation reference.",
        "num_agents": "Number of roommates",
        "total_rent_input": "Total apartment rent",
        "room_name": "Room name",
        "fixed_price": "Fixed lease price",
        "area": "Space & size",
        "bath": "Private bathroom",
        "light": "Natural light",
        "quiet": "Quietness",
        "total_rent_calc": "Total calculated rent",
        "btn_generate": "Create FairShare Link",
        "invite_title": "Invite your roommates",
        "invite_desc": "Share this link. Everyone will submit privately.",
        "progress": "Progress: {0} / {1} submitted",
        "locked": "Your preferences are locked. Waiting for others...",
        "btn_refresh": "Refresh",
        "btn_edit": "Withdraw and edit bid",
        "input_title": "How much is each room worth to you?",
        "input_desc": "Enter your personal valuation for each room. The total must equal the apartment's total rent.",
        "agent_name": "Your name / nickname",
        "val_for": "Value for",
        "btn_submit": "Submit preferences",
        "err_matrix": "Please check your name and valuations.",
        "success_title": "Results Ready",
        "rent_to_pay": "Fair monthly rent",
        "layer1_title": "Layer 1: Recommended assignment",
        "layer1_desc": "This is the most efficient assignment based on everyone's submitted valuations.",
        "layer2_title": "Layer 2: Optional fairness adjustment",
        "layer2_desc": "If you want to further balance perceived fairness, the following transfers can be used as a negotiation reference.",
        "disclaimer": "Note: Side payments are optional recommendations, not enforced transfers. This tool does not change your actual lease.",
        "pays": "Suggested payment",
        "receives": "Suggested compensation",
        "no_transfer": "No adjustment needed",
        "market_price": "Contract price",
        "theory_price": "Algorithmic fair price",
        "net_transfer": "Optional side payment",
        "regret_tip": "After the final result is generated, bids are locked for this round. If you want a new outcome, start a new round.",
        "mode_a_result_desc": "Based on everyone's valuations, here is the recommended room assignment and fair rent split.",
        "invalid_link": "Invalid or expired link.",
        "copied_hint": "Copy and send this link to your roommates",
    },
    "ZH": {
        "title": "FairShare 科学分房",
        "subtitle": "在现实约束下，为合租室友提供分房建议与公平参考。",
        "step1_title": "第一步：设置公寓信息",
        "mode_select": "选择租金模式",
        "mode_a": "模式 A：总预算动态分摊",
        "mode_b": "模式 B：固定房价 + 可选补偿参考",
        "mode_a_desc": "适用于只知道公寓总租金、还没签具体房间价格的情况。",
        "mode_b_desc": "适用于每个房间价格已经固定，但仍想得到更公平的分配与补偿参考。",
        "num_agents": "合租人数",
        "total_rent_input": "公寓总租金",
        "room_name": "房间名称",
        "fixed_price": "固定房租",
        "area": "空间大小",
        "bath": "独立卫浴",
        "light": "采光情况",
        "quiet": "安静程度",
        "total_rent_calc": "系统计算总租金",
        "btn_generate": "生成专属链接",
        "invite_title": "邀请室友填写",
        "invite_desc": "把这个链接发到群里，大家分别填写。",
        "progress": "提交进度：{0} / {1}",
        "locked": "你的估值已锁定，正在等待其他人提交。",
        "btn_refresh": "刷新进度",
        "btn_edit": "撤回并修改估值",
        "input_title": "你觉得每个房间值多少钱？",
        "input_desc": "请填写你对每个房间的主观估值，总和必须等于公寓总租金。",
        "agent_name": "你的称呼",
        "val_for": "对该房的估值",
        "btn_submit": "确认提交",
        "err_matrix": "请检查你的名字和估值填写是否正确。",
        "success_title": "结果已生成",
        "rent_to_pay": "算法公平月租",
        "layer1_title": "第一层：推荐分配方案",
        "layer1_desc": "这是基于所有人主观估值计算出的最优分配。",
        "layer2_title": "第二层：可选公平补偿",
        "layer2_desc": "如果大家希望进一步平衡公平感，可以参考以下补偿金额进行协商。",
        "disclaimer": "说明：补偿金额仅作为协商参考，不是强制执行方案。本系统不会改变实际合同价格。",
        "pays": "建议补贴",
        "receives": "建议获得补偿",
        "no_transfer": "无需补偿",
        "market_price": "合同价格",
        "theory_price": "算法公平价",
        "net_transfer": "可选私下补偿",
        "regret_tip": "结果生成后，本轮估值将锁定。如果想重新计算，请重新开启新一轮。",
        "mode_a_result_desc": "以下是基于所有人估值得到的推荐分房方案与公平租金分摊。",
        "invalid_link": "链接无效或已失效。",
        "copied_hint": "复制下面链接发给室友",
    }
}

OPTIONS = {
    "EN": {
        "area": {
            5: "5 - Extremely spacious",
            4: "4 - Spacious",
            3: "3 - Average",
            2: "2 - Small",
            1: "1 - Tiny",
        },
        "light": {
            5: "5 - Full day direct sun",
            4: "4 - Half day sun",
            3: "3 - Standard window",
            2: "2 - Poor lighting",
            1: "1 - Very dark",
        },
        "quiet": {
            5: "5 - Very quiet",
            4: "4 - Mostly quiet",
            3: "3 - Average",
            2: "2 - Some noise",
            1: "1 - Very noisy",
        }
    },
    "ZH": {
        "area": {
            5: "5 - 很大",
            4: "4 - 较大",
            3: "3 - 中等",
            2: "2 - 较小",
            1: "1 - 很小",
        },
        "light": {
            5: "5 - 采光极佳",
            4: "4 - 采光较好",
            3: "3 - 一般",
            2: "2 - 偏暗",
            1: "1 - 很暗",
        },
        "quiet": {
            5: "5 - 很安静",
            4: "4 - 较安静",
            3: "3 - 一般",
            2: "2 - 偏吵",
            1: "1 - 很吵",
        }
    }
}


# ==========================================
# 4. 语言切换
# ==========================================
if "lang" not in st.session_state:
    st.session_state.lang = "ZH"

col_a, col_b = st.columns([5, 1])
with col_b:
    zh_on = st.toggle("中 / EN", value=(st.session_state.lang == "ZH"))
    st.session_state.lang = "ZH" if zh_on else "EN"

t = TEXT[st.session_state.lang]
opt = OPTIONS[st.session_state.lang]


# ==========================================
# 5. 数据库操作
# ==========================================
def create_project(project_id, mode, total_rent, roommate_count, rooms_data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO projects (
            project_id, created_at, mode, total_rent, roommate_count
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        project_id,
        datetime.now().isoformat(),
        mode,
        total_rent,
        roommate_count
    ))

    for r in rooms_data:
        cur.execute("""
            INSERT INTO rooms (
                project_id, room_name, area, has_bath, light_score, quiet_score, fixed_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            r["name"],
            r["area"],
            r["bath"],
            r["light"],
            r["quiet"],
            r["fixed_price"]
        ))

    conn.commit()
    conn.close()


def get_project_info(project_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT mode, total_rent, roommate_count
        FROM projects
        WHERE project_id=?
    """, (project_id,))
    proj = cur.fetchone()

    if not proj:
        conn.close()
        return None, None, None, []

    cur.execute("""
        SELECT room_name, area, has_bath, light_score, quiet_score, fixed_price
        FROM rooms
        WHERE project_id=?
        ORDER BY id ASC
    """, (project_id,))
    room_rows = cur.fetchall()
    conn.close()

    rooms = []
    for row in room_rows:
        rooms.append({
            "name": row[0],
            "area": row[1],
            "bath": row[2],
            "light": row[3],
            "quiet": row[4],
            "fixed_price": row[5]
        })

    return proj[0], proj[1], proj[2], rooms


def submit_or_update_bid(project_id, user_name, valuations):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT modify_count
        FROM bids
        WHERE project_id=? AND user_name=?
    """, (project_id, user_name))
    row = cur.fetchone()

    now_str = datetime.now().isoformat()

    if row:
        cur.execute("""
            UPDATE bids
            SET valuations_json=?, last_submit_time=?, modify_count=?
            WHERE project_id=? AND user_name=?
        """, (
            json.dumps(valuations),
            now_str,
            row[0] + 1,
            project_id,
            user_name
        ))
    else:
        cur.execute("""
            INSERT INTO bids (
                project_id, user_name, valuations_json, last_submit_time, modify_count
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            project_id,
            user_name,
            json.dumps(valuations),
            now_str,
            0
        ))

    conn.commit()
    conn.close()


def get_all_bids(project_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT user_name, valuations_json
        FROM bids
        WHERE project_id=?
        ORDER BY id ASC
    """, (project_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_bid(project_id, user_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM bids
        WHERE project_id=? AND user_name=?
    """, (project_id, user_name))
    conn.commit()
    conn.close()


# ==========================================
# 6. 算法
# ==========================================
def compute_envy_free_allocation(users, rooms_data, valuations_matrix, total_rent):
    n = len(users)
    room_names = [r["name"] for r in rooms_data]
    fixed_prices_map = {r["name"]: r["fixed_price"] for r in rooms_data}

    # Step 1: assignment
    row_ind, col_ind = linear_sum_assignment(-valuations_matrix)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}

    # Step 2: envy-free pricing approximation
    avg_price = total_rent / n

    def objective(p):
        return np.sum((p - avg_price) ** 2)

    constraints = [{
        "type": "eq",
        "fun": lambda p: np.sum(p) - total_rent
    }]

    for i in range(n):
        assigned_room = assignment_idx[i]
        for j in range(n):
            if j == assigned_room:
                continue

            constraints.append({
                "type": "ineq",
                "fun": lambda p, u=i, alt=j, ass=assigned_room:
                    p[alt] - p[ass] + valuations_matrix[u, ass] - valuations_matrix[u, alt]
            })

    bounds = [(0, total_rent) for _ in range(n)]
    initial_guess = np.full(n, avg_price)

    result = minimize(
        objective,
        initial_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        raise ValueError("Optimization failed. Please try another input.")

    assignment_result = {users[i]: room_names[assignment_idx[i]] for i in range(n)}
    theoretical_prices = {room_names[j]: round(float(result.x[j]), 2) for j in range(n)}

    side_payments = {}
    for user in users:
        assigned_room = assignment_result[user]
        side_payments[user] = round(
            theoretical_prices[assigned_room] - fixed_prices_map[assigned_room],
            2
        )

    return assignment_result, theoretical_prices, fixed_prices_map, side_payments


# ==========================================
# 7. 主流程
# ==========================================
query_params = st.query_params
project_id = query_params.get("project_id")

if "current_user" not in st.session_state:
    st.session_state.current_user = None


# ------------------------------------------
# A. 创建项目页
# ------------------------------------------
if not project_id:
    st.title(t["title"])
    st.caption(t["subtitle"])

    with st.container(border=True):
        st.subheader(t["step1_title"])

        mode = st.radio(
            t["mode_select"],
            ["Mode A", "Mode B"],
            format_func=lambda x: t["mode_a"] if x == "Mode A" else t["mode_b"]
        )

        if mode == "Mode A":
            st.caption(t["mode_a_desc"])
        else:
            st.caption(t["mode_b_desc"])

        roommate_count = st.selectbox(t["num_agents"], [2, 3, 4], index=1)
        st.divider()

        rooms_data = []
        default_names = ["Master Bedroom", "Room B", "Room C", "Room D"] if st.session_state.lang == "EN" else ["主卧", "次卧", "小次卧", "房间4"]

        if mode == "Mode A":
            total_rent = st.number_input(
                t["total_rent_input"],
                min_value=100.0,
                value=3000.0,
                step=100.0
            )
            total_rent_calculated = total_rent
        else:
            total_rent_calculated = 0.0

        for i in range(roommate_count):
            with st.expander(f"Room {i+1}" if st.session_state.lang == "EN" else f"房间 {i+1}", expanded=(i == 0)):
                room_name = st.text_input(
                    t["room_name"],
                    value=default_names[i],
                    key=f"room_name_{i}"
                )

                if mode == "Mode B":
                    fixed_price = st.number_input(
                        t["fixed_price"],
                        min_value=0.0,
                        value=1000.0,
                        step=50.0,
                        key=f"fixed_price_{i}"
                    )
                    total_rent_calculated += fixed_price
                else:
                    fixed_price = 0.0

                c1, c2 = st.columns(2)
                with c1:
                    area = st.selectbox(
                        t["area"],
                        options=[5, 4, 3, 2, 1],
                        format_func=lambda x: opt["area"][x],
                        index=2,
                        key=f"area_{i}"
                    )
                    bath = st.checkbox(
                        t["bath"],
                        value=(i == 0),
                        key=f"bath_{i}"
                    )
                with c2:
                    light = st.selectbox(
                        t["light"],
                        options=[5, 4, 3, 2, 1],
                        format_func=lambda x: opt["light"][x],
                        index=2,
                        key=f"light_{i}"
                    )
                    quiet = st.selectbox(
                        t["quiet"],
                        options=[5, 4, 3, 2, 1],
                        format_func=lambda x: opt["quiet"][x],
                        index=2,
                        key=f"quiet_{i}"
                    )

                rooms_data.append({
                    "name": room_name,
                    "area": area,
                    "bath": 1 if bath else 0,
                    "light": light,
                    "quiet": quiet,
                    "fixed_price": fixed_price
                })

        if mode == "Mode B":
            st.info(f"{t['total_rent_calc']}: {total_rent_calculated:.2f}")

        if st.button(t["btn_generate"], type="primary", use_container_width=True):
            new_id = str(uuid.uuid4())[:8]
            create_project(new_id, mode, total_rent_calculated, roommate_count, rooms_data)
            st.query_params["project_id"] = new_id
            st.rerun()


# ------------------------------------------
# B. 项目页
# ------------------------------------------
else:
    mode, total_rent, roommate_count, rooms_data = get_project_info(project_id)

    if not total_rent:
        st.error(t["invalid_link"])
        st.stop()

    current_bids = get_all_bids(project_id)
    submitted_users = [b[0] for b in current_bids]
    share_link = f"https://fairdivisionlab-fd6majrlizgnvoa3y5fnui.streamlit.app/?project_id={project_id}"

    # -----------------------------
    # B1. 收集出价阶段
    # -----------------------------
    if len(current_bids) < roommate_count:
        st.title(t["title"])
        st.subheader(t["invite_title"])
        st.caption(t["invite_desc"])
        st.code(share_link, language="text")
        st.caption(t["copied_hint"])
        st.progress(len(current_bids) / roommate_count, text=t["progress"].format(len(current_bids), roommate_count))

        if st.session_state.current_user in submitted_users:
            st.success(t["locked"])

            b1, b2 = st.columns(2)
            with b1:
                if st.button(t["btn_refresh"], use_container_width=True):
                    st.rerun()
            with b2:
                if st.button(t["btn_edit"], use_container_width=True):
                    delete_bid(project_id, st.session_state.current_user)
                    st.session_state.current_user = None
                    st.rerun()

        else:
            with st.container(border=True):
                st.subheader(t["input_title"])
                st.caption(t["input_desc"])

                user_name = st.text_input(t["agent_name"])

                vals = []
                cols = st.columns(roommate_count)

                for i in range(roommate_count - 1):
                    val = cols[i].number_input(
                        f"{t['val_for']} {rooms_data[i]['name']}",
                        min_value=0.0,
                        value=float(total_rent / roommate_count),
                        step=50.0,
                        key=f"val_{project_id}_{i}"
                    )
                    vals.append(val)

                last_val = total_rent - sum(vals)
                cols[-1].number_input(
                    f"{t['val_for']} {rooms_data[-1]['name']}",
                    value=float(last_val),
                    disabled=True,
                    key=f"last_val_auto_{project_id}"
                )
                vals.append(last_val)

                if st.button(t["btn_submit"], type="primary", use_container_width=True):
                    if not user_name.strip() or last_val < 0:
                        st.error(t["err_matrix"])
                    else:
                        submit_or_update_bid(project_id, user_name.strip(), vals)
                        st.session_state.current_user = user_name.strip()
                        st.rerun()

    # -----------------------------
    # B2. 结果展示阶段
    # -----------------------------
    else:
        st.title(t["success_title"])

        users = [b[0] for b in current_bids]
        valuations = np.array([json.loads(b[1]) for b in current_bids])

        try:
            assignment, theoretical_prices, fixed_prices, side_payments = compute_envy_free_allocation(
                users, rooms_data, valuations, total_rent
            )

            # 模式 A
            if mode == "Mode A":
                st.caption(t["mode_a_result_desc"])

                for user in users:
                    assigned_room = assignment[user]
                    fair_price = theoretical_prices[assigned_room]

                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**{user}**")
                            st.write(assigned_room)
                        with c2:
                            st.markdown(f"**{t['rent_to_pay']}**")
                            st.write(f"{fair_price:.2f}")

            # 模式 B
            else:
                st.subheader(t["layer1_title"])
                st.caption(t["layer1_desc"])

                cols = st.columns(roommate_count)
                for i, user in enumerate(users):
                    assigned_room = assignment[user]
                    with cols[i]:
                        with st.container(border=True):
                            st.markdown(f"**{user}**")
                            st.write(assigned_room)

                st.divider()

                st.subheader(t["layer2_title"])
                st.caption(t["layer2_desc"])
                st.warning(t["disclaimer"])

                for user in users:
                    assigned_room = assignment[user]
                    fixed_p = fixed_prices[assigned_room]
                    fair_p = theoretical_prices[assigned_room]
                    sp = side_payments[user]

                    with st.container(border=True):
                        st.markdown(f"**{user} -> {assigned_room}**")

                        r1, r2 = st.columns(2)
                        with r1:
                            st.write(f"{t['market_price']}: {fixed_p:.2f}")
                        with r2:
                            st.write(f"{t['theory_price']}: {fair_p:.2f}")

                        if sp > 0:
                            st.write(f"{t['net_transfer']}: {t['pays']} {sp:.2f}")
                        elif sp < 0:
                            st.write(f"{t['net_transfer']}: {t['receives']} {abs(sp):.2f}")
                        else:
                            st.write(f"{t['net_transfer']}: {t['no_transfer']}")

            st.info(t["regret_tip"])

        except Exception as e:
            st.error(f"Calculation Error / 计算出错: {e}")
