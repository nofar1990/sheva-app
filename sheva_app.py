import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import base64

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # פענוח המפתח מ-Base64 כדי למנוע שגיאות PEM של תווים נסתרים
    try:
        encoded_key = st.secrets["base64_key"]
        decoded_key = base64.b64decode(encoded_key).decode("utf-8")
    except Exception as e:
        st.error(f"שגיאה בפענוח המפתח: {e}")
        return None

    info = {
        "type": "service_account",
        "project_id": "sheva-crm",
        "private_key_id": "ddf6cd036121d1f3f1b2342d3a44456d41c41b5b",
        "private_key": decoded_key,
        "client_email": "sheva-manager@sheva-crm.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def load_data():
    try:
        client = get_gsheet_client()
        if not client: return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
        sheet = client.open_by_url(st.secrets["gsheets_url"]).sheet1
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def save_to_sheet(row_dict):
    try:
        client = get_gsheet_client()
        if not client: return False
        sheet = client.open_by_url(st.secrets["gsheets_url"]).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        row_dict = {k: str(v) for k, v in row_dict.items()}
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
            df = df[df['ת.ז לקוח'] != row_dict['ת.ז לקוח']]
            
        df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ שגיאה טכנית: {e}")
        return False

# --- ממשק שבע ---
st.title("🛡️ שבע – מערכת לקוחות")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
    
    clients = df.groupby('ת.ז לקוח').agg({'שם לקוח': 'first', 'טלפון סלולרי': 'first'}).reset_index()
    search = st.text_input("חיפוש לקוח:")
    display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(10)

    for _, row in display_df.iterrows():
        cid = str(row['ת.ז לקוח'])
        stored = st.session_state.crm_data
        current = stored[stored['ת.ז לקוח'].astype(str) == cid]
        s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
        n_val = current['הערות'].values[0] if not current.empty else ""

        with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
            new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}", index=["חדש", "בטיפול", "הושלם"].index(s_val))
            new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
            if st.button("שמור שינויים", key=f"b_{cid}"):
                with st.spinner("שומר..."):
                    if save_to_sheet({'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}):
                        st.session_state.crm_data = load_data()
                        st.success("✅ נשמר!")
                        st.rerun()
