import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import re

# הגדרות מותג שבע
st.set_page_config(page_title="שבע – ניהול תיק לקוחות", layout="wide")

# --- פונקציות ליבה ---
def load_crm():
    try:
        url = f"https://docs.google.com/spreadsheets/d/1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA/export?format=csv&gid=0"
        df = pd.read_csv(url)
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'הערות'])

def clean_money(val):
    """מנקה נתונים כספיים - שומר על דיוק עשרוני ומסיר לכלוך"""
    if pd.isna(val) or val == '': return 0.0
    s = str(val).replace(',', '').replace('₪', '').strip()
    try:
        return float(s)
    except:
        res = re.findall(r"[-+]?\d*\.\d+|\d+", s)
        return float(res[0]) if res else 0.0

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול תיק לקוחות ממוקד")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_crm()

# בחירה בין שני הדוחות המרכזיים
view_mode = st.radio(
    "בחר סוג דוח לטיפול:",
    ["ביטוחי פרט (בריאות, ריסק, מחלות)", "חיסכון ופנסיה (קופות גמל, פנסיה, השתלמות)"],
    horizontal=True
)

uploaded_file = st.file_uploader(f"טעינת קובץ {view_mode}", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # זיהוי עמודות מזהות
        id_col = next((c for c in df.columns if 'ת.ז' in c or 'זהות' in c), df.columns[0])
        name_col = next((c for c in df.columns if 'שם' in c), df.columns[1])
        df[id_col] = df[id_col].astype(str).str.replace('.0', '', regex=False).str.strip()

        # הגדרת עמודת ערך לפי סוג הדוח
        if "חיסכון" in view_mode:
            val_col = st.selectbox("בחר עמודת צבירה/נכסים (למשל: סך חיסכון, ערך פדיון):", df.columns)
            label = "צבירה כוללת"
        else:
            val_col = st.selectbox("בחר עמודת פרמיה (למשל: פרמיה חודשית, סכום הפקדה):", df.columns)
            label = "פרמיה חודשית"

        df['clean_value'] = df[val_col].apply(clean_money)
        
        # חישוב סה"כ נקי ללא כפילויות שורות
        total_val = df.groupby(id_col)['clean_value'].sum().sum()
        
        # תצוגת מדדים עליונה
        c1, c2 = st.columns(2)
        c1.metric(f"סה\"כ {label} בדוח", f"₪{total_val:,.0f}")
        c2.metric("כמות לקוחות ייחודיים", len(df[id_col].unique()))

        st.divider()

        # חיפוש לקוח
        search = st.text_input(f"🔍 חיפוש לקוח בתוך דוח {view_mode}:")
        
        # סיכום לקוחות לתצוגה
        summary = df.groupby(id_col).agg({name_col: 'first', 'clean_value': 'sum'}).reset_index()
        if search:
            summary = summary[summary[name_col].str.contains(search, na=False) | summary[id_col].str.contains(search)]

        st.subheader("📋 רשימת עבודה ממוקדת")
        
        for _, row in summary.head(40).iterrows():
            cid = str(row[id_col])
            crm = st.session_state.crm_data
            # שליפת מידע קיים מה-CRM
            db_row = crm[crm['ת.ז לקוח'] == cid]
            s_val = db_row['סטטוס'].values[0] if not db_row.empty else "חדש"
            n_val = db_row['הערות'].values[0] if not db_row.empty else ""

            with st.expander(f"👤 {row[name_col]} | {label}: ₪{row['clean_value']:,.0f} | {s_val}"):
                col_data, col_crm = st.columns([2, 1])
                
                with col_data:
                    st.write(f"**ת.ז:** {cid}")
                    # הצגת כל הפוליסות של הלקוח מהדוח הנוכחי
                    st.write("**פירוט מוצרים מהקובץ:**")
                    st.dataframe(df[df[id_col] == cid].dropna(axis=1, how='all'), hide_index=True)
                
                with col_crm:
                    st.markdown("**עדכון סטטוס וטיפול:**")
                    new_s = st.selectbox("שינוי סטטוס:", ["חדש", "בטיפול", "בוצע", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}_{view_mode}")
                    new_n = st.text_area("הערות לטיפול:", value=n_val, key=f"n_{cid}_{view_mode}")
                    
                    if st.button("שמור שינויים", key=f"b_{cid}_{view_mode}"):
                        payload = {
                            'ת.ז לקוח': cid,
                            'סטטוס': new_s,
                            'הערות': new_n,
                            'נציג': "צוות שבע",
                            'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        res = requests.post("https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec", json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_crm()
                            st.success("עודכן ב-CRM!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בעיבוד הקובץ: {e}")
else:
    st.info(f"👋 ברוכים הבאים. אנא העלו את קובץ ה-{view_mode} כדי להתחיל בעבודה.")
