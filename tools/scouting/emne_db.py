import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time
from datetime import datetime

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"
HIF_BLA = "#0057b7"
GRON_NY = "#ccffcc"
GUL_ADVARSEL = "#ffff99"
ROD_ADVARSEL = "#ffcccc"

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
        # Præcis rækkefølge som i din CSV
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE', 'START_11_26_27'
        ]
        _, sha = get_github_file(SCOUT_DB_PATH)
        
        export_df = df.copy()
        
        # Sørg for at alle kolonner eksisterer inden gem
        for col in original_cols:
            if col not in export_df.columns:
                export_df[col] = ""
            
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
                    # Vi mapper altid tilbage til STORE bogstaver for databasen
                    db_col = col.upper()
                    full_db.at[idx_in_full, db_col] = val
        
        save_to_github(full_db)
        st.session_state[state_key]["edited_rows"] = {}

# --- 3. DATA PROCESSING ---
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
    
    # TVING ALLE KOLONNER TIL STORE BOGSTAVER VED INDLÆSNING
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Sikkerheds-oprettelse af manglende kolonner
    needed = ['POS_343', 'POS_433', 'POS_352', 'START_11_26_27', 'SKYGGEHOLD', 'ER_EMNE', 'PLAYER_WYID', 'DATO']
    for col in needed:
        if col not in df.columns: df[col] = ""

    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values(by='DATO_DT', ascending=False)
    
    st.session_state['full_db'] = df.copy()
    
    # Unik visning pr spiller
    df_display = df.drop_duplicates(subset=['PLAYER_WYID'], keep='first').copy()

    # Rens positioner
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        df_display[c] = df_display[c].apply(clean_pos_val)
        if c != 'POS': # Hvis system-position er tom, brug standard POS
            df_display[c] = df_display.apply(lambda r: r['POS'] if r[c] == "" else r[c], axis=1)

    if 'KONTRAKT' in df_display.columns:
        df_display['KONTRAKT_DT'] = pd.to_datetime(df_display['KONTRAKT'], dayfirst=True, errors='coerce')

    # Konverter boolean felter korrekt
    for c in ['ER_EMNE', 'SKYGGEHOLD', 'START_11_26_27']:
        df_display[c] = df_display[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False}).fillna(False)
        
    df_display['IS_HIF'] = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)
    
    return df_display

