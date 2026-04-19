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
        return df if not df.empty else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except:
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
        df = df.dropna(subset=['ת.ז לקוח', 'שם לקוח']).copy()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str).str.replace('.0', '', regex=False).str.strip()

        # זיהוי עמודות חכם
        c_age = get_col(df, ['גיל', 'תאריך לידה', 'שנת לידה'])
        c_prem = get_col(df, ['פרמיה חודשית', 'פרמיה', 'סך פרמיה'])
        c_assets = get_col(df, ['צבירה', 'צבירה כוללת', 'שווי נכסים', 'ערך פדיון'])
        c_prod = get_col(df, ['סוג מוצר', 'שם מוצר', 'ענף'])

        # המרה למספרים לניתוח
        df_calc = df.copy()
        if c_age:
            # ניסיון לחילוץ גיל מתאריך
            df_calc['age_val'] = pd.to_numeric(df_calc[c_age], errors='coerce')
            if df_calc['age_val'].isna().all(): # אם זה תאריך לידה
                 df_calc['age_val'] = pd.to_datetime(df_calc[c_age], errors='coerce').dt.year.apply(lambda x: 2026 - x if x > 0 else 0)
            df_calc['age_val'] = df_calc['age_val'].fillna(0)
        else:
            df_calc['age_val'] = 0

        df_calc['assets_val'] = pd.to_numeric(df_calc[c_assets], errors='coerce').fillna(0) if c_assets else 0
        df_calc['prem_val'] = pd.to_numeric(df_calc[c_prem], errors='coerce').fillna(0) if c_prem else 0

        # --- הניתוח של ג'ימי ---
        st.markdown("### 🤖 מרכז הבקרה של ג'ימי")
        
        # בניית קבוצות
        retire_df = df_calc[df_calc['age_val'] >= 55]
        high_prem_df = df_calc[df_calc['prem_val'] >= 1500]
        
        counts = df_calc.groupby('ת.ז לקוח')['שם לקוח'].count()
        single_ids = counts[counts == 1].index.tolist()
        single_df = df_calc[df_calc['ת.ז לקוח'].isin(single_ids)]

        # Tabs למניעת כפילות וסדר בעבודה
        tabs = st.tabs([
            f"🔍 כל הלקוחות ({len(df_calc['ת.ז לקוח'].unique())})", 
            f"👨‍ פוטנציאל פרישה ({len(retire_df['ת.ז לקוח'].unique())})", 
            f"💰 פרמיה גבוהה ({len(high_prem_df['ת.ז לקוח'].unique())})", 
            f"🛡️ מוצר יחיד ({len(single_ids)})"
        ])

        # פונקציה להצגת כרטיס לקוח
        def render_client_card(cid, row_data, full_df, tab_name):
            stored = st.session_state.crm_data
            current = stored[stored['ת.ז לקוח'] == cid]
            s_val = current['סטטוס'].values[0] if not current.empty else "חדש"
            n_val = current['הערות'].values[0] if not current.empty else ""

            # ניתוח מוצרים
            products = full_df[full_df['ת.ז לקוח'] == cid]
            prod_list = products[c_prod].str.cat(sep=' ') if c_prod else ""
            
            has_pension = any(x in prod_list for x in ['פנסיה', 'תגמולים', 'קצבה'])
            has_health = any(x in prod_list for x in ['בריאות', 'תרופות', 'ניתוחים'])
            has_life = any(x in prod_list for x in ['חיים', 'ריסק', 'מוות'])

            with st.expander(f"👤 {row_data['שם לקוח']} | נכסים: ₪{row_data['assets_val']:,.0f} | {s_val}"):
                col1, col2, col3 = st.columns([1.5, 2, 1.5])
                
                with col1:
                    st.markdown("**📋 נתונים**")
                    st.write(f"ת.ז: {cid}")
                    st.write(f"טלפון: {row_data['טלפון סלולרי']}")
                    st.write(f"גיל: {int(row_data['age_val'])}")
                    st.write(f"פרמיה: ₪{row_data['prem_val']:,.0f}")

                with col2:
                    st.markdown("**🔍 צ'קליסט ג'ימי:**")
                    if row_data['age_val'] >= 55: st.error("⚠️ לבדוק מוכנות לפרישה")
                    if not has_health: st.warning("❌ חסר ביטוח בריאות")
                    if not has_pension: st.warning("❌ אין קרן פנסיה/קצבה")
                    if not has_life: st.warning("❌ לבדוק צורך בביטוח חיים")
                    if row_data['prem_val'] > 1200: st.info("📈 לבדוק כפל ביטוחי")
                    
                with col3:
                    st.markdown("**📝 עדכון**")
                    # שימוש ב-Tab Name במפתח כדי למנוע את שגיאת ה-Duplicate Key
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"], key=f"s_{cid}_{tab_name}",
                                         index=["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"].index(s_val) if s_val in ["חדש", "בטיפול", "הושלם", "לא עונה", "לקוח פוטנציאלי"] else 0)
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}_{tab_name}")
                    if st.button("שמור", key=f"b_{cid}_{tab_name}"):
                        payload = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}
                        requests.post(SCRIPT_URL, json=payload)
                        st.session_state.crm_data = load_data()
                        st.success("נשמר!")
                        st.rerun()
                
                st.write("**פירוט מוצרים:**")
                st.dataframe(products.dropna(axis=1, how='all'), hide_index=True)

        def process_tab(filtered_df, full_df, tab_id):
            summary = filtered_df.groupby('ת.ז לקוח').agg({
                'שם לקוח': 'first', 'טלפון סלולרי': 'first', 'assets_val': 'sum', 'prem_val': 'sum', 'age_val': 'max'
            }).reset_index()
            # סינון חיפוש בתוך הטאב
            search_tab = st.text_input(f"חיפוש לקוח ב-{tab_id}:", key=f"search_{tab_id}")
            if search_tab:
                summary = summary[summary['שם לקוח'].str.contains(search_tab, na=False)]
            
            for _, row in summary.head(25).iterrows():
                render_client_card(str(row['ת.ז לקוח']), row, full_df, tab_id)

        with tabs[0]: process_tab(df_calc, df_calc, "all")
        with tabs[1]: process_tab(retire_df, df_calc, "retire")
        with tabs[2]: process_tab(high_prem_df, df_calc, "premium")
        with tabs[3]: process_tab(single_df, df_calc, "single")

    except Exception as e:
        st.error(f"שגיאה בניתוח: {e}")
else:
    st.info("👋 שלום צוות שבע. העלו קובץ ROETO.")
