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

VINDUE_OPTIONS = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

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

def style_kontrakt(df):
    styler = pd.DataFrame('', index=df.index, columns=df.columns)
    if 'KONTRAKT' in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, 'KONTRAKT']
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183: styler.at[idx, 'KONTRAKT'] = 'background-color: #ffcccc; color: black;'
                elif days <= 365: styler.at[idx, 'KONTRAKT'] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    if 'TRANSFER_VINDUE' not in df.columns: df['TRANSFER_VINDUE'] = "Nu"
    needed = ['SKYGGEHOLD', 'POS', 'POS_343', 'POS_433', 'POS_352']
    for c in needed:
        if c not in df.columns: df[c] = False if c == 'SKYGGEHOLD' else "0"
    for c in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()
    df['SKYGGEHOLD'] = df['SKYGGEHOLD'].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False}).fillna(False)
    if 'KONTRAKT' in df.columns:
        df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=False, errors='coerce').dt.date
    df['KLUB'] = 'Hvidovre IF' if is_hif else df.get('KLUB', '-')
    return df

# --- HOVEDSIDE ---
def vis_side(df_input_unused=None):
    st.markdown("""
        <style>
            div.block-container{padding: 0.2rem 0.5rem; max-width: 95% !important;}
            /* Fjern label/overskrift fra selectbox helt */
            div[data-testid="stSelectbox"] label { display: none; }
            
            /* Aggressiv reducering af afstand mellem tabs og indhold */
            .stTabs { margin-top: 5px; }
            div[data-baseweb="tab-panel"] {
                padding-top: 0px !important;
                margin-top: 5px !important;
            }
            
            /* Fjern ekstra luft under knapperne til højre */
            div[data-testid="column"] { padding-top: 0px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    # Hent data
    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    df_scout = prepare_df(s_c)
    df_hif = prepare_df(h_c, is_hif=True)

    # --- TOP: DROPDOWN I HØJRE SIDE ---
    t_col1, t_col2 = st.columns([4, 1])
    with t_col2:
        sel_v = st.selectbox("", VINDUE_OPTIONS, key="global_vindue_sel")

    # Tabs placeres herunder
    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # --- TAB 1 & 2: LISTER ---
    configs = [(tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "EMNE_LIST"), 
               (tabs[1], df_hif, HIF_PATH, "HIF_LIST")]
    
    for tab, df_display, path, key_base in configs:
        with tab:
            if not df_display.empty:
                target_cols = ['TRANSFER_VINDUE', 'POS', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']
                df_editor_in = df_display.set_index('Navn')[target_cols]
                ed = st.data_editor(
                    df_editor_in.style.apply(style_kontrakt, axis=None),
                    use_container_width=True,
                    key=f"ed_v10_{key_base}", 
                    column_config={
                        "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_OPTIONS),
                        "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                        "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")
                    }
                )
                if not ed.equals(df_editor_in):
                    c, sha = get_github_file(path)
                    df_save = pd.read_csv(StringIO(c))
                    df_save.columns = [str(x).upper().strip() for x in df_save.columns]
                    if 'NAVN' in df_save.columns: df_save = df_save.rename(columns={'NAVN': 'Navn'})
                    for navn, row in ed.iterrows():
                        mask = df_save['Navn'] == navn
                        df_save.loc[mask, ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']] = [row['TRANSFER_VINDUE'], row['POS'], row['SKYGGEHOLD']]
                    push_to_github(path, "Update data", df_save.to_csv(index=False), sha)
                    st.rerun()

    # --- TAB 3: SKYGGELISTE ---
    with tabs[2]:
        df_s = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            df_s_input = df_s.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352', 'KONTRAKT']]
            ed_s = st.data_editor(
                df_s_input.style.apply(style_kontrakt, axis=None),
                use_container_width=True,
                key="skyggeliste_editor_v10",
                column_config={
                    "TRANSFER_VINDUE": st.column_config.SelectboxColumn("Vindue", options=VINDUE_OPTIONS),
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                }
            )
            if not ed_s.equals(df_s_input):
                for navn, row in ed_s.iterrows():
                    for p in [SCOUT_DB_PATH, HIF_PATH]:
                        c_raw, sha_raw = get_github_file(p)
                        df_tmp = pd.read_csv(StringIO(c_raw))
                        df_tmp.columns = [col.upper().strip() for col in df_tmp.columns]
                        if 'NAVN' in df_tmp.columns: df_tmp = df_tmp.rename(columns={'NAVN': 'Navn'})
                        if navn in df_tmp['Navn'].values:
                            df_tmp.loc[df_tmp['Navn'] == navn, ['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']] = [row['TRANSFER_VINDUE'], row['POS_343'], row['POS_433'], row['POS_352']]
                            push_to_github(p, "Update tact", df_tmp.to_csv(index=False), sha_raw)
                st.rerun()

    # --- TAB 4: BANE ---
    with tabs[3]:
        df_total = pd.concat([df_scout[df_scout['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_total.empty:
            df_filtered = df_total[df_total['TRANSFER_VINDUE'].isin(["Nu", sel_v])]
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            
            c_p, c_m = st.columns([8.5, 1.5])
            with c_m:
                # Mindre spacer for at flugte med legende-teksten på banen
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True) 
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"btn_v10_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(10, 6))
                
                # Legends og Overskrift (Rykket lidt op: y=2)
                ax.text(2, 4, " < 6 mdr ", size=7, weight='bold', bbox=dict(facecolor='#ffcccc', edgecolor='#333', boxstyle='round,pad=0.2'))
                ax.text(14, 4, " 6-12 mdr ", size=7, weight='bold', bbox=dict(facecolor='#ffffcc', edgecolor='#333', boxstyle='round,pad=0.2'))
                ax.text(26, 4, " Ny tilgang ", size=7, weight='bold', bbox=dict(facecolor=GRON_NY, edgecolor='black', linewidth=1.2, boxstyle='round,pad=0.2'))
                ax.text(118, 4, f"Vindue: {sel_v}", size=12, color="black", weight='bold', ha='right')

                m = {
                    "3-4-3": {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')},
                    "4-3-3": {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')},
                    "3-5-2": {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}
                }[f]
                
                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_filtered[df_filtered[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(players.iterrows()):
                        bg = "white"; edge = "#333"; lw = 1
                        is_new = str(p['TRANSFER_VINDUE']) != "Nu"
                        
                        if is_new:
                            bg = GRON_NY; edge = "black"; lw = 1.2
                        elif pd.notna(p['KONTRAKT']):
                            diff = (p['KONTRAKT'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        
                        ax.text(x, y+(i*2.3), f"{p['Navn']}{'*' if is_new else ''}", size=7.5, ha='center', weight='bold', 
                                bbox=dict(facecolor=bg, edgecolor=edge, alpha=0.9, boxstyle='square,pad=0.1', linewidth=lw))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
