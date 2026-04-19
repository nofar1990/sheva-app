import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות ופיננסים", layout="wide")

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

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול לקוחות ונכסים פיננסיים")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # קריאת הנתונים
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        
        # --- חלק 1: לוח בקרה פיננסי (Dashboard) ---
        st.header("📊 תמונת מצב פיננסית")
        
        col_a, col_b, col_c = st.columns(3)
        total_premium = df['פרמיה חודשית'].sum() if 'פרמיה חודשית' in df.columns else 0
        total_assets = df['צבירה'].sum() if 'צבירה' in df.columns else 0
        unique_clients = df['ת.ז לקוח'].nunique()
        
        col_a.metric("סה\"כ לקוחות בקובץ", unique_clients)
        col_b.metric("סה\"כ פרמיה חודשית", f"₪{total_premium:,.0f}")
        col_c.metric("סה\"כ צבירה (נכסים)", f"₪{total_assets:,.0f}")
        
        # פילוח לפי קטגוריות מוצר
        if 'סוג מוצר' in df.columns:
            st.subheader("📁 פילוח לפי מוצרים")
            product_summary = df.groupby('סוג מוצר').agg({
                'ת.ז לקוח': 'count',
                'פרמיה חודשית': 'sum'
            }).rename(columns={'ת.ז לקוח': 'מספר פוליסות', 'פרמיה חודשית': 'פרמיה סה"כ'})
            st.table(product_summary)

        st.divider()

        # --- חלק 2: ניהול ה-CRM ---
        st.header("👥 ניהול לקוחות")
        
        # סיכום לקוחות ייחודיים לטובת הרשימה
        clients = df.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first', 
            'טלפון סלולרי': 'first',
            'פרמיה חודשית': 'sum',
            'צבירה': 'sum'
        }).reset_index()
        
        search = st.text_input("🔍 חיפוש לקוח לפי שם:")
        if search:
            display_df = clients[clients['שם לקוח'].str.contains(search, na=False)]
        else:
            display_df = clients.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'].astype(str) == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    st.write(f"**ת.ז:** {cid}")
                    st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                with c2:
                    st.write(f"**סה\"כ פרמיה:** ₪{row['פרמיה חודשית']:,.0f}")
                    st.write(f"**סה\"כ צבירה:** ₪{row['צבירה']:,.0f}")
                with c3:
                    # משיכת רשימת המוצרים של הלקוח הספציפי
                    client_products = df[df['ת.ז לקוח'] == cid][['סוג מוצר', 'חברה', 'פרמיה חודשית']]
                    st.write("**מוצרים קיימים:**")
                    st.dataframe(client_products, hide_index=True)

                st.divider()
                
                # עדכון סטטוס והערות
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_s = st.selectbox("עדכן סטטוס:", 
                                         ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], 
                                         key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with edit_col2:
                    new_n = st.text_area("סיכום שיחה והערות:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור שינויים ללקוח", key=f"b_{cid}"):
                    with st.spinner("מעדכן את שבע..."):
                        payload = {
                            'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע",
                            'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        response = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in response.text:
                            st.session_state.crm_data = load_data()
                            st.success("✅ נשמר!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בניתוח הקובץ: {e}. וודאי שהעלית קובץ ROETO תקין עם העמודות הדרושות.")
else:
    st.info("👋 ברוכים הבאים. אנא העלו קובץ ROETO כדי לראות את הניתוח הפיננסי ולנהל את הלקוחות.")
