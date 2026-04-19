import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

# --- הגדרות חיבור סופיות ---
SHEET_ID = "1-qwKNpPQnFvKrnWXFQIGpBhtmrp1s1zp7nPL0NBqwjA"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwIJiLHWTQp3Yi6FdkSd8fke_HXPClUnnLmeYWFn7eWqoTYOlRvQGHLpQECAfVhgXh66A/exec"

def load_data():
    try:
        # קריאת הנתונים מהגיליון לצורך הצגת הסטטוסים הקיימים
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
        return pd.read_csv(url)
    except Exception:
        # אם הגיליון ריק או לא נגיש, יצירת טבלה ריקה עם העמודות המתאימות
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

# --- ממשק שבע ---
st.title("🛡️ שבע – מערכת לקוחות")

# טעינת נתונים לזיכרון האתר
if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO (קובץ אקסל או CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    # קריאת הקובץ שהועלה (ROETO)
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
    
    # סידור רשימת לקוחות ייחודית
    clients = df.groupby('ת.ז לקוח').agg({'שם לקוח': 'first', 'טלפון סלולרי': 'first'}).reset_index()
    
    search = st.text_input("חיפוש לקוח לפי שם:")
    display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(20)

    for _, row in display_df.iterrows():
        cid = str(row['ת.ז לקוח'])
        
        # משיכת נתונים קיימים מהשיטס עבור הלקוח הספציפי
        stored = st.session_state.crm_data
        current = stored[stored['ת.ז לקוח'].astype(str) == cid]
        
        s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
        n_val = current['הערות'].values[0] if not current.empty else ""

        with st.expander(f"👤 {row['שם לקוח']} | ת.ז: {cid} | סטטוס נוכחי: {s_val}"):
            st.write(f"📞 טלפון: {row['טלפון סלולרי']}")
            
            # שדות לעריכה
            new_s = st.selectbox("עדכון סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], 
                                 key=f"s_{cid}", 
                                 index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
            
            new_n = st.text_area("הוספת הערות/סיכום שיחה:", value=n_val, key=f"n_{cid}")
            
            if st.button("שמור שינויים בגיליון", key=f"b_{cid}"):
                with st.spinner("מעדכן את הגיליון של שבע..."):
                    payload = {
                        'ת.ז לקוח': cid, 
                        'סטטוס': new_s, 
                        'נציג': "צוות שבע",
                        'הערות': new_n, 
                        'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    try:
                        # שליחת הנתונים ל-Web App שיצרנו בגוגל
                        response = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in response.text:
                            # ריענון הנתונים בזיכרון האתר כדי להראות שהתעדכן
                            st.session_state.crm_data = load_data()
                            st.success(f"✅ השינויים עבור {row['שם לקוח']} נשמרו בהצלחה!")
                            st.rerun()
                        else:
                            st.error("השמירה נכשלה. ודאי שהגדרת את ה-Script לגישה לכולם (Anyone).")
                    except Exception as e:
                        st.error(f"שגיאת תקשורת: {e}")
