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

# --- GITHUB ---
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

# --- DEN STORE RENSNING (Løser duplicate keys) ---
def clean_and_prepare(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    
    # 1. Standardiser navne (NAVN -> Navn)
    df.columns = [c.strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    if 'KONTRAKT' in df.columns: df = df.rename(columns={'KONTRAKT': 'Kontrakt'})
    
    # 2. Fjern rækker uden navn (løser de tomme komma-rækker i bunden af din fil)
    df = df.dropna(subset=['Navn'])
    df['Navn'] = df['Navn'].astype(str).str.strip()
    
    # 3. Fjern dubletter baseret på Navn og nulstil index fuldstændigt
    df = df.drop_duplicates(subset=['Navn']).reset_index(drop=True)
    
    # 4. Sikr formations-kolonner (vigtigt for emneliste.csv)
    target_cols = ['POS', 'POS_343', 'POS_433', 'POS_352']
    for c in target_cols:
        if c not in df.columns:
            df[c] = df['POS'] if 'POS' in df.columns else "0"
        # Tving til tekst og fjern .0 (løser dropdown-lås)
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()
    
    # 5. Datoer
    df['Kontrakt'] = pd.to_datetime(df['Kontrakt'], errors='coerce').dt.date
    
    # 6. Skyggehold status
    if 'Skyggehold' not in df.columns: df['Skyggehold'] = False
    df['Skyggehold'] = df['Skyggehold'].fillna(False).replace({'True':True, 'False':False, '1':True, '0':False, 1:True, 0:False}).astype(bool)
    
    df['Klub'] = 'Hvidovre IF' if is_hif else df.get('Klub', '-')
    return df

# --- HOVEDSIDE ---
def vis_side(dp=None):
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    e_c, e_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_emner = clean_and_prepare(e_c)
    df_hif = clean_and_prepare(h_c, is_hif=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    # --- TAB: LISTER ---
    for t, d, s, p in [(t1, df_emner, e_s, EMNE_PATH), (t2, df_hif, h_s, HIF_PATH)]:
        with t:
            if d.empty: continue
            
            # Vi bruger en kopi med nulstillet index til editoren
            df_display = d[['POS', 'Navn', 'Klub', 'Kontrakt', 'Skyggehold']].copy().reset_index(drop=True)
            
            ed = st.data_editor(df_display, hide_index=True, use_container_width=True, key=f"ed_{p}_v6",
                                column_config={
                                    "Skyggehold": st.column_config.CheckboxColumn("🛡️"),
                                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                                    "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                                }, disabled=['Navn', 'Klub'])
            
            # Gem hvis ændret
            if not ed['Skyggehold'].equals(df_display['Skyggehold']) or not ed['POS'].equals(df_display['POS']):
                # Map ændringer tilbage til d baseret på Navn
                for idx, row in ed.iterrows():
                    name = row['Navn']
                    d.loc[d['Navn'] == name, 'Skyggehold'] = row['Skyggehold']
                    d.loc[d['Navn'] == name, 'POS'] = row['POS']
                
                d_save = d.copy()
                d_save['KONTRAKT'] = pd.to_datetime(d_save['Kontrakt']).dt.strftime('%d-%m-%Y')
                push_to_github(p, "Update Player Status", d_save.to_csv(index=False), s)
                st.rerun()

    # --- TAB: SKYGGELISTE (3 DROPDOWNS) ---
    with t3:
        # Saml kun de valgte og nulstil index FØR concat
        s_e = df_emner[df_emner['Skyggehold']].copy()
        s_h = df_hif[df_hif['Skyggehold']].copy()
        df_samlet = pd.concat([s_e, s_h], ignore_index=True)
        
        if not df_samlet.empty:
            cols = ['Navn', 'POS_343', 'POS_433', 'POS_352']
            ed_s = st.data_editor(df_samlet[cols], hide_index=True, use_container_width=True, key="ed_formations_v6",
                                  column_config={
                                      "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                      "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                      "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                  }, disabled=['Navn'])
            
            if not ed_s.equals(df_samlet[cols]):
                for _, row in ed_s.iterrows():
                    name = row['Navn']
                    # Find i hvilken fil spilleren findes og opdater
                    for source_df, path, sha in [(df_emner, EMNE_PATH, e_s), (df_hif, HIF_PATH, h_s)]:
                        if name in source_df['Navn'].values:
                            for c in ['POS_343', 'POS_433', 'POS_352']:
                                source_df.loc[source_df['Navn'] == name, c] = row[c]
                            s_save = source_df.copy()
                            s_save['KONTRAKT'] = pd.to_datetime(s_save['Kontrakt']).dt.strftime('%d-%m-%Y')
                            push_to_github(path, "Update Formations", s_save.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Vælg spillere i de andre faner først.")

    # --- TAB: BANEVISNING ---
    with t4:
        df_samlet = pd.concat([df_emner[df_emner['Skyggehold']], df_hif[df_hif['Skyggehold']]], ignore_index=True)
        if not df_samlet.empty:
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            c_p, c_m = st.columns([6,1])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"f_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
                fig, ax = pitch.draw(figsize=(10, 7))
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round'))
                    players = df_samlet[df_samlet[p_col].astype(str) == str(pid)]
                    for i, (_, row) in enumerate(players.iterrows()):
                        ax.text(x, y+(i*3.5), row['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.9))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
