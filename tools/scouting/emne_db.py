import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time
from datetime import datetime
from data.users import get_users

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"
HIF_BLA = "#0057b7"
GRON_NY = "#ccffcc"
GUL_ADVARSEL = "#ffff99"
ROD_ADVARSEL = "#ffcccc"
AKADEMI_FARVE = "#d1d1ff" # Lys lilla

VINDUE_DATOER = {
    "Nuværende trup": datetime.now(),
    "Sommer 26": datetime(2026, 7, 1),
    "Vinter 26": datetime(2027, 1, 1),
    "Sommer 27": datetime(2027, 7, 1),
    "Vinter 27": datetime(2028, 1, 1)
}

VINDUE_ORDEN = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
POS_OPTS = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]

# --- 2. GITHUB & DATA LOGIK ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except: pass
    return None, None

def save_to_github(df):
    try:
        # Tilføjet ER_AKADEMI til de gemte kolonner
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE','ER_AKADEMI',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE', 'START_11_26_27'
        ]
        _, sha = get_github_file(SCOUT_DB_PATH)
        export_df = df.copy()
        for col in original_cols:
            if col not in export_df.columns: export_df[col] = ""
        csv_content = export_df[original_cols].to_csv(index=False)
        payload = {
            "message": "Auto-update scouting data", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        requests.put(f"https://api.github.com/repos/{REPO}/contents/{SCOUT_DB_PATH}", 
                     headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        st.toast("Databasen er opdateret!", icon="✅")
    except Exception as e:
        st.error(f"Fejl ved automatisk gem: {e}")

def handle_auto_save(key, df_display, source_df):
    state_key = f"editable_{key}"
    if st.session_state.get(state_key) and st.session_state[state_key].get("edited_rows"):
        changes = st.session_state[state_key]["edited_rows"]
        full_db = st.session_state['full_db']
        for idx_str, updated_cols in changes.items():
            wyid = source_df.iloc[int(idx_str)]['PLAYER_WYID']
            matching_rows = full_db[full_db['PLAYER_WYID'] == wyid].sort_values('DATO', ascending=False)
            if not matching_rows.empty:
                idx_in_full = matching_rows.index[0]
                for col, val in updated_cols.items():
                    full_db.at[idx_in_full, col.upper()] = val
        save_to_github(full_db)
        st.session_state[state_key]["edited_rows"] = {}

def clean_pos_val(val):
    if pd.isna(val) or val == "" or str(val).lower() == "nan": return ""
    return str(val).replace('.0', '').strip()

def get_status_color(val, ref_date=None):
    if ref_date is None: ref_date = datetime.now()
    try:
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return None
        days = (dt - ref_date).days
        if days < 0: return "#444444" 
        if days < 183: return ROD_ADVARSEL
        if days <= 365: return GUL_ADVARSEL
        return None
    except: return None

def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    # Tilføjet ER_AKADEMI her
    needed = ['POS_343', 'POS_433', 'POS_352', 'START_11_26_27', 'SKYGGEHOLD', 'ER_EMNE', 'ER_AKADEMI', 'PLAYER_WYID', 'DATO']
    for col in needed:
        if col not in df.columns: df[col] = ""
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values(by='DATO_DT', ascending=False)
    st.session_state['full_db'] = df.copy()
    df_display = df.drop_duplicates(subset=['PLAYER_WYID'], keep='first').copy()
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        df_display[c] = df_display[c].apply(clean_pos_val)
        if c != 'POS':
            df_display[c] = df_display.apply(lambda r: r['POS'] if r[c] == "" else r[c], axis=1)
    if 'KONTRAKT' in df_display.columns:
        df_display['KONTRAKT_DT'] = pd.to_datetime(df_display['KONTRAKT'], dayfirst=True, errors='coerce')
    
    # Tilføjet ER_AKADEMI til mapping logik
    for c in ['ER_EMNE', 'SKYGGEHOLD', 'START_11_26_27', 'ER_AKADEMI']:
        df_display[c] = df_display[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False}).fillna(False)
    
    df_display['IS_HIF'] = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)
    return df_display

