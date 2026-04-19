import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע – ניהול לקוחות ופיננסים", layout="wide")

# --- הגדרות חיבור סופיות (הצינור שלנו) ---
SHEET_ID = "1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec"

def load_data():
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        df = pd.read_csv(url)
        return df if not df.empty else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

# פונקציה חכמה לזיהוי עמודות לפי רשימת אפשרויות
def get_col(df, options):
    for opt in options:
        if opt in df.columns:
            return opt
    return None

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול לקוחות ונכסים פיננסיים")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # קריאת הקובץ
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        
        # זיהוי עמודות קריטיות (גמיש)
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה', 'ערך פדיון'])
        c_premium = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה', 'פרמיה לחיסכון'])
        c_company = get_col(df, ['חברה', 'שם חברה', 'שם יצרן', 'יצרן', 'גוף מנהל'])
        c_product = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית', 'שם קופה'])

        # --- Dashboard פיננסי ---
        st.header("📊 תמונת מצב פיננסית")
        c1, c2, c3 = st.columns(3)
        total_a = df[c_assets].sum() if c_assets else 0
        total_p = df[c_premium].sum() if c_premium else 0
        
        c1.metric("סה\"כ לקוחות", df['ת.ז לקוח'].nunique())
        c2.metric("סה\"כ פרמיה חודשית", f"₪{total_p:,.0f}")
        c3.metric("סה\"כ צבירה (נכסים)", f"₪{total_a:,.0f}")
        
        st.divider()

        # --- ניהול לקוחות ---
        st.header("👥 ניהול לקוחות ומוצרים")
        
        # בניית רשימת לקוחות מאוחדת
        agg_map = {'שם לקוח': 'first', 'טלפון סלולרי': 'first'}
        if c_assets: agg_map[c_assets] = 'sum'
        if c_premium: agg_map[c_premium] = 'sum'
        
        clients_df = df.groupby('ת.ז לקוח').agg(agg_map).reset_index()
        
        search = st.text_input("🔍 חיפוש לפי שם לקוח:")
        display_df = clients_df[clients_df['שם לקוח'].str.contains(search, na=False)] if search else clients_df.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'].astype(str) == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                # מידע כספי
                m1, m2, m3 = st.columns(3)
                m1.metric("צבירה", f"₪{row[c_assets]:,.0f}" if c_assets else "---")
                m2.metric("פרמיה", f"₪{row[c_premium]:,.0f}" if c_premium else "---")
                m3.write(f"📞 **טלפון:** {row['טלפון סלולרי']}")
                
                # פירוט מוצרים של הלקוח
                st.write("**📂 פירוט מוצרים ופוליסות:**")
                client_prods = df[df['ת.ז לקוח'] == cid].copy()
                cols_to_show = [c for c in [c_product, c_company, c_assets, c_premium] if c]
                st.table(client_prods[cols_to_show])

                st.divider()
                
                # עריכת CRM
                e1, e2 = st.columns(2)
                with e1:
                    new_s = st.selectbox("שינוי סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with e2:
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור שינויים", key=f"b_{cid}"):
                    with st.spinner("מעדכן..."):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        res = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_data()
                            st.success("נשמר!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("אנא העלי קובץ ROETO כדי להתחיל.")
