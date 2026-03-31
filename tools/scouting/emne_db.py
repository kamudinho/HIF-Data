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
GRON_NY = "#ccffcc" 

POS_OPTIONS = {
    "1": "Målmand", "2": "Hoejre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Hoejre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

# Opdelte vinduer for at styre logikken
VINDUE_OPTIONS_GLOBAL = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
EMNE_VINDUE_OPTIONS = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
HIF_VINDUE_OPTIONS = ["Nuværende trup"]

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
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    
    # Standardiser Transfervindue
    if 'TRANSFER_VINDUE' in df.columns:
        df['TRANSFER_VINDUE'] = df['TRANSFER_VINDUE'].replace(['Nu', 'nu', 'NU'], 'Nuværende trup').fillna("Sommer 26")
    else:
        df['TRANSFER_VINDUE'] = "Nuværende trup" if is_hif else "Sommer 26"

    # Boolean rensning
    for c in ['ER_EMNE', 'SKYGGEHOLD']:
        if c not in df.columns:
            df[c] = False
        else:
            b_map = {True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False, 'TRUE':True, 'FALSE':False}
            df[c] = df[c].map(b_map).fillna(False)
    
    # Position-synkronisering (Sikrer at POS altid er en tekst-streng af tallet)
    pos_cols = ['POS', 'POS_343', 'POS_433', 'POS_352']
    for c in pos_cols:
        if c not in df.columns: df[c] = "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace(['nan', 'None', ''], '0').str.strip()
    
    # VIGTIGT: Hvis en taktisk position er 0, så arver den fra hoved-POS med det samme
    for tac in ['POS_343', 'POS_433', 'POS_352']:
        mask = (df[tac] == "0") | (df[tac] == "")
        df.loc[mask, tac] = df['POS']

    if 'KONTRAKT' in df.columns:
        df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=False, errors='coerce').dt.date
    
    df['IS_HIF'] = is_hif
    return df

# --- HOVEDSIDE ---
def vis_side(df_input_unused=None):
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 0px !important; }
            div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }
            div[data-testid="stDataEditor"] { min-height: 650px !important; }
        </style>
    """, unsafe_allow_html=True)

    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)

    t_col1, t_col2 = st.columns([4, 1])
    with t_col2:
        sel_v = st.selectbox("", VINDUE_OPTIONS_GLOBAL, key="global_vindue_sel")

    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # --- LISTER (TAB 1 & 2) ---
    configs = [(tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "EMNE", False), 
               (tabs[1], df_hif, HIF_PATH, "HIF", True)]

    for tab, df_display, path, key_base, is_hif_flag in configs:
        with tab:
            if not df_display.empty:
                # Vælg tilladte vinduer baseret på om det er emne eller HIF
                v_opts = HIF_VINDUE_OPTIONS if is_hif_flag else EMNE_VINDUE_OPTIONS
                
                target_cols = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
                df_editor_in = df_display.set_index('Navn')[target_cols]
                
                ed = st.data_editor(df_editor_in, use_container_width=True, height=600, key=f"ed_v2_{key_base}",
                    column_config={
                        "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=v_opts),
                        "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                        "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")
                    })
                
                if not ed.equals(df_editor_in):
                    c, sha = get_github_file(path)
                    df_save = pd.read_csv(StringIO(c))
                    df_save.columns = [str(x).upper().strip() for x in df_save.columns]
                    if 'NAVN' in df_save.columns: df_save = df_save.rename(columns={'NAVN': 'Navn'})
                    
                    for navn, row in ed.iterrows():
                        mask = df_save['Navn'] == navn
                        # Opdater POS og gennemtving synkronisering til taktiske felter ved ændring i hovedliste
                        df_save.loc[mask, ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD', 'POS_343', 'POS_433', 'POS_352']] = [
                            row['TRANSFER_VINDUE'], row['POS'], row['SKYGGEHOLD'], row['POS'], row['POS'], row['POS']
                        ]
                    push_to_github(path, f"Sync {key_base} Data", df_save.to_csv(index=False), sha)
                    st.rerun()

    # --- TAB 3: SKYGGELISTE ---
    with tabs[2]:
        df_s = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            df_s_input = df_s.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']]
            ed_s = st.data_editor(df_s_input, use_container_width=True, height=600, key="sky_ed_v2",
                column_config={
                    # Her tillader vi alle vinduer, men logikken fra hovedlisten begrænser emnerne ved oprettelse
                    "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_OPTIONS_GLOBAL),
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                })
            
            if not ed_s.equals(df_s_input):
                for navn, row in ed_s.iterrows():
                    for p in [SCOUT_DB_PATH, HIF_PATH]:
                        c_raw, sha_raw = get_github_file(p)
                        df_tmp = pd.read_csv(StringIO(c_raw))
                        df_tmp.columns = [col.upper().strip() for col in df_tmp.columns]
                        if 'NAVN' in df_tmp.columns: df_tmp = df_tmp.rename(columns={'NAVN': 'Navn'})
                        if navn in df_tmp['Navn'].values:
                            df_tmp.loc[df_tmp['Navn'] == navn, ['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']] = [
                                row['TRANSFER_VINDUE'], row['POS_343'], row['POS_433'], row['POS_352']
                            ]
                            push_to_github(p, "Update Skygge Pos", df_tmp.to_csv(index=False), sha_raw)
                st.rerun()

    # --- TAB 4: BANE ---
    with tabs[3]:
        df_total = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_total.empty:
            # FILTRERING:
            if sel_v == "Nuværende trup":
                # Vis kun HIF-spillere der reelt er i nuværende trup
                df_filtered = df_total[(df_total['IS_HIF'] == True) & (df_total['TRANSFER_VINDUE'] == "Nuværende trup")]
            else:
                # Vis nuværende HIF (base) + de emner der er sat til det specifikke vindue
                df_filtered = df_total[(df_total['TRANSFER_VINDUE'] == "Nuværende trup") | (df_total['TRANSFER_VINDUE'] == sel_v)]

            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"

            c_p, c_m = st.columns([8.5, 1.5])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"b_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()

            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(10, 6))
                
                m = {
                    "3-4-3": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(55,10,'VWB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "2":(55,70,'HWB'), "11":(80,15,'VW'), "9":(100,40,'ANG'), "7":(80,65,'HW')},
                    "4-3-3": {"1":(10,40,'MM'), "5":(35,10,'VB'), "4":(30,25,'VCB'), "3":(30,55,'HCB'), "2":(35,70,'HB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "10":(75,40,'CM'), "11":(85,15,'VW'), "9":(100,40,'ANG'), "7":(85,65,'HW')},
                    "3-5-2": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(45,10,'VWB'), "6":(60,30,'DM'), "8":(60,50,'DM'), "2":(45,70,'HWB'), "10":(75,40,'CM'), "9":(95,32,'ANG'), "7":(95,48,'ANG')}
                }[f]

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_filtered[df_filtered[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(players.iterrows()):
                        # Markér emner med grøn og stjerne hvis de matcher det valgte vindue
                        is_new = str(p['TRANSFER_VINDUE']) == sel_v and sel_v != "Nuværende trup"
                        bg = GRON_NY if is_new else "white"
                        ax.text(x, y + (i * 2.3), f"{p['Navn']}{'*' if is_new else ''}", size=7, ha='center', va='center', weight='bold', 
                                bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.8, boxstyle='square,pad=0.2'))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
