import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# הגדרות עיצוב
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { color: #1e2130 !important; font-weight: bold !important; }
    .stMetric { background-color: #ffffff !important; border: 1px solid #c5a059 !important; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e2130 !important; text-align: right; direction: rtl; }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-left: 5px; display: inline-block; margin-bottom: 5px; }
    .bg-premium { background-color: #f3e5f5; color: #7b1fa2; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ שבע – מערכת לקוחות")

# --- חיבור לגוגל שיטס ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_crm_data():
    try:
        return conn.read(spreadsheet=st.secrets["gsheets_url"], ttl="0s")
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון_אחרון'])

def save_crm_data(new_data_row):
    existing_data = load_crm_data()
    # הסרת שורה קיימת אם יש עדכון
    existing_data = existing_data[existing_data['ת.ז לקוח'] != new_data_row['ת.ז לקוח']]
    updated_data = pd.concat([existing_data, pd.DataFrame([new_data_row])], ignore_index=True)
    conn.update(spreadsheet=st.secrets["gsheets_url"], data=updated_data)

crm_df = load_crm_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        
        clients = df.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first', 'טלפון סלולרי': 'first', 'סך חסכון': 'sum', 'פרמיה חודשית': 'sum'
        }).reset_index()

        search = st.text_input("חיפוש לקוח:")
        display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(10)

        for _, row in display_df.iterrows():
            cid = row['ת.ז לקוח']
            # שליפת מידע קיים מהשיטס
            current_info = crm_df[crm_df['ת.ז לקוח'] == cid]
            saved_status = current_info['סטטוס'].values[0] if not current_info.empty else "חדש"
            saved_note = current_info['הערות'].values[0] if not current_info.empty else ""
            saved_agent = current_info['נציג'].values[0] if not current_info.empty else "יונתן תורגמן"

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {saved_status}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"📞 {row['טלפון סלולרי']}")
                    st.write(f"💰 פרמיה: ₪{row['פרמיה חודשית']:,.0f}")
                with col2:
                    status = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}", index=["חדש", "בטיפול", "הושלם"].index(saved_status))
                    agent = st.selectbox("סוכן:", ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן"], key=f"a_{cid}", index=["יונתן תורגמן", "אור בן עזרא", "עומרי כהן"].index(saved_agent) if saved_agent in ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן"] else 0)
                    note = st.text_area("הערות:", value=saved_note, key=f"n_{cid}")
                    if st.button("שמור שינויים", key=f"b_{cid}"):
                        save_crm_data({
                            'ת.ז לקוח': cid, 'סטטוס': status, 'נציג': agent, 
                            'הערות': note, 'עדכון_אחרון': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success("נשמר בשיטס!")

    except Exception as e:
        st.error(f"שגיאה: {e}")
