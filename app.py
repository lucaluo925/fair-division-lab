import json
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from scipy.optimize import linear_sum_assignment, minimize


# =========================
# 数据库
# =========================
def init_db():
    conn = sqlite3.connect("submissions.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            roommate_count INTEGER NOT NULL,
            total_rent REAL NOT NULL,
            users_json TEXT NOT NULL,
            rooms_json TEXT NOT NULL,
            valuations_json TEXT NOT NULL,
            assignment_json TEXT NOT NULL,
            prices_json TEXT NOT NULL,
            conflict_json TEXT NOT NULL,
            compromise_json TEXT NOT NULL,
            labels_json TEXT NOT NULL,
            envy_free INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_case(data):
    conn = sqlite3.connect("submissions.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cases (
            created_at, roommate_count, total_rent,
            users_json, rooms_json, valuations_json,
            assignment_json, prices_json, conflict_json,
            compromise_json, labels_json, envy_free
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["created_at"],
        data["roommate_count"],
        data["total_rent"],
        json.dumps(data["users"], ensure_ascii=False),
        json.dumps(data["rooms"], ensure_ascii=False),
        json.dumps(data["valuations"], ensure_ascii=False),
        json.dumps(data["assignment"], ensure_ascii=False),
        json.dumps(data["prices"], ensure_ascii=False),
        json.dumps(data["conflict_index"], ensure_ascii=False),
        json.dumps(data["compromise_scores"], ensure_ascii=False),
        json.dumps(data["behavioral_labels"], ensure_ascii=False),
        1 if data["envy_free"] else 0
    ))
    conn.commit()
    conn.close()


