import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# הגדרות עיצוב - שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { color: #1e2130 !important; font-weight: bold !important; }
    .stMetric { background-color: #ffffff !important; border: 1px solid #c5a059 !important; border-radius: 10px; }
    h1, h2, h3 { color: #1e2130 !important; text-align: right; direction: rtl; }
    div[data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #ddd !important; direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ שבע – מערכת לקוחות")

# --- פונקציות זיכרון (CRM) ---
if 'crm_data' not in st.session_state:
    st.session_state['crm_data'] = {}

def save_to_crm(client_id, status, agent, note):
    st.session_state['crm_data'][client_id] = {
        'status': status,
        'agent': agent,
        'note': note,
        'last_update': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    st.success(f"הנתונים עבור {client_id} נשמרו בהצלחה!")

# טעינת נתונים
uploaded_file = st.file_uploader("טעינת נתוני ROETO המפורטים", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # עיבוד נתונים
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        df['סך חסכון'] = pd.to_numeric(df['סך חסכון'], errors='coerce').fillna(0)
        
        clients = df.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first',
            'טלפון סלולרי': 'first',
            'סך חסכון': 'sum',
            'שם יצרן': lambda x: list(set(x.dropna())),
            'סוג מוצר': lambda x: list(set(x.dropna())),
        }).reset_index()

        # מדדים עליונים
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("סה\"כ לקוחות", len(clients))
        with c2: st.metric("נכסים בניהול (AUM)", f"₪{clients['סך חסכון'].sum():,.0f}")
        with c3: st.metric("יצרנים פעילים", len(df['שם יצרן'].unique()))

        st.write("---")

        # חיפוש וניהול
        search = st.text_input("חיפוש לקוח לטיפול:")
        display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(15)

        # רשימת הסוכנים המעודכנת - יונתן ראשון כברירת מחדל
        agent_options = ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן", "דניאל כהן", "דורי רז"]

        for _, row in display_df.iterrows():
            cid = row['ת.ז לקוח']
            # משיכת נתונים שמורים או ערכי ברירת מחדל
            saved = st.session_state['crm_data'].get(cid, {'status': 'חדש', 'agent': 'יונתן תורגמן', 'note': ''})
            
            with st.expander(f"👤 {row['שם לקוח']} | סוכן: {saved['agent']} | נכסים: ₪{row['סך חסכון']:,.0f}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write(f"**📞 טלפון:** {row['טלפון סלולרי']}")
                    st.write(f"**🏢 יצרנים בתיק:** {', '.join(row['שם יצרן'])}")
                    st.write(f"**📊 מוצרים:** {', '.join(row['סוג מוצר'])}")
                
                with col2:
                    new_status = st.selectbox("עדכון סטטוס:", ["חדש", "בטיפול", "הושלם", "לא ענה"], 
                                              index=["חדש", "בטיפול", "הושלם", "לא ענה"].index(saved['status']), key=f"st_{cid}")
                    
                    # בחירת סוכן עם יונתן כברירת מחדל
                    current_agent_idx = agent_options.index(saved['agent']) if saved['agent'] in agent_options else 0
                    new_agent = st.selectbox("נציג מטפל:", agent_options, index=current_agent_idx, key=f"ag_{cid}")
                    
                    new_note = st.text_area("הערות וסיכום שיחה:", value=saved['note'], key=f"nt_{cid}")
                    
                    if st.button("שמור שינויים", key=f"btn_{cid}"):
                        save_to_crm(cid, new_status, new_agent, new_note)

    except Exception as e:
        st.error(f"שגיאה: {e}")