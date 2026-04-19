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
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df if not df.empty else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

# פונקציה חכמה לזיהוי עמודות
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
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df = df.dropna(subset=['ת.ז לקוח', 'שם לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()

        # זיהוי עמודות לטובת הניתוח
        c_age = get_col(df, ['גיל', 'תאריך לידה'])
        c_prod = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])
        c_prem = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])

        # --- הניתוח של ג'ימי ---
        st.markdown("### 🤖 הניתוח של ג'ימי - התראות והזדמנויות")
        
        # 1. איתור פוטנציאל לתכנון פרישה (גיל 55+)
        retire_potential = []
        if c_age:
            retire_potential = df[df[c_age] >= 55]['שם לקוח'].unique().tolist()
        
        # 2. איתור פרמיה גבוהה (מעל 1500 ש"ח)
        high_prem = []
        if c_prem:
            df['temp_prem'] = pd.to_numeric(df[c_prem], errors='coerce').fillna(0)
            high_prem = df[df['temp_prem'] >= 1500]['שם לקוח'].unique().tolist()

        # 3. איתור חוסר בביטוחים (לקוחות שיש להם רק מוצר אחד בתיק)
        single_prod = df.groupby('שם לקוח')['ת.ז לקוח'].count()
        single_prod_list = single_prod[single_prod == 1].index.tolist()

        # תצוגת התראות
        col_j1, col_j2, col_j3 = st.columns(3)
        
        with col_j1:
            st.error(f"👨‍קצבה/פרישה ({len(retire_potential)})")
            if retire_potential: st.caption(f"דוגמאות: {', '.join(retire_potential[:3])}...")
            
        with col_j2:
            st.warning(f"💰 פרמיה גבוהה ({len(high_prem)})")
            if high_prem: st.caption(f"דוגמאות: {', '.join(high_prem[:3])}...")

        with col_j3:
            st.info(f"🛡️ חוסר בביטוחים ({len(single_prod_list)})")
            if single_prod_list: st.caption(f"דוגמאות: {', '.join(single_prod_list[:3])}...")

        st.divider()

        # --- רשימת לקוחות ---
        search = st.text_input("🔍 חיפוש לקוח:")
        clients_summary = df.groupby('ת.ז לקוח').agg({'שם לקוח': 'first', 'טלפון סלולרי': 'first'}).reset_index()
        
        display_df = clients_summary[clients_summary['שם לקוח'].str.contains(search, na=False)] if search else clients_summary.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'] == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"**ת.ז:** {cid}")
                    st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                    # תגית מיוחדת אם הלקוח בקטגוריית פרישה
                    if row['שם לקוח'] in retire_potential: st.error("פוטנציאל לתכנון פרישה")
                    if row['שם לקוח'] in high_prem: st.warning("פרמיה גבוהה - לבדוק הוזלה")
                
                with c2:
                    st.write("**פירוט מוצרים מלא:**")
                    st.dataframe(df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all'), hide_index=True)

                st.divider()
                e1, e2 = st.columns(2)
                with e1:
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with e2:
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור עדכון", key=f"b_{cid}"):
                    payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                    requests.post(SCRIPT_URL, json=payload)
                    st.session_state.crm_data = load_data()
                    st.success("נשמר!")
                    st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("👋 ברוכים הבאים. העלו קובץ ROETO להפעלת ג'ימי.")
