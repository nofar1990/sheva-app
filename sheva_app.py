import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import re

st.set_page_config(page_title="שבע – ניהול תיק לקוחות", layout="wide")

# --- פונקציות ליבה ---
def load_crm():
    try:
        url = "https://docs.google.com/spreadsheets/d/1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA/export?format=csv&gid=0"
        df = pd.read_csv(url)
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'הערות'])

def clean_money_value(val):
    """מנקה ערכים כספיים ומוודא שלא מדובר בתעודת זהות בטעות"""
    if pd.isna(val) or val == '': return 0.0
    s = str(val).replace(',', '').replace('₪', '').strip()
    # אם המספר ארוך מדי (כמו תעודת זהות) ואין בו נקודה עשרונית, כנראה שזה לא סכום
    if len(s) > 7 and '.' not in s and s.isdigit():
        return 0.0
    try:
        return float(s)
    except:
        res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
        return float(res[0]) if res else 0.0

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול תיק לקוחות ממוקד")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_crm()

view_mode = st.radio(
    "בחר סוג דוח לטיפול:",
    ["ביטוחי פרט (בריאות, ריסק)", "חיסכון ופנסיה (גמל, פנסיה)"],
    horizontal=True
)

uploaded_file = st.file_uploader(f"טעינת קובץ {view_mode}", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # זיהוי עמודות מזהות
        id_col = next((c for c in df.columns if any(x in c for x in ['ת.ז', 'זהות', 'ID'])), df.columns[0])
        name_col = next((c for c in df.columns if 'שם' in c), df.columns[1])
        df[id_col] = df[id_col].astype(str).str.replace('.0', '', regex=False).str.strip()

        # סינון עמודות כספיות רלוונטיות בלבד למניעת בחירת ת"ז בטעות
        money_options = [c for c in df.columns if any(x in c.lower() for x in ['פרמיה', 'צבירה', 'סכום', 'חיסכון', 'ערך'])]
        
        if not money_options: money_options = df.columns.tolist()

        if "חיסכון" in view_mode:
            val_col = st.selectbox("בחר עמודת צבירה/נכסים:", money_options)
            label = "צבירה כוללת"
        else:
            val_col = st.selectbox("בחר עמודת פרמיה חודשית/שנתית:", money_options)
            label = "פרמיה"

        df['clean_value'] = df[val_col].apply(clean_money_value)
        
        # סיכום לקוח - מונע ספירה כפולה של אותה ת"ז אם היא מופיעה כמה פעם עם אותו סכום
        summary = df.groupby(id_col).agg({name_col: 'first', 'clean_value': 'sum'}).reset_index()
        
        total_val = summary['clean_value'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric(f"סה\"כ {label} בדוח", f"₪{total_val:,.0f}")
        c2.metric("כמות לקוחות", len(summary))

        st.divider()
        search = st.text_input("🔍 חיפוש לפי שם או ת.ז:")
        if search:
            summary = summary[summary[name_col].str.contains(search, na=False) | summary[id_col].str.contains(search)]

        for _, row in summary.head(40).iterrows():
            cid = str(row[id_col])
            crm = st.session_state.crm_data
            db_row = crm[crm['ת.ז לקוח'] == cid]
            s_val = db_row['סטטוס'].values[0] if not db_row.empty else "חדש"
            
            with st.expander(f"👤 {row[name_col]} | {label}: ₪{row['clean_value']:,.0f} | {s_val}"):
                col_data, col_crm = st.columns([2, 1])
                with col_data:
                    st.write(f"**ת.ז:** {cid}")
                    st.dataframe(df[df[id_col] == cid].dropna(axis=1, how='all'), hide_index=True)
                with col_crm:
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "בוצע", "לא עונה"], key=f"s_{cid}")
                    if st.button("שמור", key=f"b_{cid}"):
                        requests.post("https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec", 
                                      json={'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "שבע"})
                        st.rerun()

    except Exception as e:
        st.error(f"שגיאה: {e}")
