import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# הגדרות עיצוב - שבע מערכת לקוחות
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { color: #1e2130 !important; font-weight: bold !important; }
    .stMetric { background-color: #ffffff !important; border: 1px solid #c5a059 !important; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e2130 !important; text-align: right; direction: rtl; }
    div[data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #ddd !important; direction: rtl; }
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

# --- מנוע הזיכרון הזמני (עד שנחבר את גוגל שיטס) ---
if 'db' not in st.session_state:
    st.session_state['db'] = {}

uploaded_file = st.file_uploader("טעינת נתוני ROETO", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        today = datetime.now()
        
        # ניקוי ועיבוד נתונים
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

        # --- מנוע החוקים של שבע ---
        def analyze(row):
            alerts = []
            if row['פרמיה חודשית'] > 1000: alerts.append(('💰 פרמיה > 1,000₪', 'bg-premium'))
            if row['דמנה״ל צבירה'] > 0.5: alerts.append(('📉 דמי ניהול גבוהים', 'bg-fee'))
            if pd.notnull(row['תאריך לידה']) and row['תאריך לידה'].month == today.month: alerts.append(('🎂 יום הולדת', 'bg-birthday'))
            if pd.notnull(row['תאריך נכונות']) and (today - row['תאריך נכונות']).days > 365: alerts.append(('⚠️ תיק רדום', 'bg-stale'))
            if pd.notnull(row['תאריך לידה']):
                age = today.year - row['תאריך לידה'].year
                if 60 <= age <= 67: alerts.append(('📈 פוטנציאל פרישה', 'bg-upsell'))
            if row['סך חסכון'] > 1000000: alerts.append(('💎 VIP', 'bg-vip'))
            return alerts

        clients['alerts'] = clients.apply(analyze, axis=1)

        # מדדים עליונים
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("סה\"כ לקוחות", len(clients))
        with c2: st.metric("נכסים (AUM)", f"₪{clients['סך חסכון'].sum():,.0f}")
        with c3: st.metric("הזדמנויות לטיפול", sum(1 for a in clients['alerts'] if len(a) > 0))
        with c4: st.metric("יצרנים פעילים", len(df['שם יצרן'].unique()))

        # ניתוח יצרנים
        with st.expander("📊 פילוח נכסים לפי חברות (יצרנים)"):
            man_data = df.groupby('שם יצרן')['סך חסכון'].sum().reset_index()
            fig = px.pie(man_data, values='סך חסכון', names='שם יצרן', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")
        
        # סינון מהיר
        filter_type = st.radio("בחרי קטגוריה להצגה:", ["הכל", "הזדמנויות", "ימי הולדת", "פרמיה > 1,000₪", "תיקים רדומים"], horizontal=True)
        
        display_df = clients.copy()
        if filter_type == "הזדמנויות": display_df = display_df[display_df['alerts'].map(len) > 0]
        elif filter_type == "ימי הולדת": display_df = display_df[display_df['alerts'].apply(lambda x: any('יום הולדת' in t[0] for t in x))]
        elif filter_type == "פרמיה > 1,000₪": display_df = display_df[display_df['alerts'].apply(lambda x: any('פרמיה' in t[0] for t in x))]
        elif filter_type == "תיקים רדומים": display_df = display_df[display_df['alerts'].apply(lambda x: any('רדום' in t[0] for t in x))]

        search = st.text_input("חיפוש חופשי:")
        if search: display_df = display_df[display_df['שם לקוח'].str.contains(search, na=False)]

        agent_options = ["יונתן תורגמן", "אור בן עזרא", "עומרי כהן", "דניאל כהן", "דורי רז"]

        for _, row in display_df.head(20).iterrows():
            cid = row['ת.ז לקוח']
            saved = st.session_state['db'].get(cid, {'status': 'חדש', 'agent': 'יונתן תורגמן', 'note': ''})
            badges = "".join([f'<span class="badge {a[1]}">{a[0]}</span>' for a in row['alerts']])
            
            with st.expander(f"👤 {row['שם לקוח']} | פרמיה: ₪{row['פרמיה חודשית']:,.0f}"):
                st.markdown(f"<div>{badges}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.write(f"**📞 טלפון:** {row['טלפון סלולרי']}")
                    st.write(f"**🏢 יצרנים:** {', '.join(row['שם יצרן'])}")
                    st.write(f"**📊 מוצרים:** {', '.join(row['סוג מוצר'])}")
                    
                    phone = str(row['טלפון סלולרי']).replace("-", "").replace(" ", "").split('.')[0]
                    if len(phone) > 5:
                        if phone.startswith('0'): phone = '972' + phone[1:]
                        st.markdown(f'[💬 שלח וואטסאפ](https://wa.me/{phone})')
                
                with col2:
                    st.selectbox("סטטוס:", ["חדש", "בטיפול", "הושלם"], key=f"s_{cid}")
                    st.selectbox("סוכן:", agent_options, index=agent_options.index(saved['agent']), key=f"a_{cid}")
                    st.text_area("הערות:", value=saved['note'], key=f"n_{cid}")
                    if st.button("שמור", key=f"b_{cid}"):
                        st.session_state['db'][cid] = {'status': st.session_state[f"s_{cid}"], 'agent': st.session_state[f"a_{cid}"], 'note': st.session_state[f"n_{cid}"]}
                        st.toast("נשמר!")

    except Exception as e:
        st.error(f"שגיאה: {e}")
