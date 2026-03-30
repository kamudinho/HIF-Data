import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

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

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
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
    col = 'KONTRAKT' if 'KONTRAKT' in df.columns else 'Kontrakt'
    if col in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, col]
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183: styler.at[idx, col] = 'background-color: #ffcccc; color: black;'
                elif days <= 365: styler.at[idx, col] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn'])
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
    df = df.drop_duplicates(subset=['Navn'], keep='first')
    
    cols_to_fix = ['POS_343', 'POS_433', 'POS_352', 'POS', 'ER_EMNE', 'SKYGGEHOLD']
    for c in cols_to_fix:
        if c not in df.columns: df[c] = False if 'ER' in c or 'SKYGGE' in c else "0"
    
    for c in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()
    
    for c in ['ER_EMNE', 'SKYGGEHOLD']:
        df[c] = df[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, '1':True, '0':False}).fillna(False)

    if 'KONTRAKT' in df.columns:
        df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=False, errors='coerce').dt.date
    
    df['KLUB'] = 'Hvidovre IF' if is_hif else df.get('KLUB', '-')
    return df.reset_index(drop=True)

# --- HOVEDSIDE ---
def vis_side():
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    s_c, s_s = get_github_file(SCOUT_DB_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_scout_all = prepare_df(s_c)
    df_emner = df_scout_all[df_scout_all['ER_EMNE'] == True].copy()
    df_hif = prepare_df(h_c, is_hif=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # --- LISTER (EMNER & HIF) ---
    configs = [(t1, df_emner, s_s, SCOUT_DB_PATH, "EMNER"), (t2, df_hif, h_s, HIF_PATH, "HIF")]
    
    for tab, df_display, sha, path, key_prefix in configs:
        with tab:
            if df_display.empty:
                st.info("Ingen data.")
                continue

            # Vi bruger Navn som index for editoren for at undgå positional errors
            df_editor_input = df_display.set_index('Navn')[['POS', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']]
            
            edited_df = st.data_editor(
                df_editor_input.style.apply(style_kontrakt, axis=None),
                use_container_width=True,
                hide_index=False, # Vi skal se Navn for at vide hvem vi retter
                key=f"editor_{key_prefix}",
                column_config={
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys()), width="small"),
                    "KONTRAKT": st.column_config.DateColumn("Udloeb", format="DD.MM.YYYY"),
                    "KLUB": st.column_config.Column(disabled=True)
                }
            )

            # Tjek for ændringer
            if not edited_df.equals(df_editor_input):
                full_content, current_sha = get_github_file(path)
                df_to_save = pd.read_csv(StringIO(full_content))
                df_to_save.columns = [str(c).upper().strip() for c in df_to_save.columns]
                if 'NAVN' in df_to_save.columns: df_to_save = df_to_save.rename(columns={'NAVN': 'Navn'})

                for navn, row in edited_df.iterrows():
                    df_to_save.loc[df_to_save['Navn'] == navn, ['SKYGGEHOLD', 'POS']] = [row['SKYGGEHOLD'], row['POS']]
                
                push_to_github(path, "Update status", df_to_save.to_csv(index=False), current_sha)
                st.rerun()

    # --- SKYGGELISTE (TAB 3) ---
    with t3:
        df_s = pd.concat([df_emner[df_emner['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            df_s_input = df_s.set_index('Navn')[['POS_343', 'POS_433', 'POS_352', 'KONTRAKT']]
            ed_s = st.data_editor(
                df_s_input.style.apply(style_kontrakt, axis=None),
                use_container_width=True,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                    "KONTRAKT": st.column_config.DateColumn("Udloeb", disabled=True)
                }
            )
            
            if not ed_s.equals(df_s_input):
                for navn, row in ed_s.iterrows():
                    for p in [SCOUT_DB_PATH, HIF_PATH]:
                        c, sha = get_github_file(p)
                        df_tmp = pd.read_csv(StringIO(c))
                        df_tmp.columns = [col.upper().strip() for col in df_tmp.columns]
                        if 'NAVN' in df_tmp.columns: df_tmp = df_tmp.rename(columns={'NAVN': 'Navn'})
                        if navn in df_tmp['Navn'].values:
                            df_tmp.loc[df_tmp['Navn'] == navn, ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                            push_to_github(p, "Taktisk update", df_tmp.to_csv(index=False), sha)
                st.rerun()

    # --- BANEVISNING (TAB 4) ---
    with t4:
        df_s = pd.concat([df_emner[df_emner['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            c_p, c_m = st.columns([5,1])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"b_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(9, 6))
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=7, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_s[df_s[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(players.iterrows()):
                        bg = "white"
                        if pd.notna(p['KONTRAKT']):
                            diff = (p['KONTRAKT'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        ax.text(x, y+(i*3.5), p['Navn'], size=7, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor='#333', alpha=0.9, boxstyle='square,pad=0.1'))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
