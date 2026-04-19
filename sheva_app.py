import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import re

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
        return df
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def clean_numeric(series):
    """מנקה פסיקים, סימני שקל ורווחים והופך למספר"""
    return pd.to_numeric(series.astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

def get_col(df, options):
    for opt in options:
        if opt in df.columns: return opt
    return None

def normalize_id(df, col_name):
    if col_name:
        df[col_name] = df[col_name].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    return df

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול וניתוח משולב")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

col_up1, col_up2 = st.columns(2)
with col_up1:
    file_roeto = st.file_uploader("1️⃣ טעינת דוח ROETO בסיסי", type=['xlsx', 'csv'])
with col_up2:
    file_extra = st.file_uploader("2️⃣ טעינת דוח תוכניות מפורט", type=['xlsx', 'csv'])

if file_roeto:
    try:
        df1 = pd.read_excel(file_roeto) if file_roeto.name.endswith('.xlsx') else pd.read_csv(file_roeto)
        id_col1 = get_col(df1, ['ת.ז לקוח', 'ת.ז', 'מספר זהות', 'מספר ת.ז', 'ID'])
        df1 = normalize_id(df1, id_col1).rename(columns={id_col1: 'ת.ז לקוח'})

        if file_extra:
            df2 = pd.read_excel(file_extra) if file_extra.name.endswith('.xlsx') else pd.read_csv(file_extra)
            id_col2 = get_col(df2, ['ת.ז לקוח', 'ת.ז', 'מספר זהות', 'מספר ת.ז', 'ID'])
            df2 = normalize_id(df2, id_col2).rename(columns={id_col2: 'ת.ז לקוח'})
            df = pd.merge(df1, df2, on='ת.ז לקוח', how='left', suffixes=('', '_מפורט'))
            st.success("✅ הנתונים שולבו!")
        else:
            df = df1

        # זיהוי עמודות
        c_age = get_col(df, ['גיל', 'תאריך לידה', 'שנת לידה'])
        c_prem = get_col(df, ['סכום הפקדה אחרונה', 'פרמיה חודשית', 'פרמיה'])
        c_assets = get_col(df, ['סך חיסכון בתוכנית', 'צבירה', 'שווי נכסים', 'ערך פדיון'])
        
        # ניקוי מספרים (חשוב מאוד!)
        df_calc = df.copy()
        df_calc['assets_num'] = clean_numeric(df_calc[c_assets]) if c_assets else 0
        df_calc['prem_num'] = clean_numeric(df_calc[c_prem]) if c_prem else 0
        
        # חישוב גיל
        if c_age:
            if df_calc[c_age].dtype == 'object' and any(df_calc[c_age].astype(str).str.contains('/')):
                df_calc['age_num'] = pd.to_datetime(df_calc[c_age], errors='coerce').dt.year.apply(lambda x: 2026 - x if x > 0 else 0)
            else:
                df_calc['age_num'] = clean_numeric(df_calc[c_age])
        else:
            df_calc['age_num'] = 0

        # קבוצות עבודה
        retire_df = df_calc[df_calc['age_num'] >= 55]
        zero_deposit = df_calc[(df_calc['prem_num'] == 0) & (df_calc['assets_num'] > 1000)]
        
        st.markdown("### 🤖 מרכז הבקרה של ג'ימי")
        tabs = st.tabs([
            f"🔍 כל הלקוחות ({len(df_calc['ת.ז לקוח'].unique())})", 
            f"👨‍ פרישה ({len(retire_df['ת.ז לקוח'].unique())})", 
            f"🛑 הפסקת הפקדה ({len(zero_deposit['ת.ז לקוח'].unique())})"
        ])

        def render_list(filtered_df, tab_id):
            if filtered_df.empty:
                st.info("לא נמצאו לקוחות בקטגוריה זו.")
                return

            summary = filtered_df.groupby('ת.ז לקוח').agg({
                'שם לקוח': 'first', 'assets_num': 'sum', 'prem_num': 'sum', 'age_num': 'max'
            }).reset_index()

            for _, row in summary.head(25).iterrows():
                cid = str(row['ת.ז לקוח'])
                stored = st.session_state.crm_data
                db_row = stored[stored['ת.ז לקוח'] == cid]
                s_val = db_row['סטטוס'].values[0] if not db_row.empty else "חדש"
                
                with st.expander(f"👤 {row['שם לקוח']} | נכסים: ₪{row['assets_num']:,.0f} | {s_val}"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    with c1:
                        st.write(f"**ת.ז:** {cid}")
                        st.write(f"**גיל:** {int(row['age_num'])}")
                    with c2:
                        st.write(f"**נכסים:** ₪{row['assets_num']:,.0f}")
                        st.write(f"**הפקדה:** ₪{row['prem_num']:,.0f}")
                    with c3:
                        new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה"], key=f"s_{cid}_{tab_id}")
                        if st.button("שמור", key=f"b_{cid}_{tab_id}"):
                            requests.post(SCRIPT_URL, json={'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")})
                            st.rerun()
                    
                    st.dataframe(df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all'), hide_index=True)

        with tabs[0]: render_list(df_calc, "all")
        with tabs[1]: render_list(retire_df, "retire")
        with tabs[2]: render_list(zero_deposit, "zero")

    except Exception as e:
        st.error(f"שגיאה: {e}")