# --- 4. UI ---
def vis_side():
    st.set_page_config(layout="wide", page_title="HIF Scouting")
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, _ = get_github_file(SCOUT_DB_PATH)
    if content is None: return
    df_display = prepare_df(content)

    t1, t2, t3, t4 = st.tabs(["Emneliste", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    # Column config bruger nu STORE bogstaver for at matche dataframe
    cfg = {
        "PLAYER_WYID": None,
        "KONTRAKT_DT": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY"),
        "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_ORDEN),
        "ER_EMNE": st.column_config.CheckboxColumn("Emne"),
        "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge"),
        "START_11_26_27": st.column_config.CheckboxColumn("Start 11 (26/27)"),
        "POS_343": st.column_config.SelectboxColumn("3-4-3", options=POS_OPTS),
        "POS_433": st.column_config.SelectboxColumn("4-3-3", options=POS_OPTS),
        "POS_352": st.column_config.SelectboxColumn("3-5-2", options=POS_OPTS)
    }

    with t1:
        source_t1 = df_display[~df_display['IS_HIF']].copy()
        st.data_editor(source_t1[['NAVN', 'KLUB', 'POS', 'KONTRAKT_DT', 'TRANSFER_VINDUE', 'ER_EMNE', 'SKYGGEHOLD', 'PLAYER_WYID']],
                       column_config=cfg, use_container_width=True, height=600, key="editable_t1", on_change=handle_auto_save, args=("t1", df_display, source_t1))

    with t2:
        source_t2 = df_display[df_display['IS_HIF']].reset_index(drop=True)
        st.data_editor(source_t2[['NAVN', 'KLUB', 'POS', 'KONTRAKT_DT', 'ER_EMNE', 'SKYGGEHOLD', 'PLAYER_WYID']],
                       column_config=cfg, use_container_width=True, height=600, key="editable_t2", on_change=handle_auto_save, args=("t2", df_display, source_t2))

    with t3:
        source_t3 = df_display[df_display['SKYGGEHOLD'] == True].reset_index(drop=True)
        st.data_editor(source_t3[['NAVN', 'KLUB', 'POS', 'POS_343', 'POS_433', 'POS_352', 'START_11_26_27', 'PLAYER_WYID']],
                       column_config=cfg, use_container_width=True, height=600, key="editable_t3", on_change=handle_auto_save, args=("t3", df_display, source_t3))

    with t4:
        c_pitch, c_ctrl = st.columns([8.2, 1.8])
        with c_ctrl:
            # Definition af rækkefølge: Nuværende -> Startopstilling -> Vinduer
            display_opts = ["Nuværende trup", "Startopstilling (26/27)"] + [k for k in VINDUE_DATOER.keys() if k != "Nuværende trup"]
            
            sel_v = st.selectbox("Visning", display_opts)
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()

        with c_pitch:
            f_suffix = st.session_state.form_skygge.replace('-', '')
            p_col = f"POS_{f_suffix}"
            
            # --- FILTRERINGSLOGIK ---
            if sel_v == "Startopstilling (26/27)":
                # KONTRAKT IGNORERES HER: Vi tager alle med flueben i Start_11
                df_f = df_display[df_display['START_11_26_27'] == True].copy()
                ref_dt = datetime(2026, 7, 1) # Bruges kun til farve-legende, ikke filtrering
                
            elif sel_v == "Nuværende trup":
                df_f = df_display[df_display['IS_HIF']].copy()
                ref_dt = datetime.now()
                
            else:
                # FOR TRANSFERVINDUER: Her filtrerer vi stadig på kontraktudløb
                ref_dt = VINDUE_DATOER.get(sel_v, datetime.now())
                hif = df_display[df_display['IS_HIF']].copy()
                emner = df_display[(df_display['SKYGGEHOLD'] == True) & (~df_display['IS_HIF']) & (df_display['TRANSFER_VINDUE'] == sel_v)].copy()
                
                # Fjern kun spillere her, hvis deres kontrakt er udløbet før vinduet
                hif = hif[~((hif['KONTRAKT_DT'].notna()) & (hif['KONTRAKT_DT'] < ref_dt))]
                df_f = pd.concat([hif, emner]).drop_duplicates(subset=['PLAYER_WYID'])

            # --- TEGNING AF BANE ---
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
                        
            # LEGENDS
            ax.text(3, 3, " < 6 mdr ", size=6, weight='bold', bbox=dict(facecolor=ROD_ADVARSEL))
            ax.text(12, 3, " 6-12 mdr ", size=6, weight='bold', bbox=dict(facecolor=GUL_ADVARSEL))
            ax.text(22, 3, " Transferfri ", size=6, weight='bold', bbox=dict(facecolor=GRON_NY))
            ax.text(33, 3, " Transferkøb ", size=6, weight='bold', color='white', bbox=dict(facecolor=HIF_BLA))

            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,32,'DM'), "2":(55,70,'HWB'), "8":(55,48,'DM'), "10":(75,40,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            drawn_players = []
            for pid, (px, py, lbl) in m.items():
                # Tegn positions-label (f.eks. 'DM')
                ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', 
                        bbox=dict(facecolor=HIF_ROD, edgecolor='white'))
                
                # --- NY LOGIK FOR FORDELING AF 6/8 ---
                # Vi leder efter spillere til denne specifikke plads (pid)
                plist = df_f[(df_f[p_col].astype(str) == str(pid)) & (~df_f['PLAYER_WYID'].isin(drawn_players))]
                
                # HVIS pladsen er tom, og vi er ved at tegne 6 eller 8, 
                # så tjekker vi om der er en "overskydende" spiller fra den anden position
                if plist.empty and str(pid) in ["6", "8"]:
                    modsat_pos = "8" if str(pid) == "6" else "6"
                    plist = df_f[(df_f[p_col].astype(str) == modsat_pos) & (~df_f['PLAYER_WYID'].isin(drawn_players))].head(1)

                # Tegn de fundne spillere
                for i, (_, r) in enumerate(plist.iterrows()):
                    drawn_players.append(r['PLAYER_WYID'])
                    k_c = get_status_color(r['KONTRAKT_DT'], ref_date=ref_dt)
                    
                    txt_c, bg = "black", "white"
                    if r['IS_HIF']:
                        bg = ROD_ADVARSEL if k_c == "#444444" else (k_c if k_c else "white")
                    else:
                        bg, txt_c = (GRON_NY, "black") if k_c in ["#444444", ROD_ADVARSEL] else (HIF_BLA, "white")
                    
                    ax.text(px, py + (i * 3.2), r['NAVN'], size=7.5, ha='center', weight='bold', color=txt_c, 
                            bbox=dict(facecolor=bg, edgecolor="black", alpha=0.9))
            
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
