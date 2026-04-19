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

def load_crm_data():
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        df = pd.read_csv(url)
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def clean_val(val):
    """מנקה מספרים בצורה זהירה - שומר על נקודה עשרונית ומסיר פסיקים"""
    if pd.isna(val) or val == '': return 0.0
    # הסרת פסיקים וסימני מטבע, שמירה על נקודה אחת בלבד
    s = str(val).replace(',', '').replace('₪', '').strip()
    try:
        return float(s)
    except:
        res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
        return float(res[0]) if res else 0.0

# --- ממשק ---
st.title("🛡️ שבע – מערכת ניהול חכמה")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_crm_data()

col_up1, col_up2 = st.columns(2)
with col_up1:
    f1 = st.file_uploader("1️⃣ דוח ROETO בסיסי", type=['xlsx', 'csv'])
with col_up2:
    f2 = st.file_uploader("2️⃣ דוח מפורט (אופציונלי)", type=['xlsx', 'csv'])

if f1:
    try:
        df1 = pd.read_excel(f1) if f1.name.endswith('.xlsx') else pd.read_csv(f1)
        id_col = next((c for c in df1.columns if 'ת.ז' in c or 'זהות' in c), df1.columns[0])
        df1[id_col] = df1[id_col].astype(str).str.replace('.0', '', regex=False).str.strip()

        if f2:
            df2 = pd.read_excel(f2) if f2.name.endswith('.xlsx') else pd.read_csv(f2)
            id_col2 = next((c for c in df2.columns if 'ת.ז' in c or 'זהות' in c), df2.columns[0])
            df2[id_col2] = df2[id_col2].astype(str).str.replace('.0', '', regex=False).str.strip()
            # איחוד דוחות לפי ת"ז
            df = pd.merge(df1, df2, left_on=id_col, right_on=id_col2, how='left', suffixes=('', '_מפורט'))
        else:
            df = df1

        # --- בחירת עמודות בסרגל צדי ---
        st.sidebar.header("⚙️ הגדרת עמודות")
        col_name = st.sidebar.selectbox("שם לקוח:", df.columns, index=df.columns.get_loc(next((c for c in df.columns if 'שם' in c), df.columns[0])))
        col_assets = st.sidebar.selectbox("עמודת נכסים (צבירה):", df.columns, index=0)
        col_age = st.sidebar.selectbox("עמודת גיל/תאריך לידה:", df.columns, index=0)
        
        # עיבוד וניקוי
        df['assets_clean'] = df[col_assets].apply(clean_val)
        df['age_clean'] = df[col_age].apply(clean_val)
        
        # חישוב סה"כ נכסים לכלל המשרד
        total_office_assets = df.drop_duplicates(subset=[id_col, col_assets])['assets_clean'].sum()
        st.metric("סה\"כ נכסים מנוהלים בדוח", f"₪{total_office_assets:,.0f}")

        # --- חיפוש וסינון ---
        search = st.text_input("🔍 חיפוש לקוח לפי שם:")
        
        # קטגוריות
        retire = df[df['age_clean'] >= 55]
        # VIP - לקוחות מעל חצי מיליון
        heavy = df.groupby(id_col).filter(lambda x: x['assets_clean'].sum() >= 500000)

        t1, t2, t3 = st.tabs([
            f"👥 כל הלקוחות ({len(df[id_col].unique())})", 
            f"👴 פרישה ({len(retire[id_col].unique())})", 
            f"💎 VIP ({len(heavy[id_col].unique())})"
        ])

        def show_list(data_df, tag):
            # קיבוץ נכון לפי לקוח כדי למנוע ספירה כפולה
            summary = data_df.groupby(id_col).agg({
                col_name: 'first', 
                'assets_clean': 'sum', 
                'age_clean': 'max'
            }).reset_index()
            
            if search:
                summary = summary[summary[col_name].str.contains(search, na=False)]
            
            for _, row in summary.head(40).iterrows():
                cid = str(row[id_col])
                crm = st.session_state.crm_data
                status = crm[crm['ת.ז לקוח'] == cid]['סטטוס'].values[0] if cid in crm['ת.ז לקוח'].values else "חדש"
                
                with st.expander(f"👤 {row[col_name]} | נכסים: ₪{row['assets_clean']:,.0f} | {status}"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**ת.ז:** {cid} | **גיל:** {int(row['age_clean'])}")
                        # הצגת המוצרים של הלקוח
                        client_prods = df[df[id_col] == cid].dropna(axis=1, how='all')
                        st.dataframe(client_prods, hide_index=True)
                    with c2:
                        new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה"], key=f"s_{cid}_{tag}")
                        new_n = st.text_area("הערות:", key=f"n_{cid}_{tag}")
                        if st.button("עדכן", key=f"b_{cid}_{tag}"):
                            requests.post(SCRIPT_URL, json={'ת.ז לקוח': cid, 'סטטוס': new_s, 'הערות': new_n, 'נציג': "שבע"})
                            st.session_state.crm_data = load_crm_data()
                            st.rerun()

        with t1: show_list(df, "all")
        with t2: show_list(retire, "ret")
        with t3: show_list(heavy, "vip")

    except Exception as e:
        st.error(f"שגיאה בעיבוד הנתונים: {e}")
