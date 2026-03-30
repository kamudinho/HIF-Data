import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
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

# --- FUNKTIONER ---
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
    """ Farver celler baseret på KONTRAKT (STORE BOGSTAVER) """
    styler = pd.DataFrame('', index=df.index, columns=df.columns)
    # RETTET: Vi kigger nu efter KONTRAKT
    target_col = 'KONTRAKT' if 'KONTRAKT' in df.columns else 'Kontrakt'
    
    if target_col in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, target_col]
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183: styler.at[idx, target_col] = 'background-color: #ffcccc; color: black;'
                elif days <= 365: styler.at[idx, target_col] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    
    # Læs filen
    df = pd.read_csv(StringIO(content))
    
    # 1. Rens kolonnenavne (Fjerner mellemrum og tvinger STORE BOGSTAVER)
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # 2. VIGTIGT: Fjern dublerede kolonnenavne (f.eks. hvis både 'Dato' og 'DATO' fandtes)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # 3. Sikr Navn-kolonnen (Pandas omdøbte NAVN til Navn i din tidligere logik)
    if 'NAVN' in df.columns: 
        df = df.rename(columns={'NAVN': 'Navn'})
    
    # 4. Fjern rækker uden navn (håndterer de tomme kommaer i din CSV)
    df = df.dropna(subset=['Navn']).reset_index(drop=True)
    
    # 5. Fjern dubletter af spillere (stopper "duplicate keys" fejlen)
    df = df.drop_duplicates(subset=['Navn'], keep='first')
    
    # 6. Formater taktiske kolonner og rens for .0
    for col in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        if col not in df.columns: df[col] = "0"
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0').str.strip()
    
    # 7. Dato-konvertering (Håndterer både YYYY-MM-DD og DD/MM/YYYY)
    if 'KONTRAKT' in df.columns:
        df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=False, errors='coerce').dt.date
    
    # 8. Skyggehold logik
    if 'SKYGGEHOLD' in df.columns:
        df['SKYGGEHOLD'] = df['SKYGGEHOLD'].fillna(False).replace(
            {'True':True, 'False':False, '1':True, '0':False, 1:True, 0:False, 'TRUE':True, 'FALSE':False}
        ).astype(bool)
    else:
        df['SKYGGEHOLD'] = False
        
    df['KLUB'] = 'Hvidovre IF' if is_hif else df.get('KLUB', '-')
    
    return df.reset_index(drop=True)

# --- APP ---
def vis_side():
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    e_c, e_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    df_emner = prepare_df(e_c)
    df_hif = prepare_df(h_c, is_hif=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # Lister (Emner & HIF)
    for t, d, s, p in [(t1, df_emner, e_s, EMNE_PATH), (t2, df_hif, h_s, HIF_PATH)]:
        with t:
            if d.empty: continue
            h = min(len(d) * 35 + 40, 500)
            # RETTET: Kolonnenavne her skal matche dem i prepare_df (STORE BOGSTAVER)
            ed = st.data_editor(
                d[['POS', 'Navn', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, use_container_width=True, height=h, key=f"ed_{p}",
                column_config={
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys()), width="small"),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                }, disabled=['Navn', 'KLUB']
            )
            
            # Gem ændringer
            if not ed['SKYGGEHOLD'].equals(d['SKYGGEHOLD']) or not ed['POS'].equals(d['POS']):
                for idx in ed.index:
                    name = d.iloc[idx]['Navn']
                    d.loc[d['Navn'] == name, ['SKYGGEHOLD', 'POS']] = [ed.iloc[idx]['SKYGGEHOLD'], ed.iloc[idx]['POS']]
                push_to_github(p, "Update", d.to_csv(index=False), s)
                st.rerun()

    # Skyggeliste
    with t3:
        df_s = pd.concat([df_emner[df_emner['SKYGGEHOLD']], df_hif[df_hif['SKYGGEHOLD']]], ignore_index=True)
        if not df_s.empty:
            h = min(len(df_s) * 35 + 40, 600)
            ed_s = st.data_editor(
                df_s[['Navn', 'POS_343', 'POS_433', 'POS_352', 'KONTRAKT']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, use_container_width=True, height=h,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY", disabled=True)
                }, disabled=['Navn']
            )
            # Gem taktiske ændringer
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_s[['POS_343', 'POS_433', 'POS_352']]):
                for _, row in ed_s.iterrows():
                    for src, p, sh in [(df_emner, EMNE_PATH, e_s), (df_hif, HIF_PATH, h_s)]:
                        if row['Navn'] in src['Navn'].values:
                            src.loc[src['Navn'] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                            push_to_github(p, "Tactical", src.to_csv(index=False), sh)
                st.rerun()

    # Banevisning (Bliver nu også styret af KONTRAKT)
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
