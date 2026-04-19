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
        return df if not df.empty else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except Exception:
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
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        
        # זיהוי עמודות
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'סכום צבירה'])
        c_premium = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_company = get_col(df, ['חברה', 'שם חברה', 'שם יצרן', 'יצרן'])
        c_product = get_col(df, ['סוג מוצר', 'שם מוצר', 'תוכנית'])

        # --- הצינור של ג'ימי: ניתוח חכם ופתיח ---
        st.markdown(f"### 🤖 ג'ימי מנתח עבורך את הנתונים...")
        
        # זיהוי לקוחות לטיפול דחוף (למשל צבירה מעל 100k שעדיין בסטטוס 'חדש')
        merged_logic = df.groupby('ת.ז לקוח').agg({c_assets: 'sum', 'שם לקוח': 'first'}).reset_index()
        crm_status = st.session_state.crm_data[['ת.ז לקוח', 'סטטוס']]
        logic_df = merged_logic.merge(crm_status, on='ת.ז לקוח', how='left').fillna({'סטטוס': 'חדש'})
        
        urgent_clients = logic_df[(logic_df[c_assets] > 100000) & (logic_df['סטטוס'] == 'חדש')]
        
        col_jimmy1, col_jimmy2 = st.columns([2, 1])
        
        with col_jimmy1:
            st.info(f"💡 **המלצת ג'ימי:** ישנם {len(urgent_clients)} לקוחות עם צבירה גבוהה שטרם נוצר איתם קשר. כדאי להתחיל מהם.")
            if not urgent_clients.empty:
                st.write(f"לקוחות בולטים: {', '.join(urgent_clients['שם לקוח'].head(3).tolist())}")
        
        with col_jimmy2:
            st.metric("נכסים בטיפול", f"₪{df[c_assets].sum():,.0f}")

        st.divider()

        # --- לוח בקרה וקטגוריות ---
        tab1, tab2 = st.tabs(["📋 רשימת עבודה", "📊 ניתוח קטגוריות"])
        
        with tab2:
            st.subheader("פילוח נכסים לפי מוצרים")
            if c_product:
                prod_dist = df.groupby(c_product)[c_assets].sum().sort_values(ascending=False)
                st.bar_chart(prod_dist)
                st.table(prod_dist)

        with tab1:
            # חיפוש וניהול
            search = st.text_input("🔍 חיפוש לקוח (שם או ת.ז):")
            
            # הכנת דאטה ללקוחות
            clients_summary = df.groupby('ת.ז לקוח').agg({
                'שם לקוח': 'first', 
                'טלפון סלולרי': 'first',
                c_assets: 'sum',
                c_premium: 'sum'
            }).reset_index()
            
            if search:
                display_df = clients_summary[clients_summary['שם לקוח'].str.contains(search, na=False)]
            else:
                display_df = clients_summary.head(20)

            for _, row in display_df.iterrows():
                cid = str(row['ת.ז לקוח'])
                stored = st.session_state.crm_data
                current = stored[stored['ת.ז לקוח'].astype(str) == cid]
                
                s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
                n_val = current['הערות'].values[0] if not current.empty else ""

                with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                    # תצוגת נתונים פיננסיים מלאה
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**ת.ז:** {cid}")
                        st.write(f"**טלפון:** {row['טלפון סלולרי']}")
                        st.write(f"**צבירה כוללת:** ₪{row[c_assets]:,.0f}")
                    
                    with col_info2:
                        st.write("**פירוט פוליסות:**")
                        c_prods = df[df['ת.ז לקוח'] == cid][[c_product, c_company, c_assets]].copy()
                        st.dataframe(c_prods, hide_index=True)

                    st.write("---")
                    # עדכון CRM
                    c_edit1, c_edit2 = st.columns(2)
                    with c_edit1:
                        new_s = st.selectbox("סטטוס טיפול:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}",
                                             index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    with c_edit2:
                        new_n = st.text_area("סיכום והערות:", value=n_val, key=f"n_{cid}")
                    
                    if st.button("שמור עדכון", key=f"b_{cid}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        res = requests.post(SCRIPT_URL, json=payload)
                        if "Success" in res.text:
                            st.session_state.crm_data = load_data()
                            st.success("המידע עודכן בגיליון שבע!")
                            st.rerun()

    except Exception as e:
        st.error(f"שגיאה בהצגת הנתונים: {e}")
else:
    st.info("אנא העלי קובץ ROETO כדי שג'ימי יוכל להתחיל בניתוח.")
