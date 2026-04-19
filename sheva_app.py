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
        
        # ניקוי שורות ריקות וערכים חסרים בת"ז (מונע את שגיאת ה-nan)
        df = df_raw.dropna(subset=['ת.ז לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.strip()
        
        # זיהוי עמודות
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה'])
        c_premium = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_company = get_col(df, ['חברה', 'שם חברה', 'שם יצרן', 'יצרן'])
        c_product = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])

        # --- הצינור של ג'ימי: ניתוח חכם ופתיח ---
        st.markdown(f"### 🤖 ג'ימי מנתח עבורך את הנתונים...")
        
        # חישוב לוגיקה לג'ימי (רק על עמודות קיימות)
        merged_logic = df.groupby('ת.ז לקוח').agg({
            c_assets: 'sum' if c_assets else 'count', 
            'שם לקוח': 'first'
        }).reset_index()
        
        crm_status = st.session_state.crm_data[['ת.ז לקוח', 'סטטוס']].copy()
        crm_status['ת.ז לקוח'] = crm_status['ת.ז לקוח'].astype(str).str.strip()
        
        logic_df = merged_logic.merge(crm_status, on='ת.ז לקוח', how='left').fillna({'סטטוס': 'חדש'})
        
        col_jimmy1, col_jimmy2 = st.columns([2, 1])
        
        with col_jimmy1:
            # המלצה חכמה
            if c_assets:
                urgent = logic_df[(logic_df[c_assets] > 150000) & (logic_df['סטטוס'] == 'חדש')]
                if not urgent.empty:
                    st.info(f"💡 **המלצת ג'ימי:** מצאתי {len(urgent)} לקוחות עם צבירה משמעותית שעדיין בסטטוס 'חדש'. כדאי לתת להם עדיפות.")
                else:
                    st.success("✅ ג'ימי בדק: נראה שכל הלקוחות הגדולים כבר בטיפול!")
            else:
                st.warning("ג'ימי לא מצא עמודת 'צבירה' לניתוח עומק.")
        
        with col_jimmy2:
            st.metric("נכסים בטיפול", f"₪{df[c_assets].sum():,.0f}" if c_assets else "0")

        st.divider()

        # --- לוח בקרה וקטגוריות ---
        tab1, tab2 = st.tabs(["📋 רשימת עבודה", "📊 ניתוח קטגוריות"])
        
        with tab2:
            if c_product and c_assets:
                st.subheader("פילוח נכסים לפי מוצרים")
                prod_dist = df.groupby(c_product)[c_assets].sum().sort_values(ascending=False)
                st.bar_chart(prod_dist)
            else:
                st.write("אין מספיק נתונים להצגת גרפים.")

        with tab1:
            search = st.text_input("🔍 חיפוש לקוח (שם או ת.ז):")
            
            # הכנת סיכום ללקוחות
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
                current = stored[stored['ת.ז לקוח'].astype(str).str.strip() == cid]
                
                s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
                n_val = current['הערות'].values[0] if not current.empty else ""

                with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                    c_info1, c_info2 = st.columns(2)
                    with c_info1:
                        st.write(f"**ת.ז:** {cid}")
                        st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                        if c_assets: st.write(f"**צבירה כוללת:** ₪{row[c_assets]:,.0f}")
                    
                    with c_info2:
                        st.write("**פירוט פוליסות:**")
                        show_cols = [c for c in [c_product, c_company, c_assets] if c]
                        st.dataframe(df[df['ת.ז לקוח'] == cid][show_cols], hide_index=True)

                    st.divider()
                    e1, e2 = st.columns(2)
                    with e1:
                        new_s = st.selectbox("סטטוס טיפול:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                             index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    with e2:
                        new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                    
                    if st.button("שמור עדכון", key=f"b_{cid}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        res = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_data()
                            st.success("נשמר!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("👋 ברוכים הבאים למערכת שבע. העלי קובץ ROETO כדי שג'ימי יוכל לנתח את התיק.")
