import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from transformers import pipeline
import re

# Set up page configurations
st.set_page_config(
    page_title="Live NBA Google Forms Dashboard",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Live Google Forms NBA Attainment Dashboard")
st.markdown("### **Real-Time Outcome-Based Education (OBE) Portal**")
st.write("This dashboard downloads real-time student submissions directly from active Google Form links and processes NBA metrics and AI sentiments on the fly.")

# =====================================================================
# 🛠️ CONFIGURATION: ADD YOUR LIVE GOOGLE SHEETS HERE
# =====================================================================
# 1. Replace the URLs below with your actual Google Sheet links.
# 2. Make sure the sheets are set to "Anyone with the link can view".
COURSE_LINKS = {
    "CS301 - Data Structures (Live)": "https://google.com",
    "EE202 - Circuit Theory (Live)": "https://google.com"
}

# Fallback/Demo setup if user hasn't added real working links yet
DEFAULT_DEMO_URL = "https://google.com"

# =====================================================================
# HELPER: CONVERT GOOGLE SHEET LINK TO LIVE CSV DOWNLOAD LINK
# =====================================================================
def convert_to_csv_url(sheet_url):
    # Extracts the core sheet ID and changes /edit to /export?format=csv
    if "://google.com" in sheet_url:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            sheet_id = match.group(1)
            return f"https://://google.com/d/{sheet_id}/export?format=csv"
    return sheet_url

# =====================================================================
# LIVE DATA FETCHING & REAL-TIME AI PIPELINE
# =====================================================================
@st.cache_resource # Keeps the AI model loaded in memory for speed
def load_ai_model():
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

sentiment_analyzer = load_ai_model()

@st.cache_data(ttl=10) # Live updates: refetches from the internet every 10 seconds if refreshed
def fetch_live_data(display_name, raw_url):
    csv_url = convert_to_csv_url(raw_url)
    
    try:
        # Pull data directly from Google over HTTP
        data = pd.read_csv(csv_url)
    except Exception as e:
        # Elegant fallback mock generation if the user runs the script using the mock links
        st.sidebar.warning(f"Using generated sandbox stream data for demo purposes.")
        data = pd.DataFrame({
            'CO1_Rating':,
            'CO2_Rating':,
            'CO3_Rating':,
            'Open_Ended_Feedback': [
                "Loved it.", "Lab systems for CO2 were down.", "Nice course.", 
                "Syllabus pacing for CO3 was too fast.", "All good.", "None",
                "Excellent.", "Final assignments felt completely rushed.", "Good", "Satisfactory."
            ]
        })
    
    # Run dynamic text column detection for feedback strings
    feedback_cols = [c for c in data.columns if 'FEEDBACK' in c.upper() or 'COMMENT' in c.upper() or 'SUGGESTION' in c.upper()]
    text_col = feedback_cols[0] if feedback_cols else 'Open_Ended_Feedback'
    
    if text_col not in data.columns:
        data[text_col] = "No feedback text column caught."
        
    # Standardize column naming convention for downstream scripts
    data = data.rename(columns={text_col: 'Open_Feedback'})
    data['Open_Feedback'] = data['Open_Feedback'].astype(str).fillna("").str.strip()
    
    # Process Real-Time AI Sentiments
    def evaluate_text(text):
        if text.lower() in ["", "none", "nothing", "good", "no", "na", "n/a", "all good"]:
            return "SATISFACTORY"
        try:
            res = sentiment_analyzer(text)[0]
            if res['label'] == 'NEGATIVE' and res['score'] > 0.70:
                return "ACTION REQUIRED (Negative Remark)"
            return "SATISFACTORY"
        except:
            return "SATISFACTORY"
            
    data["AI_Action_Status"] = data["Open_Feedback"].apply(evaluate_text)
    return data

# =====================================================================
# DROPDOWN SELECTOR LAYOUT
# =====================================================================
st.markdown("---")
selected_course = st.selectbox(
    "📂 Choose Live Active Course Stream:",
    options=list(COURSE_LINKS.keys())
)

# Fetch data live
target_link = COURSE_LINKS[selected_course]
df = fetch_live_data(selected_course, target_link)
total_responses = len(df)

# =====================================================================
# DYNAMIC CO COLUMN CALCULATION
# =====================================================================
# Automatically extracts any columns containing 'CO' or 'RATING' from the live form
co_columns = [col for col in df.columns if 'CO' in col.upper() or 'RATING' in col.upper()]

if not co_columns:
    st.error("❌ No Course Outcome (CO) or Rating columns detected in this Google Form. Please name your form questions containing phrases like 'CO1' or 'Rating'.")
    st.stop()

TARGET_SCORE = 3
attainment_data = []

for co in co_columns:
    df[co] = pd.to_numeric(df[co], errors='coerce').fillna(0)
    students_meeting_target = int((df[co] >= TARGET_SCORE).sum())
    percentage_attained = (students_meeting_target / total_responses) * 100 if total_responses > 0 else 0
    
    if percentage_attained >= 70: level = 3
    elif percentage_attained >= 60: level = 2
    elif percentage_attained >= 50: level = 1
    else: level = 0
        
    attainment_data.append({
        "Course Outcome": co, 
        "Attainment Percentage (%)": round(percentage_attained, 1),
        "NBA Attainment Level": level
    })

attainment_df = pd.DataFrame(attainment_data)

# =====================================================================
# METRIC CARDS RENDER
# =====================================================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric(label="Live Submissions Tracked", value=total_responses)
with kpi2:
    st.metric(label="Detected Form Questions", value=len(co_columns))
with kpi3:
    critical_alerts = int((df["AI_Action_Status"] == "ACTION REQUIRED (Negative Remark)").sum())
    st.metric(label="AI-Flagged Action Items", value=critical_alerts, delta=f"{critical_alerts} issues logged", delta_color="inverse")
with kpi4:
    avg_level = round(attainment_df["NBA Attainment Level"].mean(), 1)
    st.metric(label="Avg NBA Level attained", value=f"{avg_level} / 3.0")

# =====================================================================
# VISUAL ATTRIBUTES CHARTS
# =====================================================================
st.markdown("---")
col1, col2 = st.columns()

with col1:
    st.subheader("📉 Live Attainment Chart")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=attainment_df["Course Outcome"], y=attainment_df["Attainment Percentage (%)"],
        name="Students >= 3 (%)", marker_color='#00G8B5',
        text=attainment_df["Attainment Percentage (%)"].astype(str) + '%', textposition='auto'
    ))
    fig.add_trace(go.Scatter(
        x=attainment_df["Course Outcome"], y=attainment_df["NBA Attainment Level"] * 23.3, 
        name="NBA Level (0-3)", mode='lines+markers', line=dict(color='#FF5722', width=3), yaxis="y2"
    ))
    fig.update_layout(
        yaxis=dict(title="Attainment (%)", range=[0, 105]),
        yaxis2=dict(title="NBA Audit Level", overlaying="y", side="right", range=[0, 3.5]),
        legend=dict(x=0.01, y=0.99), hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 SAR Compliance Grid")
    st.dataframe(attainment_df, use_container_width=True, hide_index=True)

# =====================================================================
# ACTION TAKEN ENGINE (SAR CRITERION 7)
# =====================================================================
st.markdown("---")
st.subheader("🔍 Continuous Quality Loop (Live Action Item Tracker)")
status_filter = st.selectbox(
    "Filter live remarks by priority mapping:",
    options=["All Feedbacks", "ACTION REQUIRED (Negative Remark)", "SATISFACTORY"]
)

filtered_df = df if status_filter == "All Feedbacks" else df[df["AI_Action_Status"] == status_filter]
st.dataframe(filtered_df[["Open_Feedback", "AI_Action_Status"]].reset_index(drop=True), use_container_width=True)
