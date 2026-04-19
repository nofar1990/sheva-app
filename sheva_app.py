import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

st.title("🛡️ שבע – מערכת לקוחות")

# חיבור מאובטח לשיטס (מושך את הכל מה-Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(ttl="0s")
    except Exception as e:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

# שמירת המידע בסטייט
if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
    clients = df.groupby('ת.ז לקוח').agg({'שם לקוח': 'first', 'טלפון סלולרי': 'first'}).reset_index()

    search = st.text_input("חיפוש לקוח:")
    display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(10)

    for _, row in display_df.iterrows():
        cid = str(row['ת.ז לקוח'])
        stored = st.session_state.crm_data
        current = stored[stored['ת.ז לקוח'].astype(str) == cid]
        s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
        n_val = current['הערות'].values[0] if not current.empty else ""

        with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
            new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}", index=["חדש", "בטיפול", "הושלם"].index(s_val))
            new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
            
            if st.button("שמור שינויים", key=f"b_{cid}"):
                with st.spinner("שומר..."):
                    # הכנת השורה החדשה
                    new_row = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                    
                    # עדכון הדאטה פריים
                    df_existing = load_data()
                    df_existing = df_existing[df_existing['ת.ז לקוח'].astype(str) != cid]
                    updated_df = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # כתיבה לשיטס
                    conn.update(data=updated_df)
                    st.session_state.crm_data = updated_df
                    st.success("✅ נשמר בהצלחה!")
                    st.rerun()
