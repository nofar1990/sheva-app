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
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def get_col(df, options):
    for opt in options:
        if opt in df.columns: return opt
    return None

# --- ממשק המערכת ---
st.title("🛡️ שבע – מערכת ניהול וניתוח משולבת")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

# העלאת קבצים
col_up1, col_up2 = st.columns(2)
with col_up1:
    file_roeto = st.file_uploader("1️⃣ טעינת דוח ROETO בסיסי", type=['xlsx', 'csv'])
with col_up2:
    file_extra = st.file_uploader("2️⃣ טעינת דוח תוכניות מפורט (אופציונלי)", type=['xlsx', 'csv'])

if file_roeto:
    try:
        # טעינת דוח 1
        df1 = pd.read_excel(file_roeto) if file_roeto.name.endswith('.xlsx') else pd.read_csv(file_roeto)
        df1 = df1.dropna(subset=['ת.ז לקוח']).copy()
        df1['ת.ז לקוח'] = df1['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()

        # שילוב דוח 2 אם קיים
        if file_extra:
            df2 = pd.read_excel(file_extra) if file_extra.name.endswith('.xlsx') else pd.read_csv(file_extra)
            df2['ת.ז לקוח'] = df2['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()
            # חיבור הנתונים לפי ת"ז
            df = pd.merge(df1, df2, on='ת.ז לקוח', how='left', suffixes=('', '_נוסף'))
            st.success("✅ הנתונים מהדוח הנוסף שולבו בהצלחה!")
        else:
            df = df1

        # זיהוי עמודות (כולל החדשות מהדוח שהעלית)
        c_age = get_col(df, ['גיל', 'תאריך לידה'])
        c_prem = get_col(df, ['פרמיה חודשית', 'סכום הפקדה אחרונה', 'פרמיה'])
        c_assets = get_col(df, ['צבירה', 'סך חיסכון בתוכנית', 'שווי נכסים'])
        c_status = get_col(df, ['סטטוס_נוסף', 'סטטוס פוליסה'])
        c_prod = get_col(df, ['סוג מוצר', 'שם מוצר'])

        # המרה למספרים
        df_calc = df.copy()
        df_calc['age_num'] = pd.to_numeric(df_calc[c_age], errors='coerce').fillna(0) if c_age else 0
        df_calc['assets_num'] = pd.to_numeric(df_calc[c_assets], errors='coerce').fillna(0) if c_assets else 0
        df_calc['prem_num'] = pd.to_numeric(df_calc[c_prem], errors='coerce').fillna(0) if c_prem else 0

        # --- הניתוח של ג'ימי ---
        st.markdown("### 🤖 הניתוח המורחב של ג'ימי")
        
        # זיהוי הזדמנויות חדשות מהדוח החדש
        inactive = df_calc[df_calc[c_status].str.contains('לא פעיל|מוקפא', na=False)] if c_status else pd.DataFrame()
        zero_deposit = df_calc[(df_calc['prem_num'] == 0) & (df_calc['assets_num'] > 10000)]

        j1, j2, j3 = st.columns(3)
        with j1:
            st.error(f"👨‍ פוטנציאל פרישה ({len(df_calc[df_calc['age_num'] >= 55]['ת.ז לקוח'].unique())})")
        with j2:
            st.warning(f"🛑 הופסקו הפקדות ({len(zero_deposit['ת.ז לקוח'].unique())})")
            if not zero_deposit.empty: st.caption("לקוחות עם צבירה ללא הפקדה חודשית")
        with j3:
            st.info(f"📁 תוכניות לא פעילות ({len(inactive['ת.ז לקוח'].unique())})")

        st.divider()

        # --- רשימת לקוחות ---
        search = st.text_input("🔍 חיפוש לקוח:")
        clients_summary = df_calc.groupby('ת.ז לקוח').agg({'שם לקוח': 'first', 'טלפון סלולרי': 'first', 'assets_num': 'sum'}).reset_index()
        
        if search:
            display_df = clients_summary[clients_summary['שם לקוח'].str.contains(search, na=False)]
        else:
            display_df = clients_summary.head(15)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            stored = st.session_state.crm_data
            db_row = stored[stored['ת.ז לקוח'] == cid]
            s_val = db_row['סטטוס'].values[0] if not db_row.empty else "חדש"
            n_val = db_row['הערות'].values[0] if not db_row.empty else ""

            with st.expander(f"👤 {row['שם לקוח']} | נכסים: ₪{row['assets_num']:,.0f} | {s_val}"):
                col1, col2, col3 = st.columns([1.5, 2, 1.5])
                
                with col1:
                    st.markdown("**📋 נתונים משולבים**")
                    st.write(f"ת.ז: {cid}")
                    st.write(f"טלפון: {row['טלפון סלולרי']}")
                    if c_status: st.write(f"סטטוס פוליסות: {df[df['ת.ז לקוח']==cid][c_status].unique()}")

                with col2:
                    st.markdown("**🔍 צ'קליסט ג'ימי:**")
                    # ניתוח משולב
                    if row['assets_num'] > 50000 and s_val == "חדש": st.error("⚠️ לקוח 'כבד' שטרם טופל")
                    if cid in zero_deposit['ת.ז לקוח'].values: st.warning("❗ הפקדות הופסקו - לבדוק ריסק/רצף")
                    
                with col3:
                    st.markdown("**📝 עדכון CRM**")
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה"], key=f"s_{cid}")
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                    if st.button("שמור", key=f"b_{cid}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        requests.post(SCRIPT_URL, json=payload)
                        st.session_state.crm_data = load_data()
                        st.rerun()
                
                st.write("**פירוט תוכניות מורחב (משני הדוחות):**")
                st.dataframe(df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all'), hide_index=True)

    except Exception as e:
        st.error(f"שגיאה בשילוב הדוחות: {e}")
else:
    st.info("👋 אנא העלי את דוח ה-ROETO הבסיסי כדי להתחיל.")
