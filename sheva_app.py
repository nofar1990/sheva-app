import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע – ניהול לקוחות חכם", layout="wide")

# --- הגדרות חיבור ---
SHEET_ID = "1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec"

def load_data():
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        df = pd.read_csv(url)
        if not df.empty:
            df = df.dropna(subset=['ת.ז לקוח']) # ניקוי שורות ריקות מהשיטס
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.strip()
        return df if not df.empty else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def get_col(df, options):
    for opt in options:
        if opt in df.columns: return opt
    return None

# --- ממשק המערכת ---
st.title("🛡️ שבע – מערכת ניהול חכמה")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # טעינה ראשונית
        raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # --- התיקון הקריטי: ניקוי יסודי של נתונים ריקים ---
        # 1. מוחקים שורות שבהן אין שם לקוח או אין ת"ז
        df = raw_df.dropna(subset=['ת.ז לקוח', 'שם לקוח'], how='any').copy()
        # 2. מוודאים שת"ז היא טקסט נקי
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        # 3. מוחקים שורות שהת"ז שלהן הפכה ל "nan" או שהיא ריקה
        df = df[df['ת.ז לקוח'] != 'nan']
        df = df[df['ת.ז לקוח'] != '']

        # זיהוי עמודות
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה'])
        c_premium = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_company = get_col(df, ['חברה', 'שם חברה', 'שם יצרן', 'יצרן'])
        c_product = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])

        # --- הפתיח של ג'ימי ---
        st.markdown("### 🤖 הניתוח של ג'ימי")
        
        # חישוב נתונים לסיכום
        total_assets = df[c_assets].sum() if c_assets else 0
        num_clients = df['ת.ז לקוח'].nunique()
        
        col_j1, col_j2 = st.columns([2, 1])
        with col_j1:
            st.info(f"💡 **ג'ימי מעדכן:** סרקתי {num_clients} לקוחות בתיק. סך הנכסים המנוהלים בקובץ זה עומד על ₪{total_assets:,.0f}.")
        with col_j2:
            st.metric("נכסים בטיפול", f"₪{total_assets:,.0f}")

        st.divider()

        # --- רשימת עבודה ---
        st.header("👥 רשימת לקוחות ומוצרים")
        
        # קיבוץ נתונים להצגה ברשימה
        agg_map = {'שם לקוח': 'first', 'טלפון סלולרי': 'first'}
        if c_assets: agg_map[c_assets] = 'sum'
        if c_premium: agg_map[c_premium] = 'sum'
        
        clients_summary = df.groupby('ת.ז לקוח').agg(agg_map).reset_index()
        
        search = st.text_input("🔍 חיפוש לקוח:")
        if search:
            display_df = clients_summary[clients_summary['שם לקוח'].str.contains(search, na=False)]
        else:
            display_df = clients_summary.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            
            # הצלבת נתונים עם השיטס (CRM)
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'] == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                c_i1, c_i2 = st.columns(2)
                with c_i1:
                    st.write(f"**ת.ז:** {cid}")
                    st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                    if c_assets: st.write(f"**סה\"כ צבירה:** ₪{row[c_assets]:,.0f}")
                
                with c_i2:
                    st.write("**פירוט מוצרים:**")
                    cols = [c for c in [c_product, c_company, c_assets] if c]
                    st.dataframe(df[df['ת.ז לקוח'] == cid][cols], hide_index=True)

                st.divider()
                
                # עריכה ושמירה
                e1, e2 = st.columns(2)
                with e1:
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with e2:
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור שינויים", key=f"b_{cid}"):
                    payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                    res = requests.post(SCRIPT_URL, json=payload)
                    if "Success" in res.text:
                        st.session_state.crm_data = load_data()
                        st.success("נשמר!")
                        st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("👋 שלום צוות שבע. העלו קובץ ROETO כדי להתחיל בניהול התיק.")
