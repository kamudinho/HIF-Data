# --- FIL: tools/scouting/emne_db.py ---
import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 

POS_OPTIONS = {
    "1": "Målmand", "2": "Hoejre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Hoejre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

VINDUE_OPTIONS_GLOBAL = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

# --- HJÆLPEFUNKTIONER ---
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

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content), skipinitialspace=True)
    df.columns = [str(c).upper().strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    
    if 'TRANSFER_VINDUE' in df.columns:
        df['TRANSFER_VINDUE'] = df['TRANSFER_VINDUE'].astype(str).replace(['Nu', 'nu', 'NU', 'nan'], 'Nuværende trup')
    else:
        df['TRANSFER_VINDUE'] = "Nuværende trup" if is_hif else "Sommer 26"

    for c in ['SKYGGEHOLD', 'ER_EMNE']:
        if c in df.columns:
            b_map = {True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False, 'TRUE':True, 'FALSE':False}
            df[c] = df[c].map(b_map).fillna(False)
        else:
            df[c] = False

    pos_cols = ['POS', 'POS_343', 'POS_433', 'POS_352']
    for c in pos_cols:
        if c not in df.columns: df[c] = "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).str.strip()
        df[c] = df[c].replace(['nan', 'None', '', 'True', 'False'], '0')

    for tac in ['POS_343', 'POS_433', 'POS_352']:
        df.loc[df[tac] == "0", tac] = df['POS']

    df['IS_HIF'] = is_hif
    return df

# --- APP LOGIK ---
# FIX: Tilføjet df_input som argument, så den ikke fejler ved kald fra hovedfilen
def vis_side(df_input=None):
    # Vi bruger ikke df_input her, da vi henter frisk data fra GitHub for at kunne gemme korrekt
    st.markdown("<style>.stAppViewBlockContainer { padding-top: 0px !important; } div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }</style>", unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)

    _, t_col2 = st.columns([4, 1])
    sel_v = t_col2.selectbox("Visning på bane:", VINDUE_OPTIONS_GLOBAL, key="v_sel_global")

    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # 1 & 2: ADMINISTRATION
    for i, (path, name, is_hif_flag) in enumerate([(SCOUT_DB_PATH, "EMNE", False), (HIF_PATH, "HIF", True)]):
        with tabs[i]:
            curr_df = df_hif if is_hif_flag else df_scout[df_scout['ER_EMNE']]
            if not curr_df.empty:
                cols = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
                ed = st.data_editor(curr_df.set_index('Navn')[cols], use_container_width=True, key=f"ed_{name}")
                
                if not ed.equals(curr_df.set_index('Navn')[cols]):
                    raw_c, sha = get_github_file(path)
                    df_save = pd.read_csv(StringIO(raw_c))
                    df_save.columns = [c.upper().strip() for c in df_save.columns]
                    if 'NAVN' in df_save.columns: df_save = df_save.rename(columns={'NAVN': 'Navn'})
                    
                    for navn, row in ed.iterrows():
                        mask = df_save['Navn'] == navn
                        df_save.loc[mask, ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD', 'POS_343', 'POS_433', 'POS_352']] = \
                            [row['TRANSFER_VINDUE'], row['POS'], row['SKYGGEHOLD'], row['POS'], row['POS'], row['POS']]
                    
                    push_to_github(path, f"Update {name}", df_save.to_csv(index=False), sha)
                    st.rerun()

    # 3: SKYGGELISTE (LÅST VINDUE)
    with tabs[2]:
        df_s = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]])
        if not df_s.empty:
            ed_s = st.data_editor(
                df_s.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']], 
                use_container_width=True,
                key="sky_ed_final",
                column_config={
                    "TRANSFER_VINDUE": st.column_config.TextColumn("Vindue", disabled=True),
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                }
            )
            if not ed_s.equals(df_s.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']]):
                for navn, row in ed_s.iterrows():
                    for p in [SCOUT_DB_PATH, HIF_PATH]:
                        rc, rsha = get_github_file(p)
                        if not rc: continue
                        tmp = pd.read_csv(StringIO(rc))
                        tmp.columns = [c.upper().strip() for c in tmp.columns]
                        if 'NAVN' in tmp.columns: tmp = tmp.rename(columns={'NAVN': 'Navn'})
                        if navn in tmp['Navn'].values:
                            tmp.loc[tmp['Navn'] == navn, ['POS_343', 'POS_433', 'POS_352']] = \
                                [row['POS_343'], row['POS_433'], row['POS_352']]
                            push_to_github(p, "Update Skygge Pos", tmp.to_csv(index=False), rsha)
                st.rerun()

    # 4: BANE
    with tabs[3]:
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"

        if sel_v == "Nuværende trup":
            df_filtered = df_hif.copy()
        else:
            h_s = df_hif[df_hif['SKYGGEHOLD']]
            e_s = df_scout[(df_scout['SKYGGEHOLD']) & (df_scout['TRANSFER_VINDUE'] == sel_v)]
            df_filtered = pd.concat([h_s, e_s])

        c_p, c_m = st.columns([8.5, 1.5])
        with c_m:
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, key=f"btn_{opt}", type="primary" if f == opt else "secondary"):
                    st.session_state.form_skygge = opt
                    st.rerun()

        with c_p:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
            fig, ax = pitch.draw(figsize=(10, 6))
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(55,10,'VWB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "2":(55,70,'HWB'), "11":(80,15,'VW'), "9":(100,40,'ANG'), "7":(80,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,10,'VB'), "4":(30,25,'VCB'), "3":(30,55,'HCB'), "2":(35,70,'HB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "10":(75,40,'CM'), "11":(85,15,'VW'), "9":(100,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(45,10,'VWB'), "6":(60,30,'DM'), "8":(60,50,'DM'), "2":(45,70,'HWB'), "10":(75,40,'CM'), "9":(95,32,'ANG'), "7":(95,48,'ANG')}}[f]

            for pid, (px, py, lbl) in m.items():
                ax.text(px, py-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white'))
                at_pos = df_filtered[df_filtered[p_col].astype(str) == str(pid)]
                for i, (_, p) in enumerate(at_pos.iterrows()):
                    bg = GRON_NY if not p['IS_HIF'] else "white"
                    ax.text(px, py + (i * 2.5), f"{p['Navn']}{'*' if not p['IS_HIF'] else ''}", size=7, ha='center', weight='bold', bbox=dict(facecolor=bg, alpha=0.8))
            st.pyplot(fig)

# Sørg for at den kun kører hvis den kaldes direkte (til test)
if __name__ == "__main__":
    vis_side()
