import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import base64

# הגדרות מותג שבע
st.set_page_config(page_title="שבע - מערכת לקוחות", layout="wide")

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # המפתח מקודד ב-Base64 כדי למנוע שגיאות PEM של רווחים ואנטרים
    encoded_key = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JSUV2Z0lCQURBTkJna3Foa2lHOXcwQkFRRUZBQVNDQktnd2dnU2tBZ0VBQW9JQkFRRGd4MGQ2Wk1OcXBYZ0wKV2lvZ01nY1NtUzdRSXVLaW1VRTlMSkdCcEltTWVkSFFhUHF3QkpzbDJpZkhsdlY5TlltOHoxd2FJK0dGK3FVUwpL053WlQ3WndxWTROaGZSZTFlWWlKa2VFRm9VMzF3V0hXUlQ2aGcxdE1QMEtwcGMrUzM3T0FpTks5Mk5MSmlnKwpxa0lLUG5vS1hIdGJvQ2RKMlRuMEllVk5wQVBxRHB3R2NZYkkxNEtnMHhzVVpsUlZZVDQ2Q3hqSEYvckFFd2NxCmZBRG9NSDRpVUpPRkhoMktQT0w4RjlGQTRMunFzL2d0enIv b0V1MmRaWEZtSVhZRzVJYUVuMmh5V3VzUUJwVApPZDBSMkhUL1doN2lhSkFzbnV2QWo1VFlIemxTSGRlYWJjMzFDa2dzRU0yaXdxQm95RXdEM0RUUXgrRmt4bHUKeERNbHIvM2xBZ01CQUFFQ2dnRUFEV01wQ1d2YmJLeGV2alJZU25NWVV6MysyUVFlNGViRlNTNndtdHRSR3VYOQpmazltVU5ueFlKdUIzNFFJNm5Sbkkvem9wQ0RyYzJhV2NzOVBENDNkRkpBd3B2TUp0eVUvUjl4K09pczZNM1Z4CnZab3JZVkZkZHRtaVZJSlFBekNOWUprbGYzZEUrV3FVSG9sVzVoUExBbmQ0SEdDcFBsOTY4V1NjYXRlZ0tRNXAKbWI4aEFIUDltYmdDemM5V2MzclN6d3RtZzk1UXpLcnEybHV1M29lNTdFWXhxclMydnBva3dTMFVsM2JIWWkqaQpIL09vbm5IWWMzby9hazV0R0p6L0ExVXBVSlZHaDRkYWhxbnJNNkVqMUJrdXhBVmliVkFXUTV3U3Y1SVRBNURxCjlTaUp0ajd6dldtQmNWRGZKYUd4R01KSjdVMDh3M3hhSmtYb0w3Zmo1SVFLQmdRRDVaQkpPS EZTZFdQQ3AwU2ZVCnpjelNqTUNPYlk4UTArOStUV1lvdmpZUlloeTNWZmVuMnVhNjVwMXg0UkFnbEdkR2UybmFBVndUQU52RzlHbHYKRjhrWW4zUnY4aHl1cFhGdldaVFFtdzBZZmVabVhkOGdFVFQ5QXIyd0t3emt3N0hQQXUycy9WUnFWVGlORDh6QTkKdVhEakhId3RnMlhFWkgyZzBBdjNiMjZob1FLQmdRbm1Ec1JKeGU5aWNJODc3NVBFc0N3a0h3clE4RTl0MkJhCnZRTGdBUU5sbE1BUnp0Z3ZocUlFeHdaRVlEdTFKZkhtOXJ1aHZIdkVIMlFSdWZObWJMMTF6eVdUK1lUakpTWU8KNE9PMXVobTVNa1dyOGM5d09hNVZpUVJqUC80NEVQV3lvc2dhdzdxZUlMV3pQWXdGa0hqT1RGZEVWMnZ1S1RWQkxhaFo0V0o5eFFLQmdRQ0VrdzBrRnUxb1EvcVQyOHNIMWx0dDNMd1VPdWRkMzN4bUlSRVl3WjBPZXptd29IT3AKK0xWRlVBa01tNzh1QXBZd0lyVXZuaDlyUHI2V3NpRkdYRmViemxCZ25rMWZEallTSW9YNHF5UTRDOXJxTjJiQQpyay9VNDV5ZGRaVkNHMEh2c1RmVnIvV1pEMU94dHpFTzd3Q3l5N1BoQWZ0YlFxeTJDME1CUTF5RllRS0JnR21jCkxoa01hS3hqbXBsanJycm92WFBUbmxIN1FEN3NhVmp2L0lybFM5VzZBVFRQejFub3ltUy9hQm54NWtKaTdOY24KaGZoaFJaU0QrU1VILzErdnNFOY2tuZXBrdTZZK1ZPRUVoWUM2WFZBRW0zQ1Q0MXhpVjh6U09QWXpaYkNCTVBQCkNFRmVZejZnVHBvdER5TVkzb0tmdGJBQW1sNHM2SjErdVhqeVZhOTFBb0dCQUlnQUY2MloyZ21qMW5NRHVia3E0CjhLaUdpd3UxK3BCM2ttcXdwNnBVdm5KSTlFNEpOdURLU2pSZ3cvOUdCaDBNTTBTMnFwQjlENFdOUWlRVm1jZgp4QXh6cWNUU0FRUWRxK2FMOEQwQ3lHazFROGJOUGdTZnExY0NhWWRtcSsyYXp0azM5bTNSa0sxY0FCUXYxbkJVCi82bTdvK0R0TXhVaDVtZEVRRmRlQUJmMQotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg=="
    
    decoded_key_bytes = base64.b64decode(encoded_key)
    private_key = decoded_key_bytes.decode("utf-8")

    info = {
        "type": "service_account",
        "project_id": "sheva-crm",
        "private_key_id": "ddf6cd036121d1f3f1b2342d3a44456d41c41b5b",
        "private_key": private_key,
        "client_email": "sheva-manager@sheva-crm.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def load_data_from_sheet():
    try:
        client = get_gsheet_client()
        workbook = client.open_by_url(st.secrets["gsheets_url"])
        sheet = workbook.get_worksheet(0)
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])
    except Exception:
        return pd.DataFrame(columns=['ת.ז לקוח', 'סטטוס', 'נציג', 'הערות', 'עדכון'])

def save_to_sheet(row_dict):
    try:
        client = get_gsheet_client()
        workbook = client.open_by_url(st.secrets["gsheets_url"])
        sheet = workbook.get_worksheet(0)
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        row_dict = {k: str(v) for k, v in row_dict.items()}
        if not df.empty:
            df['ת.ז לקוח'] = df['ת.ז לקוח'].astype(str)
            df = df[df['ת.ז לקוח'] != row_dict['ת.ז לקוח']]
        df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ שגיאה טכנית: {e}")
        return False

st.title("🛡️ שבע – מערכת לקוחות")

if 'crm_data' not in st.session_state:
    st.session_state.crm_data = load_data_from_sheet()

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
                    if save_to_sheet({'ת.ז לקוח': cid, 'סטטוס': new_s, 'נציג': "צוות שבע", 'הערות': new_n, 'עדכון': datetime.now().strftime("%d/%m/%Y %H:%M")}):
                        st.session_state.crm_data = load_data_from_sheet()
                        st.success("✅ נשמר!")
                        st.rerun()
