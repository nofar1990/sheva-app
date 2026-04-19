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

def normalize_id(df, col_name):
    """מנקה תעודות זהות מרווחים, נקודות ואפסים מיותרים"""
    if col_name:
        df[col_name] = df[col_name].astype(str).str.replace('.0', '', regex=False).str.strip()
        return df
    return df

# --- ממשק המערכת ---
st.title("🛡️ שבע – מערכת ניהול וניתוח משולבת")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data()

# העלאת קבצים
col_up1, col_up2 = st.columns(2)
with col_up1:
    file_roeto = st.file_uploader("1️⃣ טעינת דוח ROETO בסיסי", type=['xlsx', 'csv'])
with col_up2:
    file_extra = st.file_uploader("2️⃣ טעינת דוח תוכניות מפורט", type=['xlsx', 'csv'])

if file_roeto:
    try:
        # טעינת דוח 1
        df1 = pd.read_excel(file_roeto) if file_roeto.name.endswith('.xlsx') else pd.read_csv(file_roeto)
        id_col1 = get_col(df1, ['ת.ז לקוח', 'ת.ז', 'מספר זהות', 'מספר ת.ז', 'ID'])
        df1 = normalize_id(df1, id_col1)
        # וודאי ששם העמודה אחיד לצורך ה-Merge
        df1 = df1.rename(columns={id_col1: 'ת.ז לקוח'})

        # שילוב דוח 2 אם קיים
        if file_extra:
            df2 = pd.read_excel(file_extra) if file_extra.name.endswith('.xlsx') else pd.read_csv(file_extra)
            id_col2 = get_col(df2, ['ת.ז לקוח', 'ת.ז', 'מספר זהות', 'מספר ת.ז', 'ID'])
            df2 = normalize_id(df2, id_col2)
            df2 = df2.rename(columns={id_col2: 'ת.ז לקוח'})
            
            # חיבור הנתונים - מוריד כפילויות של עמודות זהות
            df = pd.merge(df1, df2, on='ת.ז לקוח', how='left', suffixes=('', '_מפורט'))
            st.success("✅ הנתונים שולבו בהצלחה לפי תעודות זהות!")
        else:
            df = df1

        # זיהוי עמודות חכם לניתוח
        c_age = get_col(df, ['גיל', 'תאריך לידה', 'שנת לידה'])
        c_prem = get_col(df, ['סכום הפקדה אחרונה', 'פרמיה חודשית', 'פרמיה'])
        c_assets = get_col(df, ['סך חיסכון בתוכנית', 'צבירה', 'שווי נכסים'])
        c_status = get_col(df, ['סטטוס_מפורט', 'סטטוס', 'מצב פוליסה'])

        # המרה למספרים
        df_calc = df.copy()
        df_calc['age_num'] = pd.to_numeric(df_calc[c_age], errors='coerce').fillna(0) if c_age else 0
        df_calc['assets_num'] = pd.to_numeric(df_calc[c_assets], errors='coerce').fillna(0) if c_assets else 0
        df_calc['prem_num'] = pd.to_numeric(df_calc[c_prem], errors='coerce').fillna(0) if c_prem else 0

        # --- הניתוח של ג'ימי ---
        st.markdown("### 🤖 הניתוח המורחב של ג'ימי")
        
        # בניית קבוצות
        retire_df = df_calc[df_calc['age_num'] >= 55]
        zero_deposit = df_calc[(df_calc['prem_num'] == 0) & (df_calc['assets_num'] > 10000)]
        
        tabs = st.tabs([
            f"🔍 כל הלקוחות ({len(df_calc['ת.ז לקוח'].unique())})", 
            f"👨‍ פרישה ({len(retire_df['ת.ז לקוח'].unique())})", 
            f"🛑 הפסקת הפקדה ({len(zero_deposit['ת.ז לקוח'].unique())})"
        ])

        def render_client_list(filtered_df, tab_id):
            summary = filtered_df.groupby('ת.ז לקוח').agg({
                'שם לקוח': 'first', 'assets_num': 'sum', 'prem_num': 'sum', 'age_num': 'max'
            }).reset_index()
            
            for _, row in summary.head(20).iterrows():
                cid = str(row['ת.ז לקוח'])
                stored = st.session_state.crm_data
                db_row = stored[stored['ת.ז לקוח'] == cid]
                s_val = db_row['סטטוס'].values[0] if not db_row.empty else "חדש"
                n_val = db_row['הערות'].values[0] if not db_row.empty else ""

                with st.expander(f"👤 {row['שם לקוח']} | נכסים: ₪{row['assets_num']:,.0f} | {s_val}"):
                    c1, c2, c3 = st.columns([1.5, 2, 1.5])
                    with c1:
                        st.write(f"**ת.ז:** {cid}")
                        st.write(f"**גיל:** {int(row['age_num'])}")
                        st.write(f"**הפקדה:** ₪{row['prem_num']:,.0f}")
                    with c2:
                        st.markdown("**🔍 צ'קליסט:**")
                        if row['age_num'] >= 55: st.error("⚠️ לתכנון פרישה")
                        if row['prem_num'] == 0 and row['assets_num'] > 0: st.warning("❗ הפקדות הופסקו")
                    with c3:
                        new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה"], key=f"s_{cid}_{tab_id}")
                        new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}_{tab_id}")
                        if st.button("שמור", key=f"b_{cid}_{tab_id}"):
                            payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                            requests.post(SCRIPT_URL, json=payload)
                            st.session_state.crm_data = load_data()
                            st.rerun()
                    
                    st.write("**פירוט תוכניות מלא:**")
                    st.dataframe(df[df['ת.ז לקוח'] == cid].dropna(axis=1, how='all'), hide_index=True)

        with tabs[0]: render_client_list(df_calc, "all")
        with tabs[1]: render_client_list(retire_df, "retire")
        with tabs[2]: render_client_list(zero_deposit, "zero")

    except Exception as e:
        st.error(f"שגיאה בניתוח: {e}")
else:
    st.info("👋 אנא העלי את דוח ה-ROETO הבסיסי.")
