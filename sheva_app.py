import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# עיצוב מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { color: #1e2130 !important; font-weight: bold !important; }
    .stMetric { background-color: #ffffff !important; border: 1px solid #c5a059 !important; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e2130 !important; text-align: right; direction: rtl; }
    .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-left: 5px; display: inline-block; margin-bottom: 5px; }
    .bg-birthday { background-color: #fff3cd; color: #856404; }
    .bg-stale { background-color: #f8d7da; color: #721c24; }
    .bg-fee { background-color: #e2e3e5; color: #383d41; }
    .bg-premium { background-color: #f3e5f5; color: #7b1fa2; }
    .bg-upsell { background-color: #d1e7dd; color: #0f5132; }
    .bg-vip { background-color: #cfe2ff; color: #084298; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ שבע – מערכת לקוחות")

# --- חיבור מאובטח לשיטס ---
# כאן התיקון: המערכת משתמשת בחיבור שהגדרנו בסיקרטס תחת connections.gsheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_crm():
    try:
        # קריאת הנתונים מהשיטס שהגדרנו ב-spreadsheet בסיקרטס
        return conn.read(ttl="0s")
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

crm_data = load_crm()

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        today = datetime.now()
        df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
        df['סך חסכון'] = pd.to_numeric(df['סך חסכון'], errors='coerce').fillna(0)
        df['פרמיה חודשית'] = pd.to_numeric(df['פרמיה חודשית'], errors='coerce').fillna(0)
        df['דמנה״ל צבירה'] = pd.to_numeric(df['דמנה״ל צבירה'], errors='coerce').fillna(0)
        for col in ['תאריך לידה', 'תאריך נכונות']:
            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')

        clients = df.groupby('ת.ז לקוח').agg({
            'שם לקוח': 'first', 'טלפון סלולרי': 'first', 'סך חסכון': 'sum', 
            'פרמיה חודשית': 'sum', 'דמנה״ל צבירה': 'max', 'תאריך לידה': 'first', 
            'תאריך נכונות': 'max', 'שם יצרן': lambda x: list(set(x.dropna())),
            'סוג מוצר': lambda x: list(set(x.dropna()))
        }).reset_index()

        def get_alerts(row):
            a = []
            if row['פרמיה חודשית'] > 1000: a.append(('💰 פרמיה > 1,000₪', 'bg-premium'))
            if row['דמנה״ל צבירה'] > 0.5: a.append(('📉 דמי ניהול גבוהים', 'bg-fee'))
            if pd.notnull(row['תאריך לידה']) and row['תאריך לידה'].month == today.month: a.append(('🎂 יום הולדת', 'bg-birthday'))
            if pd.notnull(row['תאריך נכונות']) and (today - row['תאריך נכונות']).days > 365: a.append(('⚠️ תיק רדום', 'bg-stale'))
            if pd.notnull(row['תאריך לידה']):
                age = today.year - row['תאריך לידה'].year
                if 60 <= age <= 67: a.append(('📈 פוטנציאל פרישה', 'bg-upsell'))
            if row['סך חסכון'] > 1000000: a.append(('💎 VIP', 'bg-vip'))
            return a

        clients['alerts'] = clients.apply(get_alerts, axis=1)

        # מדדים
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("סה\"כ לקוחות", len(clients))
        with c2: st.metric("AUM נכסים", f"₪{clients['סך חסכון'].sum():,.0f}")
        with c3: st.metric("הזדמנויות", sum(1 for x in clients['alerts'] if x))
        with c4: st.metric("יצרנים", len(df['שם יצרן'].unique()))

        st.write("---")
        
        search = st.text_input("חיפוש לקוח:")
        display_df = clients[clients['שם לקוח'].str.contains(search, na=False)] if search else clients.head(20)

        for _, row in display_df.iterrows():
            cid = str(row['ת.ז לקוח'])
            # חיפוש הערה קיימת בשיטס
            info = crm_data[crm_data['ת.ז לקוח'].astype(str) == cid]
            s_val = info['סטטוס'].values[0] if not info.empty else "חדש"
            n_val = info['הערות'].values[0] if not info.empty else ""
            a_val = info['נציג'].values[0] if not info.empty else "יונתן תורגמן"

            with st.expander(f"👤 {row['שם לקוח']} | סטטוס: {s_val}"):
                badges = "".join([f'<span class="badge {al[1]}">{al[0]}</span>' for al in row['alerts']])
                st.markdown(badges, unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"📞 **טלפון:** {row['טלפון סלולרי']}")
                    st.write(f"💰 **נכסים:** ₪{row['סך חסכון']:,.0f}")
                with col_b:
                    new_s = st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}", index=["חדש", "בטיפול", "הושלם"].index(s_val))
                    new_a = st.selectbox("סוכן:", ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן", "דניאל כהן", "דורי רז"], key=f"a_{cid}", index=["יונתן תורגמן", "אור בן עזרא", "עומרי כהן", "דניאל כהן", "דורי רז"].index(a_val) if a_val in ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן", "דניאל כהן", "דורי רז"] else 0)
                    new_n = st.text_area("הערות:", value=n_val, key=f"n_{cid}")
                    
                    if st.button("שמור", key=f"b_{cid}"):
                        row_to_save = {'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': new_a, 'הערות': new_n, 'עדכון': datetime.now().strftime("%Y-%m-%d %H:%M")}
                        
                        # שמירה לשיטס
                        df_existing = load_crm()
                        df_existing = df_existing[df_existing['ת.ז לקוח'].astype(str) != cid]
                        df_updated = pd.concat([df_existing, pd.DataFrame([row_to_save])], ignore_index=True)
                        conn.update(data=df_updated)
                        st.toast("נשמר בשיטס!")
                        st.rerun()

    except Exception as e:
        st.error(f"שגיאה: {e}")
