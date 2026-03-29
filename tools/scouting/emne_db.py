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

# --- DATA PREP ---
def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df = df.rename(columns={'NAVN': 'Navn', 'POS': 'POS', 'KONTRAKT': 'Kontrakt'})
    
    # 1. FJERN DUBLETTER OG NULSTIL INDEKS (Løser 'duplicate keys' fejlen)
    df['Navn'] = df['Navn'].astype(str).str.strip()
    df = df.drop_duplicates(subset=['Navn']).reset_index(drop=True)
    
    # 2. DATO HÅNDTERING
    df['Kontrakt'] = pd.to_datetime(df['Kontrakt'], dayfirst=True, errors='coerce').dt.date
    
    # 3. POSITIONER TIL DROPDOWN (Tving til streng, fjern .0)
    cols = ['POS', 'POS_343', 'POS_433', 'POS_352']
    for c in cols:
        if c not in df.columns: df[c] = "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace('nan', '0')
            
    col_sky = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    df['Skyggehold'] = df[col_sky].fillna(False).replace({'True':True,'False':False,'1':True,'0':False}).astype(bool) if col_sky else False
    df['Klub'] = 'Hvidovre IF' if is_hif else df.get('Klub', '-')
    return df

# --- SIDE LOGIK ---
def vis_side(dp=None):
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    # Hent filer
    e_c, e_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(e_c)
    df_hif = prepare_df(h_c, is_hif=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    # TAB 1 & 2: Vælg spillere til skyggehold
    for t, d, s, p in [(t1, df_emner, e_s, EMNE_PATH), (t2, df_hif, h_s, HIF_PATH)]:
        with t:
            if d.empty: continue
            ed = st.data_editor(d[['POS', 'Navn', 'Klub', 'Kontrakt', 'Skyggehold']], 
                                hide_index=True, use_container_width=True, key=f"ed_{p}",
                                column_config={
                                    "Skyggehold": st.column_config.CheckboxColumn("🛡️"),
                                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                                    "Kontrakt": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                                }, disabled=['Navn', 'Klub'])
            
            if not ed['Skyggehold'].equals(d['Skyggehold']) or not ed['POS'].equals(d['POS']):
                d.update(ed)
                d_save = d.copy().rename(columns={'Navn':'NAVN','POS':'POS','Kontrakt':'KONTRAKT'})
                d_save['KONTRAKT'] = pd.to_datetime(d_save['KONTRAKT']).dt.strftime('%d-%m-%Y')
                push_to_github(p, "Update Selection", d_save.to_csv(index=False), s)
                st.rerun()

    # TAB 3: Konfiguration af alle 3 formationer
    with t3:
        # Saml kun dem der er valgt til skyggehold
        df_skygge = pd.concat([df_emner[df_emner['Skyggehold']], df_hif[df_hif['Skyggehold']]], ignore_index=True)
        
        if not df_skygge.empty:
            st.subheader("Positioner i formationerne")
            cols = ['Navn', 'POS_343', 'POS_433', 'POS_352']
            ed_s = st.data_editor(df_skygge[cols], hide_index=True, use_container_width=True, key="ed_formations",
                                  column_config={
                                      "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                      "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                      "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                  }, disabled=['Navn'])
            
            if not ed_s.equals(df_skygge[cols]):
                # Gem ændringer tilbage til de respektive filer
                for _, row in ed_s.iterrows():
                    name = row['Navn']
                    for source_df, path, sha in [(df_emner, EMNE_PATH, e_s), (df_hif, HIF_PATH, h_s)]:
                        if name in source_df['Navn'].values:
                            for c in ['POS_343', 'POS_433', 'POS_352']:
                                source_df.loc[source_df['Navn'] == name, c] = row[c]
                            s_save = source_df.copy().rename(columns={'Navn':'NAVN','POS':'POS','Kontrakt':'KONTRAKT'})
                            s_save['KONTRAKT'] = pd.to_datetime(s_save['KONTRAKT']).dt.strftime('%d-%m-%Y')
                            push_to_github(path, "Update Formations", s_save.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Ingen spillere valgt til skyggeholdet.")

    # TAB 4: Banen
    with t4:
        df_skygge = pd.concat([df_emner[df_emner['Skyggehold']], df_hif[df_hif['Skyggehold']]], ignore_index=True)
        if not df_skygge.empty:
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            
            c_p, c_m = st.columns([6,1])
            with c_m:
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"btn_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                # Simple position maps
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,20,'VCB'), 3.5:(30,40,'CB'), 3:(30,60,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,20,'VCB'), 3.5:(30,40,'CB'), 3:(30,60,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,30,'ANG'), 7:(95,50,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round'))
                    players = df_skygge[df_skygge[p_col] == str(pid)]
                    for i, (_, row) in enumerate(players.iterrows()):
                        ax.text(x, y+(i*3), row['Navn'], size=7, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
