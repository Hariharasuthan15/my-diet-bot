import streamlit as st
import sqlite3
from datetime import date
import google.generativeai as genai
import json

# Page Config
st.set_page_config(page_title="Diet Tracker", page_icon="🏋️")

# 1. Password Protection
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Login")
        pwd = st.text_input("Enter Password", type="password")
        if st.button("Unlock"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong password!")
        return False
    return True

if not check_password():
    st.stop()

# 2. Local Database
conn = sqlite3.connect("nutrition.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        food TEXT,
        calories REAL,
        protein REAL
    )
""")
conn.commit()

# 3. AI Client Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-latest")

st.title("🏋️ Daily Diet Tracker")
st.caption("Target: 2,350 kcal | 100g Protein")

# Calculate Today's Totals
today_str = date.today().isoformat()
cursor.execute("SELECT SUM(calories), SUM(protein) FROM meals WHERE date = ?", (today_str,))
row = cursor.fetchone()
cals_today = row[0] or 0.0
protein_today = row[1] or 0.0

col1, col2 = st.columns(2)
col1.metric("Calories", f"{cals_today:.0f} / 2350 kcal", delta=f"{2350 - cals_today:.0f} remaining", delta_color="inverse")
col2.metric("Protein", f"{protein_today:.1f} / 100 g", delta=f"{100 - protein_today:.1f}g remaining", delta_color="inverse")

# Show Today's Logged Items
with st.expander("📋 Today's Meals"):
    cursor.execute("SELECT food, calories, protein FROM meals WHERE date = ? ORDER BY id DESC", (today_str,))
    meals = cursor.fetchall()
    if not meals:
        st.write("No meals logged yet today.")
    for item in meals:
        st.markdown(f"- **{item[0]}**: {item[1]:.0f} kcal | {item[2]:.1f}g protein")

# Reset Button
if st.button("Clear Today's Log"):
    cursor.execute("DELETE FROM meals WHERE date = ?", (today_str,))
    conn.commit()
    st.rerun()

# 4. Chat Input
if prompt_text := st.chat_input("E.g., 3 eggs with yolk, 50g soya chunks curry..."):
    st.chat_message("user").write(prompt_text)

    sys_instruction = """
    You are a nutrition calculator for an Indian diet. The user is a 53kg gym-goer aiming for weight gain.
    Analyze the user input, parse the food items, and accurately estimate total calories and protein.
    Return ONLY a single valid JSON object in this exact format:
    {
      "food_summary": "Short English summary of items logged",
      "calories": 0.0,
      "protein": 0.0,
      "reply_tamil": "Friendly short response in Tamil/Tanglish with calories, protein and encouraging words"
    }
    """

    try:
        full_prompt = f"{sys_instruction}\nUser ate: {prompt_text}"
        response = model.generate_content(full_prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)

        cursor.execute(
            "INSERT INTO meals (date, food, calories, protein) VALUES (?, ?, ?, ?)",
            (today_str, data["food_summary"], float(data["calories"]), float(data["protein"]))
        )
        conn.commit()
        st.success(data.get("reply_tamil", "Logged successfully!"))
        st.rerun()
    except Exception as e:
        st.error(f"Actual Error: {e}")
      
