import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # המפתח הפרטי מחולק לשורות - שיטת ה-strip() והסינון מוודאים ששום תו נסתר לא ישבור את ה-PEM
    key_lines = [
        "-----BEGIN PRIVATE KEY-----",
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDgx0d6ZMNqpXgL",
        "WiogMgcSmS7QIuKimUE9LJGBpImMedHQaPqwBJsl2ifHlvV9NXm8z1waI+GF+qUS",
        "/NwZT7ZwqY4NhfRe1eYiJkaEFoU31wWHWRT6hg1tMP0Kppc+S37OAiNK92NLJig+",
        "qkIKPnoKXHtboCdJ2Tn0IeVNpAPqDpwGcYbI14Kg0xsUZlRVYT46CxjHF/rAEwcq",
        "fADoMH4iUJOFHh2KPOL8F9FA4Ljqs/gtzr/oEFu2dZXFmIXYG5IaEn2hyWusQBpT",
        "Od1R2HT/Wh7iaJAsnuvAj5TYhzlSHdeabc31CkgsEM2iwqQboyEwD3DTEx+Gkxlu",
        "xDMlr/3lAgMBAAECggEADWMpCWvbbKxevjRYSnMYUz3+2QQe4ebFSS6wmttRGuX9",
        "fk9mUNnxYJuB34QI6nRnI/zopCDrc2aWcs9PD43dFJAwpvMJtyU/r9x+Ois6M3Vx",
        "vZorYvFddtmiVIJQAzSNYJklf3dE+WqUHolW5hPLAnd4HGCpPl968WScategKQ4p",
        "mb8hAHP9mbgCzc9Wc3rSzwtmg95QzhKq2luu3oe57EYxqrS2vpokwS0ul3bHYi+i",
        "H/OonNHYc3o/ak5tGJz/A1UpUJVGh4dahqnrM6Ej1BkuxAVibVAWQ5wSv5HTA5Dq",
        "9SiJtj7zvWmBcVdJaGxGMhJ7U08w3xaHkXoL7fj5IQKBgQD5ZBJOHFSdWPCp0SfU",
        "zczBjMCObY8Q0+9+TWYovjYRYzy3Vfen2ua65p1x4RAglGdGe2naAVwTANvG9Glv",
        "F8kYn3Rv8hyupXFvWZTQmw0YfeZmXd8gETT9Ar2wKwzkw7HPAu2sVUqVTiNDhzA9",
        "nuXDjHhwtg1XEZH2g0Av3b26hoQKBgQDmvDsRJxe9icI8775PEsCwkHwrQ8E9t2Ba",
        "vQLgAQNllMATztgvhQIExwZEYDu1JfHm9ruhvfHvEH2QRufNibL1zyWT+YTjJSYO",
        "4OO1uhm5MkWr8c9wOa5ViQRjP/44EPWyosgawGqeIlWzPYwFkHjOPTFdEV2vuKTV",
        "LahZ4WJ9xQKBgQCEkw0kFu1oQ/qT28sX1ltt3LwUOuud33xmIREYwZ0OezmwoHOp",
        "+LVFUAkMm78uApYwIrUvnh9rPr6WsiFGXFebzlBgnk1fDjYSIoX4qyQ4C92qN2bA",
        "rkUD5ywddZVCG0HvsTfVr/WZD1OxtzEO7wCyy7PhAftbDqy2C0MBQ2yFYQKBgGmc",
        "LHkMaKxjmpljrrrovXPTnlH7QD7saVj+/IrlS9W6ATTPz1noymS/aBnx5kJi7Ncn",
        "hfhhRZSD+sUH/1+vsE8cknmpku6Y+VOEEhYC6XVAEm3CT41xiV8zSOPYzZaCBMPQ",
        "CEFeYy6gTpOtDyMY3oKftbGAml4s6J1+uXjyVa91AoGBAIgAF62Z2gmj1nMDukq4",
        "8KiKGiwu1+pB3kmqwp6pUvnJJ9E4ZNuDKSjRgw/9GBh0MM032qpB9D4WnQiQVmcf",
        "xAxzqcTSAQQdq+aL8D0CyGk1Q8bNPgSfq1cCaYdmq+2aztk39m3RkK1cABQv1nBU",
        "/6m7o+DtMxUh5mdEQFdeABf1",
        "-----END PRIVATE KEY-----"
    ]
    
    # חיבור השורות עם אנטרים נקיים תוך הסרת רווחים סמויים מכל שורה ושורה
    formatted_key = "\n".join([line.strip() for line in key_lines if line.strip()])
    
    info = {
        "type": "service_account",
        "project_id": "sheva-crm",
        "private_key_id": "ddf6cd036121d1f3f1b2342d3a44456d41c41b5b",
        "private_key": formatted_key,
        "client_email": "sheva-manager@sheva-crm.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def load_data():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_url(st.secrets["gsheets_url"]).sheet1
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def save_to_sheet(row_dict):
    try:
        client = get_gsheet_client()
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
        st.error(f"❌ שגיאה טכנית בשמירה: {e}")
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
                with st.spinner("שומר לשיטס..."):
                    if save_to_sheet({'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}):
                        st.session_state.crm_data = load_data()
                        st.success("✅ נשמר!")
                        st.rerun()
