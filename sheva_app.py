import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

# --- חיבור מאובטח וישיר לגוגל שיטס ---
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # פרטי ה-Service Account בצורה ישירה כדי למנוע שגיאות PEM
    info = {
        "type": "service_account",
        "project_id": "sheva-crm",
        "private_key_id": "ddf6cd036121d1f3f1b2342d3a44456d41c41b5b",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDgx0d6ZMNqpXgL\nWiogMgcSmS7QIuKimUE9LJGBpImMedHQaPqwBJsl2ifHlvV9NXm8z1waI+GF+qUS\n/NwZT7ZwqY4NhfRe1eYiJkaEFoU31wWHWRT6hg1tMP0Kppc+S37OAiNK92NLJig+\nqkIKPnoKXHtboCdJ2Tn0IeVNpAPqDpwGcYbI14Kg0xsUZlRVYT46CxjHF/rAEwcq\nfADoMH4iUJOFHh2KPOL8F9FA4Ljqs/gtzr/oEFu2dZXFmIXYG5IaEn2hyWusQBpT\nOd1R2HT/Wh7iaJAsnuvAj5TYhzlSHdeabc31CkgsEM2iwqQboyEwD3DTEx+Gkxlu\nxDMlr/3lAgMBAAECggEADWMpCWvbbKxevjRYSnMYUz3+2QQe4ebFSS6wmttRGuX9\nfk9mUNnxYJuB34QI6nRnI/zopCDrc2aWcs9PD43dFJAwpvMJtyU/r9x+Ois6M3Vx\nvZorYvFddtmiVIJQAzSNYJklf3dE+WqUHolW5hPLAnd4HGCpPl968WScategKQ4p\nmb8hAHP9mbgCzc9Wc3rSzwtmg95QzhKq2luu3oe57EYxqrS2vpokwS0ul3bHYi+i\nH/OonNHYc3o/ak5tGJz/A1UpUJVGh4dahqnrM6Ej1BkuxAVibVAWQ5wSv5HTA5Dq\n9SiJtj7zvWmBcVdJaGxGMhJ7U08w3xaHkXoL7fj5IQKBgQD5ZBJOHFSdWPCp0SfU\nzczBjMCObY8Q0+9+TWYovjYRYzy3Vfen2ua65p1x4RAglGdGe2naAVwTANvG9Glv\F8kYn3Rv8hyupXFvWZTQmw0YfeZmXd8gETT9Ar2wKwzkw7HPAu2sVUqVTiNDhzA9\nuXDjHhwtg1XEZH2g0Av3b26hoQKBgQDmvDsRJxe9icI8775PEsCwkHwrQ8E9t2Ba\nvQLgAQNllMATztgvhQIExwZEYDu1JfHm9ruhvfHvEH2QRufNibL1zyWT+YTjJSYO\n4OO1uhm5MkWr8c9wOa5ViQRjP/44EPWyosgawGqeIlWzPYwFkHjOPTFdEV2vuKTV\ LahZ4WJ9xQKBgQCEkw0kFu1oQ/qT28sX1ltt3LwUOuud33xmIREYwZ0OezmwoHOp\n+LVFUAkMm78uApYwIrUvnh9rPr6WsiFGXFebzlBgnk1fDjYSIoX4qyQ4C92qN2bA\ rkUD5ywddZVCG0HvsTfVr/WZD1OxtzEO7wCyy7PhAftbDqy2C0MBQ2yFYQKBgGmc\nLHkMaKxjmpljrrrovXPTnlH7QD7saVj+/IrlS9W6ATTPz1noymS/aBnx5kJi7Ncn\nhfhhRZSD+sUH/1+vsE8cknmpku6Y+VOEEhYC6XVAEm3CT41xiV8zSOPYzZaCBMPQ\nCEFeYy6gTpOtDyMY3oKftbGAml4s6J1+uXjyVa91AoGBAIgAF62Z2gmj1nMDukq4\n8KiKGiwu1+pB3kmqwp6pUvnJJ9E4ZNuDKSjRgw/9GBh0MM032qpB9D4WnQiQVmcf\nxAxzqcTSAQQdq+aL8D0CyGk1Q8bNPgSfq1cCaYdmq+2aztk39m3RkK1cABQv1nBU\n/6m7o+DtMxUh5mdEQFdeABf1\n-----END PRIVATE KEY-----\n",
        "client_email": "sheva-manager@sheva-crm.iam.gserviceaccount.com",
        "client_id": "113445430055656668909",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sheva-manager%40sheva-crm.iam.gserviceaccount.com"
    }
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def load_data_from_sheet():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_url(st.secrets["gsheets_url"]).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except Exception as e:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def save_to_sheet(row_dict):
    client = get_gsheet_client()
    sheet = client.open_by_url(st.secrets["gsheets_url"]).sheet1
    
    # משיכת כל הנתונים לעדכון
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # הסרת שורה קיימת של אותו לקוח
    if not df.empty and 'ת.ז לקוח' in df.columns:
        df = df[df['ת.ז לקוח'].astype(str) != str(row_dict['ת.ז לקוח'])]
    
    # הוספת השורה החדשה
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    
    # ניקוי ועדכון השיטס
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- ממשק האתר ---
st.title("🛡️ שבע – מערכת לקוחות")

crm_df = load_data_from_sheet()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
    
    # פילוח לקוחות
    clients = df.groupby('ת.ז לקוח').agg({
        'שם לקוח': 'first', 'טלפון סלולרי': 'first', 'פרמיה חודשית': 'sum'
    }).reset_index()

    search = st.text_input("חיפוש לקוח:")
    display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(15)

    for _, row in display_df.iterrows():
        cid = str(row['ת.ז לקוח'])
        # שליפת הערות מהשיטס
        current_crm = crm_df[crm_df['ת.ז לקוח'].astype(str) == cid]
        s_val = current_crm['סטטוס'].values[0] if not current_crm.empty else "חדש"
        n_val = current_crm['הערות'].values[0] if not current_crm.empty else ""

        with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"📞 טלפון: {row['טלפון סלולרי']}")
                st.write(f"💰 פרמיה: ₪{row['פרמיה חודשית']:,.0f}")
            with col2:
                new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}", index=["חדש", "בטיפול", "הושלם"].index(s_val))
                new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                if st.button("שמור שינויים", key=f"b_{cid}"):
                    save_to_sheet({
                        'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע",
                        'הערות': new_n, 'עדכון': datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success("המידע נשמר בשיטס!")
                    st.rerun()
