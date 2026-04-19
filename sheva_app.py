import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# הגדרות מותג שבע
st.set_page_config(page_title="שבע – ניהול לקוחות ופיננסים", layout="wide")

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

# פונקציה למציאת עמודה גם אם השם לא מדויק
def find_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# --- ממשק המערכת ---
st.title("🛡️ שבע – ניהול לקוחות ונכסים פיננסיים")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        
        # זיהוי עמודות סכומים באופן גמיש
        col_assets = find_column(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה'])
        col_premium = find_column(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        col_product = find_column(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])
        
        # חישוב לוח בקרה כללי
        st.header("📊 תמונת מצב פיננסית כללית")
        c_a, c_b, c_c = st.columns(3)
        
        assets_val = df[col_assets].sum() if col_assets else 0
        premium_val = df[col_premium].sum() if col_premium else 0
        
        c_a.metric("סה\"כ לקוחות", df['ת.ז לקוח'].nunique())
        c_b.metric("סה\"כ פרמיה חודשית", f"₪{premium_val:,.0f}")
        c_c.metric("סה\"כ צבירה (נכסים)", f"₪{assets_val:,.0f}")
        
        st.divider()

        # --- ניהול לקוחות ---
        st.header("👥 רשימת לקוחות ופירוט מוצרים")
        
        # איחוד נתונים ברמת לקוח
        agg_dict = {'שם לקוח': 'first', 'טלפון סלולרי': 'first'}
        if col_assets: agg_dict[col_assets] = 'sum'
        if col_premium: agg_dict[col_premium] = 'sum'
        
        clients = df.groupby('ת.ז לקוח').agg(agg_dict).reset_index()
        
        search = st.text_input("🔍 חיפוש לקוח לפי שם או ת.ז:")
        if search:
            display_df = clients[(clients['שם לקוח'].str.contains(search, na=False)) | (clients['ת.ז לקוח'].contains(search))]
        else:
            display_df = clients.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'].astype(str) == cid]
            
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | ת.ז {cid} | סטטוס: {s_val}"):
                # סיכום כספי ללקוח
                st.subheader("💰 סיכום נכסים")
                m1, m2, m3 = st.columns(3)
                m1.metric("צבירה כוללת", f"₪{row[col_assets]:,.0f}" if col_assets else "N/A")
                m2.metric("פרמיה חודשית", f"₪{row[col_premium]:,.0f}" if col_premium else "N/A")
                m3.write(f"📞 **טלפון:** {row['טלפון סלולרי']}")
                
                # פירוט מוצרים של הלקוח
                st.write("---")
                st.subheader("📂 פירוט פוליסות ומוצרים")
                client_details = df[df['ת.ז לקוח'] == cid].copy()
                # הצגת עמודות רלוונטיות בלבד
                cols_to_show = [c for c in [col_product, 'חברה', col_assets, col_premium] if c]
                st.dataframe(client_details[cols_to_show], use_container_width=True, hide_index=True)

                st.write("---")
                # עדכון CRM
                st.subheader("📝 עדכון טיפול")
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_s = st.selectbox("שינוי סטטוס:", 
                                         ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], 
                                         key=f"s_{cid}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                with edit_col2:
                    new_n = st.text_area("הערות לטיפול:", value=n_val, key=f"n_{cid}")
                
                if st.button("שמור שינויים", key=f"b_{cid}"):
                    with st.spinner("מעדכן..."):
                        payload = {
                            'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע",
                            'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        try:
                            res = requests.post(SCRIPT_URL, json=payload)
                            if "Success" in res.text:
                                st.session_state.crm_data = load_data()
                                st.success("נשמר בהצלחה!")
                                st.rerun()
                        except:
                            st.error("שגיאת תקשורת בשמירה")

    except Exception as e:
        st.error(f"שגיאה בניתוח הקובץ: {e}. וודאי שהעמודות 'פרמיה' ו'צבירה' קיימות.")
else:
    st.info("אנא העלי קובץ ROETO כדי לראות את הנתונים הפיננסיים ולנהל את הלקוחות.")
