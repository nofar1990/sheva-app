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
        # ניקוי ת"ז ריקות גם בבסיס הנתונים של גוגל
        if not df.empty:
            df = df.dropna(subset=['ת.ז לקוח'])
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
        df_raw = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # --- תיקון השגיאה: ניקוי שורות ריקות (nan) ---
        # אנחנו משאירים רק שורות שיש בהן ת"ז ומנקים רווחים מיותרים
        df = df_raw.dropna(subset=['ת.ז לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.strip()
        
        # זיהוי עמודות
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה'])
        c_premium = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_company = get_col(df, ['חברה', 'שם חברה', 'שם יצרן', 'יצרן'])
        c_product = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])

        # --- הצינור של ג'ימי: ניתוח חכם ופתיח ---
        st.markdown(f"### 🤖 ג'ימי מנתח עבורך את הנתונים...")
        
        # הכנת נתונים ללוגיקה של ג'ימי
        merged_logic = df.groupby('ת.ז לקוח').agg({
            c_assets: 'sum' if c_assets else 'count', 
            'שם לקוח': 'first'
        }).reset_index()
        
        crm_status = st.session_state.crm_data[['ת.ז לקוח', 'סטטוס']].copy()
        crm_status['ת.ז לקוח'] = crm_status['ת.ז לקוח'].astype(str).str.strip()
        
        logic_df = merged_logic.merge(crm_status, on='ת.ז לקוח', how='left').fillna({'סטטוס': 'חדש'})
        
        col_jimmy1, col_jimmy2 = st.columns([2, 1])
        
        with col_jimmy1:
            if c_assets:
                # ג'ימי מוצא לקוחות "מעניינים" לטיפול (צבירה מעל 150k וסטטוס 'חדש')
                urgent = logic_df[(logic_df[c_assets] > 150000) & (logic_df['סטטוס'] == 'חדש')]
                if not urgent.empty:
                    st.info(f"💡 **המלצת ג'ימי:** מצאתי {len(urgent)} לקוחות עם צבירה גבוהה שטרם טופלו. כדאי להתחיל איתם.")
                else:
                    st.success("✅ ג'ימי סרק את התיק: הלקוחות הגדולים כבר בטיפול!")
            else:
                st.warning("ג'ימי לא מצא נתוני צבירה לניתוח מעמיק.")
        
        with col_jimmy2:
            val = df[c_assets].sum() if c_assets else 0
            st.metric("נכסים מנוהלים בקובץ", f"₪{val:,.0f}")

        st.divider()

        # --- לוח עבודה ---
        tab1, tab2 = st.tabs(["📋 רשימת עבודה", "📊 פילוח קטגוריות"])
        
        with tab2:
            if c_product and c_assets:
                st.subheader("התפלגות נכסים לפי סוג מוצר")
                prod_dist = df.groupby(c_product)[c_assets].sum().sort_values(ascending=False)
                st.bar_chart(prod_dist)

        with tab1:
            search = st.text_input("🔍 חיפוש לפי שם או ת.ז:")
            
            # קיבוץ נתונים לפי לקוח לתצוגה ברשימה
            agg_map = {'שם לקוח': 'first', 'טלפון סלולרי': 'first'}
            if c_assets: agg_map[c_assets] = 'sum'
            if c_premium: agg_map[c_premium] = 'sum'
            
            clients_summary = df.groupby('ת.ז לקוח').agg(agg_map).reset_index()
            
            if search:
                display_df = clients_summary[clients_summary['שם לקוח'].str.contains(search, na=False) | clients_summary['ת.ז לקוח'].str.contains(search)]
            else:
                display_df = clients_summary.head(20)

            for _, row in display_df.iterrows():
                cid = str(row['ת.ז לקוח'])
                stored = st.session_state.crm_data
                # ניקוי השוואה למניעת שגיאות nan נוספות
                current = stored[stored['ת.ז לקוח'].astype(str).str.strip() == cid]
                
                s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
                n_val = current['הערות'].values[0] if not current.empty else ""

                with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                    c_i1, c_i2 = st.columns(2)
                    with c_i1:
                        st.write(f"**ת.ז:** {cid}")
                        st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                        if c_assets: st.write(f"**סה\"כ צבירה בתיק:** ₪{row[c_assets]:,.0f}")
                    
                    with c_i2:
                        st.write("**פירוט פוליסות ומוצרים:**")
                        cols = [c for c in [c_product, c_company, c_assets] if c]
                        st.dataframe(df[df['ת.ז לקוח'] == cid][cols], hide_index=True)

                    st.divider()
                    
                    # עריכת ה-CRM
                    e1, e2 = st.columns(2)
                    with e1:
                        new_s = st.selectbox("שינוי סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                             index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    with e2:
                        new_n = st.text_area("הערות לטיפול:", value=n_val, key=f"n_{cid}")
                    
                    if st.button("שמור שינויים", key=f"b_{cid}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        res = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_data()
                            st.success("נשמר בשיטס של שבע!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("👋 שלום צוות שבע. העלו קובץ ROETO כדי שג'ימי יוכל לנתח את הנתונים.")