# =========================
# 核心算法
# =========================
def solve_fair_division(users, rooms, valuations, total_rent):
    n = len(users)

    if len(rooms) != n:
        raise ValueError("室友人数必须等于房间数量。")

    for i in range(n):
        row_sum = np.sum(valuations[i])
        if not np.isclose(row_sum, total_rent, atol=1e-6):
            raise ValueError(f"{users[i]} 的估值总和是 {row_sum:.2f}，不等于总租金 {total_rent:.2f}。")

    # Step 1: 匹配
    row_ind, col_ind = linear_sum_assignment(-valuations)
    assignment_idx = {int(i): int(col_ind[i]) for i in range(n)}

    # Step 2: 求价格
    avg_price = total_rent / n

    def objective(p):
        return np.sum((p - avg_price) ** 2)

    constraints = []
    constraints.append({
        "type": "eq",
        "fun": lambda p: np.sum(p) - total_rent
    })

    for i in range(n):
        assigned = assignment_idx[i]
        for j in range(n):
            if j == assigned:
                continue

            def make_constraint(user_idx, alt_room_idx, assigned_room_idx):
                return lambda p: (
                    p[alt_room_idx]
                    - p[assigned_room_idx]
                    + valuations[user_idx, assigned_room_idx]
                    - valuations[user_idx, alt_room_idx]
                )

            constraints.append({
                "type": "ineq",
                "fun": make_constraint(i, j, assigned)
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
        raise ValueError("无法找到满足条件的价格，请重新填写。")

    prices = result.x
    envy_free = check_envy_free(valuations, assignment_idx, prices)

    assignment = {users[i]: rooms[assignment_idx[i]] for i in range(n)}
    prices_map = {rooms[j]: round(float(prices[j]), 2) for j in range(n)}

    conflict_index = compute_conflict_index(rooms, valuations)
    compromise_scores = compute_compromise_scores(users, valuations, assignment_idx)
    behavioral_labels = compute_behavioral_labels(users, valuations, total_rent)

    return {
        "assignment": assignment,
        "prices": prices_map,
        "envy_free": envy_free,
        "conflict_index": conflict_index,
        "compromise_scores": compromise_scores,
        "behavioral_labels": behavioral_labels
    }

def check_envy_free(valuations, assignment_idx, prices, tolerance=1e-5):
    n = valuations.shape[0]
    for i in range(n):
        assigned = assignment_idx[i]
        my_utility = valuations[i, assigned] - prices[assigned]
        for j in range(n):
            if valuations[i, j] - prices[j] > my_utility + tolerance:
                return False
    return True

def compute_conflict_index(rooms, valuations):
    result = {}
    for j, room in enumerate(rooms):
        result[room] = round(float(np.var(valuations[:, j])), 2)
    return result

def compute_compromise_scores(users, valuations, assignment_idx):
    result = {}
    for i, user in enumerate(users):
        best_value = float(np.max(valuations[i]))
        assigned_value = float(valuations[i, assignment_idx[i]])
        result[user] = round(best_value - assigned_value, 2)
    return result

def compute_behavioral_labels(users, valuations, total_rent):
    result = {}
    for i, user in enumerate(users):
        row = valuations[i]
        max_share = np.max(row) / total_rent
        std_ratio = np.std(row) / total_rent

        if max_share >= 0.50:
            label = "核心资源偏好者"
        elif std_ratio <= 0.08:
            label = "均衡型估值者"
        else:
            label = "价格敏感型估值者"

        result[user] = label
    return result


# =========================
# 页面 (Streamlit UI)
# =========================
st.set_page_config(page_title="Fair Division Lab", page_icon="🏠")
init_db()

st.title("🏠 Fair Division Lab")

roommate_count = st.sidebar.selectbox("人数", [2, 3, 4], index=1)
total_rent = st.sidebar.number_input("总租金", value=3000.0)

users = []
rooms = []
valuations = np.zeros((roommate_count, roommate_count))

st.subheader("1. 填写名字")
user_cols = st.columns(roommate_count)
for i in range(roommate_count):
    users.append(user_cols[i].text_input(f"室友 {i+1}", f"User {i+1}"))

st.subheader("2. 填写房间")
room_cols = st.columns(roommate_count)
default_rooms = ["主卧", "次卧", "客厅", "房间4"]
for j in range(roommate_count):
    # 防止选择人数超过默认房间名字时报错
    default_name = default_rooms[j] if j < len(default_rooms) else f"房间 {j+1}"
    rooms.append(room_cols[j].text_input(f"房间 {j+1}", default_name))

st.subheader("3. 盲填心理价位")
st.info(f"注意：每个人对自己那一行的估值加起来，必须等于总租金 {total_rent}")

for i in range(roommate_count):
    st.markdown(f"**{users[i]} 的估值**")
    val_cols = st.columns(roommate_count)
    for j in range(roommate_count):
        valuations[i][j] = val_cols[j].number_input(
            f"对 {rooms[j]}",
            value=total_rent/roommate_count,
            key=f"{i}_{j}"
        )
    st.divider()

if st.button("🚀 一键计算分配方案", type="primary"):
    try:
        result = solve_fair_division(users, rooms, valuations, total_rent)

        st.success("计算成功！")
        
        st.write("### ✅ 分配结果")
        st.json(result["assignment"])

        st.write("### 💰 应付价格")
        st.json(result["prices"])

        st.write("### 🛡️ 是否无嫉妒 (Envy-Free)")
        st.write(result["envy_free"])

        st.write("### ⚠️ 冲突指数")
        st.json(result["conflict_index"])

        save_case({
            "created_at": datetime.now().isoformat(),
            "roommate_count": roommate_count,
            "total_rent": total_rent,
            "users": users,
            "rooms": rooms,
            "valuations": valuations.tolist(),
            "assignment": result["assignment"],
            "prices": result["prices"],
            "conflict_index": result["conflict_index"],
            "compromise_scores": result["compromise_scores"],
            "behavioral_labels": result["behavioral_labels"],
            "envy_free": result["envy_free"]
        })

        st.toast("数据已保存到本地！", icon="💾")

    except Exception as e:
        st.error(f"报错啦：{str(e)}")