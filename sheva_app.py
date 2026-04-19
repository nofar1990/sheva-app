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
        # טעינה וניקוי
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df = df.dropna(subset=['ת.ז לקוח', 'שם לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()

        # זיהוי עמודות סכומים וגיל
        c_age = get_col(df, ['גיל', 'תאריך לידה'])
        c_prem = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים'])

        # המרה למספרים לטובת חישובים
        df_calc = df.copy()
        df_calc['age_val'] = pd.to_numeric(df_calc[c_age], errors='coerce').fillna(0) if c_age else 0
        df_calc['prem_val'] = pd.to_numeric(df_calc[c_prem], errors='coerce').fillna(0) if c_prem else 0
        df_calc['assets_val'] = pd.to_numeric(df_calc[c_assets], errors='coerce').fillna(0) if c_assets else 0

        # --- הניתוח של ג'ימי - בניית קבוצות עבודה ---
        st.markdown("### 🤖 מרכז הבקרה של ג'ימי")
        
        # 1. פרישה (גיל 55+)
        retire_df = df_calc[df_calc['age_val'] >= 55]
        retire_sum = retire_df['assets_val'].sum()
        
        # 2. פרמיה גבוהה (1500+)
        high_prem_df = df_calc[df_calc['prem_val'] >= 1500]
        high_prem_sum = high_prem_df['prem_val'].sum()

        # 3. מוצר יחיד (חוסר ביטוחים)
        counts = df_calc.groupby('ת.ז לקוח')['שם לקוח'].count()
        single_ids = counts[counts == 1].index.tolist()
        single_df = df_calc[df_calc['ת.ז לקוח'].isin(single_ids)]

        # תצוגת הקטגוריות ככרטיסים לחיצים (Tabs)
        tab_all, tab_retire, tab_prem, tab_single = st.tabs([
            "🔍 כל הלקוחות", 
            f"👨‍ פרישה ({len(retire_df['ת.ז לקוח'].unique())})", 
            f"💰 פרמיה גבוהה ({len(high_prem_df['ת.ז לקוח'].unique())})", 
            f"🛡️ מוצר יחיד ({len(single_ids)})"
        ])

        def render_client_list(filtered_df):
            search = st.text_input("חיפוש בתוך הרשימה:", key=f"search_{filtered_df.index[0] if not filtered_df.empty else 'empty'}")
            
            summary = filtered_df.groupby('ת.ז לקוח').agg({
                'שם לקוח': 'first', 
                'טלפון סלולרי': 'first',
                'assets_val': 'sum',
                'prem_val': 'sum'
            }).reset_index()

            if search:
                summary = summary[summary['שם לקוח'].str.contains(search, na=False)]

            for _, row in summary.head(20).iterrows():
                cid = str(row['ת.ז לקוח'])
                stored = st.session_state.crm_data
                current = stored[stored['ת.ז לקוח'] == cid]
                s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
                n_val = current['הערות'].values[0] if not current.empty else ""

                with st.expander(f"👤 {row['שם לקוח']} | נכסים: ₪{row['assets_val']:,.0f} | סטטוס: {s_val}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**ת.ז:** {cid} | **טלפון:** {row['טלפון סלולרי']}")
                        st.write(f"**סה\"כ פרמיה:** ₪{row['prem_val']:,.0f}")
                    with c2:
                        st.write("**מוצרים:**")
                        st.dataframe(df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all'), hide_index=True)
                    
                    # עדכון CRM
                    e1, e2 = st.columns(2)
                    with e1:
                        new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}_{filtered_df.index[0]}",
                                             index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    with e2:
                        new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}_{filtered_df.index[0]}")
                    
                    if st.button("שמור שינויים", key=f"b_{cid}_{filtered_df.index[0]}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        requests.post(SCRIPT_URL, json=payload)
                        st.session_state.crm_data = load_data()
                        st.rerun()

        with tab_all:
            st.subheader("כל הלקוחות בקובץ")
            render_client_list(df_calc)
        
        with tab_retire:
            st.subheader(f"לקוחות פוטנציאליים לפרישה - סה\"כ נכסים: ₪{retire_sum:,.0f}")
            render_client_list(retire_df)
            
        with tab_prem:
            st.subheader(f"לקוחות עם פרמיה גבוהה (מעל 1500 ₪) - סה\"כ גבייה: ₪{high_prem_sum:,.0f}")
            render_client_list(high_prem_df)
            
        with tab_single:
            st.subheader("לקוחות עם מוצר אחד בלבד (פוטנציאל להגדלת תיק)")
            render_client_list(single_df)

    except Exception as e:
        st.error(f"שגיאה בניתוח: {e}")
else:
    st.info("👋 ברוכים הבאים. העלו קובץ ROETO כדי להפעיל את מרכז הבקרה.")
