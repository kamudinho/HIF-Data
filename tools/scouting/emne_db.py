import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
EMNE_PATH = "data/emneliste.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
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

# --- DATA PROCESSING ---
def style_kontrakt(df):
    styler = pd.DataFrame('', index=df.index, columns=df.columns)
    if 'Kontrakt' in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, 'Kontrakt']
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183: styler.at[idx, 'Kontrakt'] = 'background-color: #ffcccc; color: black;'
                elif days <= 365: styler.at[idx, 'Kontrakt'] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    
    # Standardisering af Navne-kolonne
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    df = df.dropna(subset=['Navn']).reset_index(drop=True)
    df['Navn'] = df['Navn'].astype(str).str.strip()
    df = df.drop_duplicates(subset=['Navn']).reset_index(drop=True)

    # Taktiske kolonner & Typer
    tactical_cols = ['POS_343', 'POS_433', 'POS_352']
    for col in tactical_cols + ['POS']:
        if col not in df.columns: df[col] = "0"
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()

    # Boolean for Skyggehold
    if 'Skyggehold' not in df.columns: df['Skyggehold'] = False
    df['Skyggehold'] = df['Skyggehold'].fillna(False).replace({'True':True, 'False':False, '1':True, '0':False, 1:True, 0:False}).astype(bool)

    # Dato-parsing
    df['Kontrakt'] = pd.to_datetime(df['Kontrakt'], errors='coerce').dt.date
    df['Klub'] = 'Hvidovre IF' if is_hif else df.get('Klub', '-')
    
    return df

# --- APP LAYOUT ---
def vis_side():
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    e_c, e_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(e_c)
    df_hif = prepare_df(h_c, is_hif=True)

    t1, t2, t3, t4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Bane"])

    # --- TAB 1 & 2: LISTER ---
    for t, d, s, p in [(t1, df_emner, e_s, EMNE_PATH), (t2, df_hif, h_s, HIF_PATH)]:
        with t:
            if d.empty: 
                st.info("Ingen data fundet.")
                continue
            
            h = min(len(d) * 35 + 45, 500)
            ed = st.data_editor(
                d[['POS', 'Navn', 'Klub', 'Kontrakt', 'Skyggehold']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, width="stretch", height=h, key=f"ed_{p}",
                column_config={
                    "Skyggehold": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys()), width="small"),
                    "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                }, disabled=['Navn', 'Klub']
            )
            
            # Check for ændringer
            if not ed['Skyggehold'].equals(d['Skyggehold']) or not ed['POS'].equals(d['POS']):
                for idx in ed.index:
                    name = d.iloc[idx]['Navn']
                    d.loc[d['Navn'] == name, ['Skyggehold', 'POS']] = [ed.iloc[idx]['Skyggehold'], ed.iloc[idx]['POS']]
                push_to_github(p, "Update Selection", d.to_csv(index=False), s)
                st.rerun()

    # --- TAB 3: SKYGGELISTE (TAKTISK) ---
    with t3:
        df_s = pd.concat([df_emner[df_emner['Skyggehold']], df_hif[df_hif['Skyggehold']]], ignore_index=True)
        
        if not df_s.empty:
            st.write("Definer spillernes positioner i de forskellige formationer:")
            h_s_list = min(len(df_s) * 35 + 45, 600)
            ed_s = st.data_editor(
                df_s[['Navn', 'POS_343', 'POS_433', 'POS_352', 'Kontrakt']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, width="stretch", height=h_s_list, key="ed_tactical",
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                    "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY", disabled=True)
                }, disabled=['Navn']
            )
            
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_s[['POS_343', 'POS_433', 'POS_352']]):
                for _, row in ed_s.iterrows():
                    for src, p, sh in [(df_emner, EMNE_PATH, e_s), (df_hif, HIF_PATH, h_s)]:
                        if row['Navn'] in src['Navn'].values:
                            src.loc[src['Navn'] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                            push_to_github(p, f"Tactical: {row['Navn']}", src.to_csv(index=False), sh)
                st.rerun()
        else:
            st.info("Ingen spillere valgt til skyggelisten.")

    # --- TAB 4: BANE ---
    with t4:
        df_s = pd.concat([df_emner[df_emner['Skyggehold']], df_hif[df_hif['Skyggehold']]], ignore_index=True)
        if not df_s.empty:
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            
            c_p, c_m = st.columns([5,1])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"b_{opt}", width=100, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(9, 6))
                
                # Formationer
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=7, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_s[df_s[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(players.iterrows()):
                        bg = "white"
                        if pd.notna(p['Kontrakt']):
                            diff = (p['Kontrakt'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        ax.text(x, y+(i*3.8), p['Navn'], size=7, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor='#333', alpha=0.9, boxstyle='square,pad=0.1'))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
