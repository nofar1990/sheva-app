import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

# --- הגדרות חיבור סופיות ---
SHEET_ID = "1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA"
# זהו הצינור שקישרנו לגוגל שיטס שלך
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec"

def load_data():
    try:
        # משיכת הנתונים הקיימים מהגיליון לצורך תצוגת הערות קודמות
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        df = pd.read_csv(url)
        # וודוא שתמיד יש את העמודות הדרושות
        if df.empty:
            return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
        return df
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

# --- ממשק המערכת ---
st.title("🛡️ שבע – מערכת לקוחות")

# טעינת נתוני ה-CRM מהגיליון לזיכרון האפליקציה
if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO (קובץ Excel או CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    # קריאת הקובץ שהועלה מהמחשב
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df_roeto = pd.read_excel(uploaded_file)
        else:
            df_roeto = pd.read_csv(uploaded_file)
        
        df_roeto['ת.ז לקוח'] = df_roeto['ת.ז לקוח'].astype(str)
        
        # יצירת רשימת לקוחות ייחודית מהקובץ
        clients = df_roeto.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first', 
            'טלפון סלולרי': 'first'
        }).reset_index()
        
        search = st.text_input("חיפוש לקוח לפי שם:")
        if search:
            display_df = clients[clients['שם לקוח'].str.contains(search, na=False)]
        else:
            display_df = clients.head(20)

        st.subheader(f"מציג {len(display_df)} לקוחות")

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            
            # בדיקה אם יש מידע קודם בגיליון עבור הלקוח הזה
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'].astype(str) == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            # כרטיס לקוח מתקפל
            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**ת.ז:** {cid}")
                    st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                
                with col2:
                    new_s = st.selectbox("עדכן סטטוס:", 
                                         ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], 
                                         key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    
                    new_n = st.text_area("הערות וסיכום:", value=n_val, key=f"n_{cid}")
                    
                    if st.button("שמור שינויים", key=f"b_{cid}"):
                        with st.spinner("שומר בגיליון של שבע..."):
                            payload = {
                                'ת.ז לקוח': cid, 
                                'סטטוס': new_s, 
                                'נציג': "צוות שבע",
                                'הערות': new_n, 
                                'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            try:
                                # שליחת הנתונים לצינור של גוגל
                                response = requests.post(SCRIPT_URL, json=payload)
                                if "Success" in response.text:
                                    st.session_state.crm_data = load_data() # ריענון הזיכרון
                                    st.success(f"השינויים עבור {row['שם לקוח']} נשמרו!")
                                    st.rerun()
                                else:
                                    st.error("השמירה נכשלה. ודאי שה-Deployment מוגדר ל-Anyone.")
                            except Exception as e:
                                st.error(f"שגיאת תקשורת: {e}")
    except Exception as e:
        st.error(f"שגיאה בקריאת הקובץ: {e}")
else:
    st.info("אנא העלי קובץ ROETO כדי להתחיל לעבוד.")