# --- 4. UI ---
def vis_side():
    current_user = st.session_state.get("user", "default")
    user_db = get_users()
    user_data = user_db.get(current_user, {})
    res = [r.lower().strip() for r in user_data.get("restricted", [])]

    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, _ = get_github_file(SCOUT_DB_PATH)
    if content is None: return
    df_display = prepare_df(content)

    tabs_to_show = []
    if "emnedatabase" not in res: tabs_to_show.append("Emneliste")
    if "truppen" not in res: tabs_to_show.extend(["Hvidovre IF", "Skyggeliste", "Skyggehold"])

    if not tabs_to_show:
        st.error("Ingen rettigheder.")
        return

    tabs_obj = st.tabs(tabs_to_show)
    tab_map = {name: i for i, name in enumerate(tabs_to_show)}

    cfg = {
        "PLAYER_WYID": None,
        "KONTRAKT_DT": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY"),
        "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_ORDEN),
        "ER_EMNE": st.column_config.CheckboxColumn("Emne"),
        "ER_AKADEMI": st.column_config.CheckboxColumn("Akademi"),
        "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge"),
        "START_11_26_27": st.column_config.CheckboxColumn("Start 11 (26/27)"),
        "POS_343": st.column_config.SelectboxColumn("3-4-3", options=POS_OPTS),
        "POS_433": st.column_config.SelectboxColumn("4-3-3", options=POS_OPTS),
        "POS_352": st.column_config.SelectboxColumn("3-5-2", options=POS_OPTS)
    }

    if "Emneliste" in tab_map:
        with tabs_obj[tab_map["Emneliste"]]:
            source_t1 = df_display[~df_display['IS_HIF']].copy()
            st.data_editor(source_t1[['NAVN', 'KLUB', 'POS', 'KONTRAKT_DT', 'TRANSFER_VINDUE', 'ER_EMNE', 'SKYGGEHOLD', 'PLAYER_WYID']],
                            column_config=cfg, use_container_width=True, height=600, key="editable_t1", on_change=handle_auto_save, args=("t1", df_display, source_t1))

    if "Hvidovre IF" in tab_map:
        with tabs_obj[tab_map["Hvidovre IF"]]:
            source_t2 = df_display[df_display['IS_HIF']].reset_index(drop=True)
            st.data_editor(source_t2[['NAVN', 'KLUB', 'POS', 'KONTRAKT_DT', 'ER_EMNE', 'SKYGGEHOLD', 'ER_AKADEMI', 'PLAYER_WYID']],
                            column_config=cfg, use_container_width=True, height=600, key="editable_t2", on_change=handle_auto_save, args=("t2", df_display, source_t2))

    if "Skyggeliste" in tab_map:
        with tabs_obj[tab_map["Skyggeliste"]]:
            source_t3 = df_display[df_display['SKYGGEHOLD'] == True].reset_index(drop=True)
            st.data_editor(source_t3[['NAVN', 'KLUB', 'POS', 'POS_343', 'POS_433', 'POS_352', 'START_11_26_27', 'PLAYER_WYID']],
                            column_config=cfg, use_container_width=True, height=600, key="editable_t3", on_change=handle_auto_save, args=("t3", df_display, source_t3))

    if "Skyggehold" in tab_map:
        with tabs_obj[tab_map["Skyggehold"]]:
            c_pitch, c_ctrl = st.columns([8.2, 1.8])
            with c_ctrl:
                display_opts = ["Nuværende trup", "Startopstilling (26/27)"] + [k for k in VINDUE_DATOER.keys() if k != "Nuværende trup"]
                sel_v = st.selectbox("Visning", display_opts)
                for form in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(form, use_container_width=True, type="primary" if st.session_state.form_skygge == form else "secondary"):
                        st.session_state.form_skygge = form; st.rerun()

            with c_pitch:
                f_suffix = st.session_state.form_skygge.replace('-', '')
                p_col = f"POS_{f_suffix}"
                is_startopstilling = (sel_v == "Startopstilling (26/27)")
                
                if is_startopstilling:
                    df_f = df_display[df_display['START_11_26_27'] == True].copy()
                    ref_dt = datetime(2026, 7, 1)
                elif sel_v == "Nuværende trup":
                    df_f = df_display[df_display['IS_HIF']].copy()
                    ref_dt = datetime.now()
                else:
                    ref_dt = VINDUE_DATOER.get(sel_v, datetime.now())
                    hif = df_display[df_display['IS_HIF']].copy()
                    emner = df_display[(df_display['SKYGGEHOLD'] == True) & (~df_display['IS_HIF']) & (df_display['TRANSFER_VINDUE'] == sel_v)].copy()
                    hif = hif[~((hif['KONTRAKT_DT'].notna()) & (hif['KONTRAKT_DT'] < ref_dt))]
                    df_f = pd.concat([hif, emner]).drop_duplicates(subset=['PLAYER_WYID'])

                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
                fig, ax = pitch.draw(figsize=(10, 7))
                
                # --- LEGENDS ---
                ax.text(3, 3, " < 6 mdr ", size=6, weight='bold', bbox=dict(facecolor=ROD_ADVARSEL, boxstyle='round,pad=0.5'))
                ax.text(12, 3, " 6-12 mdr ", size=6, weight='bold', bbox=dict(facecolor=GUL_ADVARSEL, boxstyle='round,pad=0.5'))
                ax.text(22, 3, " Transferfri ", size=6, weight='bold', bbox=dict(facecolor=GRON_NY, boxstyle='round,pad=0.5'))
                ax.text(33, 3, " Transferkøb ", size=6, weight='bold', color='white', bbox=dict(facecolor=HIF_BLA, boxstyle='round,pad=0.5'))
                # NY LEGEND: Akademi
                ax.text(45, 3, " Akademi ", size=6, weight='bold', color='black', bbox=dict(facecolor=AKADEMI_FARVE, boxstyle='round,pad=0.5'))
                
                ax.text(118, 3, f"Vindue: {sel_v}", size=8, weight='bold', ha='right', bbox=dict(facecolor='white', edgecolor=HIF_ROD, boxstyle='round,pad=0.5'))

                m = {
                    "3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                    "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                    "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,32,'DM'), "2":(55,70,'HWB'), "8":(55,48,'DM'), "10":(75,40,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}
                }[st.session_state.form_skygge]

                drawn_players = []
                for pid, (px, py, lbl) in m.items():
                    ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', 
                            bbox=dict(facecolor=HIF_ROD, edgecolor='white'))
                    
                    plist = df_f[(df_f[p_col].astype(str) == str(pid)) & (~df_f['PLAYER_WYID'].isin(drawn_players))]
                    if is_startopstilling: 
                        plist = plist.head(1)
                
                    for i, (_, r) in enumerate(plist.iterrows()):
                        drawn_players.append(r['PLAYER_WYID'])
                        
                        # FARVE-LOGIK MED PRIORITET
                        if r['ER_AKADEMI']:
                            # Akademi (Lilla)
                            txt_c, bg = "black", AKADEMI_FARVE
                        elif not r['IS_HIF']:
                            # Emner (Grøn/Blå)
                            if r['KONTRAKT_DT'] <= ref_dt:
                                txt_c, bg = "black", GRON_NY
                            else:
                                txt_c, bg = "white", HIF_BLA
                        else:
                            # HIF (Kontraktstatus)
                            k_c = get_status_color(r['KONTRAKT_DT'], ref_date=ref_dt)
                            txt_c = "black"
                            bg = k_c if k_c else "white"
                
                        y_offset = (i * 3.2) if not is_startopstilling else 0
                        ax.text(px, py + y_offset, r['NAVN'], size=7.5, ha='center', weight='bold', 
                                color=txt_c, bbox=dict(facecolor=bg, edgecolor="black", alpha=0.9))
                st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
