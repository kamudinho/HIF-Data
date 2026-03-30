#tools/scouting/emne_db.py
import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "1": "Maalmand", "2": "Hoejre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Hoejre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

# "Nu" fjernet fra visnings-dropdown, men bibeholdt i data-muligheder
VINDUE_OPTIONS = ["Nu", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
DISPLAY_VINDUE = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

# --- GITHUB & DATA FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def style_skyggeliste(row):
    """ Logik for farver på skyggelisten """
    styles = [''] * len(row)
    # Find index for KONTRAKT og KLUB i rækken
    try:
        idx_kontrakt = row.index.get_loc('KONTRAKT')
        idx_klub = row.index.get_loc('KLUB')
        
        is_hif = row.iloc[idx_klub] == 'Hvidovre IF'
        val = row.iloc[idx_kontrakt]
        
        # 1. Grøn hvis det er en transfer (ikke HIF)
        if not is_hif:
            styles[idx_kontrakt] = 'background-color: #c6efce; color: #006100;' # Grøn
        # 2. Rød/Gul hvis det er HIF
        elif pd.notna(val) and not isinstance(val, str):
            days = (val - datetime.now().date()).days
            if days < 183: 
                styles[idx_kontrakt] = 'background-color: #ffcccc; color: black;' # Rød
            elif days <= 365: 
                styles[idx_kontrakt] = 'background-color: #ffffcc; color: black;' # Gul
    except:
        pass
    return styles

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    
    for c in ['TRANSFER_VINDUE', 'POS', 'POS_343', 'POS_433', 'POS_352']:
        if c not in df.columns: df[c] = "Nu" if c == 'TRANSFER_VINDUE' else "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()
    
    if 'SKYGGEHOLD' not in df.columns: df['SKYGGEHOLD'] = False
    df['SKYGGEHOLD'] = df['SKYGGEHOLD'].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False}).fillna(False)

    if 'KONTRAKT' in df.columns:
        df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=False, errors='coerce').dt.date
    
    df['KLUB'] = 'Hvidovre IF' if is_hif else df.get('KLUB', 'Transfer')
    return df

# --- HOVEDSIDE ---
def vis_side():
    st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)
    
    # 1. DROP DOWN OVER TABS
    c1, c2 = st.columns([2, 4])
    with c1:
        valgt_vindue = st.selectbox("🎯 Planlægningsvindue:", DISPLAY_VINDUE)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    df_scout = prepare_df(s_c)
    df_hif = prepare_df(h_c, is_hif=True)
    
    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # --- TABS 1 & 2: VEDLIGEHOLDELSE ---
    configs = [(tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "EMNE"), (tabs[1], df_hif, HIF_PATH, "HIF")]
    for tab, df_display, path, key in configs:
        with tab:
            if not df_display.empty:
                df_input = df_display.set_index('Navn')[['TRANSFER_VINDUE', 'POS', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']]
                ed = st.data_editor(df_input, use_container_width=True, key=f"ed_{key}",
                    column_config={
                        "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_OPTIONS),
                        "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                        "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")
                    })
                if not ed.equals(df_input):
                    raw_c, raw_sha = get_github_file(path)
                    df_save = pd.read_csv(StringIO(raw_c))
                    df_save.columns = [str(c).upper().strip() for c in df_save.columns]
                    if 'NAVN' in df_save.columns: df_save = df_save.rename(columns={'NAVN': 'Navn'})
                    for navn, row in ed.iterrows():
                        df_save.loc[df_save['Navn'] == navn, ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']] = [row['TRANSFER_VINDUE'], row['POS'], row['SKYGGEHOLD']]
                    push_to_github(path, "Update", df_save.to_csv(index=False), raw_sha)
                    st.rerun()

    # --- TAB 3: SKYGGELISTE (NU MED FARVE-LOGIK) ---
    with tabs[2]:
        df_s = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            df_s_input = df_s.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352', 'KONTRAKT', 'KLUB']]
            
            st.data_editor(
                df_s_input.style.apply(style_skyggeliste, axis=1),
                use_container_width=True,
                key="skyggeliste_editor_v4",
                column_config={
                    "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_OPTIONS),
                    "KLUB": st.column_config.Column(disabled=True),
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                }
            )

    # --- TAB 4: BANE ---
    with tabs[3]:
        df_total = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_total.empty:
            df_filtered = df_total[df_total['TRANSFER_VINDUE'].isin(["Nu", valgt_vindue])]
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            c_p, c_m = st.columns([5,1])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"bt_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(9, 6))
                m = {
                    "3-4-3": {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')},
                    "4-3-3": {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')},
                    "3-5-2": {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}
                }[f]
                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=7, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    p_at = df_filtered[df_filtered[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(p_at.iterrows()):
                        bg = "white"
                        edge = HIF_ROD if p['TRANSFER_VINDUE'] != "Nu" else "#333"
                        # Farve-override på banen også
                        if p['KLUB'] != 'Hvidovre IF': bg = "#c6efce"
                        elif pd.notna(p['KONTRAKT']):
                            diff = (p['KONTRAKT'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        n = p['Navn']
                        if p['TRANSFER_VINDUE'] != "Nu": n += f" ({p['TRANSFER_VINDUE']})"
                        ax.text(x, y+(i*3.5), n, size=7, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor=edge, alpha=0.9, boxstyle='square,pad=0.1', linewidth=1.5 if p['TRANSFER_VINDUE'] != "Nu" else 1))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
