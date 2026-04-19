import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע – מערכת ניהול חכמה", layout="wide")

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

# --- ממשק המערכת ---
st.title("🛡️ שבע – מערכת ניהול חכמה")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # קריאת הקובץ כמו פעם - פשוט ונקי
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        
        # ניקוי שורות ריקות בסיסי
        df = df.dropna(subset=['ת.ז לקוח', 'שם לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()

        # --- הפתיח של ג'ימי ---
        st.markdown("### 🤖 ג'ימי מנתח את הנתונים")
        num_clients = df['ת.ז לקוח'].nunique()
        st.info(f"💡 **ג'ימי מעדכן:** סרקתי {num_clients} לקוחות בתיק. המערכת מוכנה לעבודה ולעדכון סטטוסים.")

        st.divider()

        # --- רשימת הלקוחות ---
        search = st.text_input("🔍 חיפוש לקוח לפי שם או ת.ז:")
        
        # איחוד פשוט של הלקוחות (בלי חישובי סכומים מסובכים שגורמים לשגיאות)
        clients_list = df.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first',
            'טלפון סלולרי': 'first'
        }).reset_index()

        if search:
            display_df = clients_list[clients_list['שם לקוח'].str.contains(search, na=False) | clients_list['ת.ז לקוח'].str.contains(search)]
        else:
            display_df = clients_list.head(20)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            
            # בדיקת סטטוס מהשיטס
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'] == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.write(f"**ת.ז:** {cid}")
                    st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                
                with col2:
                    st.write("**מוצרים בתיק:**")
                    # מציג את כל העמודות שיש בקובץ עבור הלקוח הזה - כמו פעם
                    client_data = df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all')
                    st.dataframe(client_data, hide_index=True)

                st.divider()
                
                # שמירה ל-CRM
                e1, e2 = st.columns(2)
                with e1:
                    new_s = st.selectbox("שינוי סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with e2:
                    new_n = st.text_area("הערות לטיפול:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור עדכון", key=f"b_{cid}"):
                    with st.spinner("שומר..."):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        res = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_data()
                            st.success("נשמר בשיטס!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("👋 ברוכים הבאים. העלו קובץ ROETO כדי להתחיל.")
