import streamlit as st
import sqlite3
import pandas as pd
st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}
h1, h2, h3 {
    color: #1f2937;
}
.stButton>button {
    background-color: #4CAF50;
    color: white;
    border-radius: 8px;
    padding: 6px 12px;
}
.stTextInput>div>div>input {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(layout="wide")

# DB Connection
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

# Create table
c.execute('''CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    title TEXT,
    target REAL,
    weightage INTEGER,
    uom TEXT,
    status TEXT,
    approved INTEGER DEFAULT 0,
    achievement REAL DEFAULT 0,
    progress_status TEXT DEFAULT 'Not Started',
    manager_comment TEXT DEFAULT ''
)''')
conn.commit()

st.markdown("## 🎯 Goal Setting & Tracking Portal")
st.caption("Smart performance tracking system for employees, managers, and admins")

role = st.selectbox("Select Role", ["Employee", "Manager", "Admin"])
user = st.text_input("Enter Username")

# ================= EMPLOYEE =================
if role == "Employee":

    st.header("🧑‍💻 Create Goals")

    # session state for dynamic goals
    if "goal_count" not in st.session_state:
        st.session_state.goal_count = 1

    if st.button("➕ Add Goal"):
        if st.session_state.goal_count < 8:
            st.session_state.goal_count += 1

    goals = []

    for i in range(st.session_state.goal_count):
        st.subheader(f"Goal {i+1}")

        col1, col2, col3 = st.columns(3)

        with col1:
            title = st.text_input("Title", key=f"title{i}")
        with col2:
            target = st.number_input("Target", key=f"target{i}")
        with col3:
            weight = st.number_input("Weightage", key=f"weight{i}")

        uom = st.selectbox("UoM", ["Min", "Max", "Zero"], key=f"uom{i}")

        if title:
            goals.append((title, target, weight, uom))

    if st.button("Submit Goals"):

        total_weight = sum([g[2] for g in goals])

        if total_weight != 100:
            st.error("❌ Total weightage must be 100")
        elif any(g[2] < 10 for g in goals):
            st.error("❌ Each goal must have min 10 weightage")
        elif len(goals) > 8:
            st.error("❌ Max 8 goals allowed")
        else:
            for g in goals:
                c.execute("INSERT INTO goals (user,title,target,weightage,uom,status) VALUES (?,?,?,?,?,?)",
                          (user, g[0], g[1], g[2], g[3], "Submitted"))
            conn.commit()
            st.success("✅ Goals Submitted Successfully!")

    # ================= UPDATE =================
    st.header("📊 Update Progress")

    df = pd.read_sql(f"SELECT * FROM goals WHERE user='{user}' AND approved=1", conn)

    if df.empty:
        st.info("No approved goals yet")
    else:
        for index, row in df.iterrows():

            st.write(f"**{row['title']}** (Target: {row['target']})")
        
            ach = st.number_input("Achievement", key=f"ach{index}")
        
            status = st.selectbox(
                "Status",
                ["Not Started", "On Track", "Completed"],
                key=f"status{index}"
            )
        
            if st.button(f"Update Goal {index}"):
                c.execute(
                    "UPDATE goals SET achievement=?, progress_status=? WHERE id=?",
                    (ach, status, row["id"])
                )
                conn.commit()
                st.success("Updated Successfully!")
# ================= MANAGER =================
elif role == "Manager":

    st.header("👨‍💼 Approve Goals")

    df = pd.read_sql("SELECT * FROM goals", conn)

    if df.empty:
        st.info("No goals found")
    else:
        for index, row in df.iterrows():

            st.write(f"User: {row['user']} | Goal: {row['title']} | Weight: {row['weightage']}")

            col1, col2 = st.columns(2)

            with col1:
                if row["approved"] == 0:
                    if st.button(f"Approve {row['id']}"):
                        c.execute("UPDATE goals SET approved=1 WHERE id=?", (row["id"],))
                        conn.commit()
                        st.success("Approved")
                        st.rerun()

            with col2:
                if row["approved"] == 0:
                    if st.button(f"Reject {row['id']}"):
                        c.execute("DELETE FROM goals WHERE id=?", (row["id"],))
                        conn.commit()
                        st.warning("Rejected")
                        st.rerun()

            # 🔥 COMMENT (inside loop)
            comment = st.text_input(f"Comment", key=f"comment{row['id']}")

            if st.button(f"Save Comment {row['id']}"):
                c.execute(
                    "UPDATE goals SET manager_comment=? WHERE id=?",
                    (comment, row["id"])
                )
                conn.commit()
                st.success("Comment Saved")

# ================= ADMIN =================
elif role == "Admin":

    st.header("🧑‍💻 Admin Dashboard")

    df = pd.read_sql("SELECT * FROM goals", conn)
    st.dataframe(df)

    if st.button("⬇ Download CSV"):
        df.to_csv("report.csv", index=False)
        st.success("Downloaded!")

# ================= PROGRESS =================
# ================= PROGRESS =================
st.header("📈 Progress Dashboard")

df = pd.read_sql("SELECT * FROM goals WHERE approved=1", conn)

if df.empty:
    st.info("No approved goals to show")
else:

    titles = []
    targets = []
    achievements = []

    for index, row in df.iterrows():

        progress = 0

        if row["uom"] == "Min":
            if row["target"] != 0:
                progress = row["achievement"] / row["target"]

        elif row["uom"] == "Max":
            if row["achievement"] != 0:
                progress = row["target"] / row["achievement"]

        elif row["uom"] == "Zero":
            progress = 1 if row["achievement"] == 0 else 0

        progress_percent = round(progress * 100, 2)

        # 🔥 AUTO STATUS + INSIGHT
        if progress_percent < 50:
            auto_status = "Behind Schedule"
            insight = "⚠️ Behind Schedule"
        elif progress_percent < 100:
            auto_status = "On Track"
            insight = "✅ On Track"
        else:
            auto_status = "Completed"
            insight = "🏆 Completed"

        # 🎨 CARD STYLE UI
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {row['title']}")
            st.progress(min(progress, 1.0))
            st.write(f"Progress: {progress_percent}%")
            st.write(f"Insight: {insight}")

        with col2:
            st.markdown(f"**Status:** {auto_status}")
            st.markdown(f"💬 {row['manager_comment']}")

        st.divider()

        # collect for chart
        titles.append(row["title"])
        targets.append(row["target"])
        achievements.append(row["achievement"])

    # 📊 Analytics Dashboard
    st.subheader("📊 Analytics Dashboard")

    chart_data = pd.DataFrame({
        "Goal": titles,
        "Target": targets,
        "Achievement": achievements
    })

    st.bar_chart(chart_data.set_index("Goal"))

    # 📈 Metrics
    avg_progress = sum(achievements) / sum(targets) * 100 if sum(targets) != 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Goals", len(titles))
    col2.metric("Completed", sum(1 for a, t in zip(achievements, targets) if a >= t))
    col3.metric("Avg Progress", f"{round(avg_progress,2)}%")