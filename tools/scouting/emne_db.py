import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"  # Vi bruger nu kun denne som master
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Ingen", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

# --- GITHUB HJÆLPERE ---
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
    if 'KONTRAKT' in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, 'KONTRAKT']
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183: styler.at[idx, 'KONTRAKT'] = 'background-color: #ffcccc; color: black;'
                elif days <= 365: styler.at[idx, 'KONTRAKT'] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_all_data():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    
    df = pd.read_csv(StringIO(content))
    
    # Standardiser kolonner
    df.columns = [str(c).upper().strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    # Konverter datoer
    df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
    df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], errors='coerce').dt.date
    
    # Vigtigt: Drop dubletter så vi kun ser den nyeste scouting-rapport pr. spiller i oversigten
    # Men vi gemmer den fulde DF til når vi skal skrive tilbage til GitHub
    df_unique = df.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    
    # Rens taktik-kolonner
    for col in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        if col not in df_unique.columns: df_unique[col] = "0"
        df_unique[col] = df_unique[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0')
    
    df_unique['SKYGGEHOLD'] = df_unique['SKYGGEHOLD'].fillna(False).replace({'True':True, 'False':False, '1':True, '0':False, 1:True, 0:False}).astype(bool)
    
    return df_unique, df, sha

# --- HOVEDSIDE ---
def vis_side():
    st.title("Hvidovre IF - Scouting & Skyggehold")
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    # Hent data
    df_unique, df_full, sha = prepare_all_data()
    
    if df_unique.empty:
        st.error("Kunne ikke indlæse scouting_db.csv")
        return

    # Split i Emner og HIF
    df_hif = df_unique[df_unique['KLUB'] == 'Hvidovre IF'].copy()
    df_emner = df_unique[df_unique['KLUB'] != 'Hvidovre IF'].copy()

    t1, t2, t3, t4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # --- TAB 1 & 2: LISTER ---
    for tab, data, label in [(t1, df_emner, "emne"), (t2, df_hif, "hif")]:
        with tab:
            st.subheader(f"Oversigt: {label.upper()}")
            h = min(len(data) * 35 + 45, 500)
            
            ed = st.data_editor(
                data[['POS', 'Navn', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, use_container_width=True, height=h, key=f"ed_{label}",
                column_config={
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys()), width="small"),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                }, disabled=['Navn', 'KLUB']
            )
            
            # Gem ændringer (SKYGGEHOLD eller POS)
            if not ed['SKYGGEHOLD'].equals(data['SKYGGEHOLD']) or not ed['POS'].equals(data['POS']):
                for idx, row in ed.iterrows():
                    navn = row['Navn']
                    # Opdater alle rækker i master-filen for denne spiller
                    df_full.loc[df_full['Navn'] == navn, ['SKYGGEHOLD', 'POS']] = [row['SKYGGEHOLD'], row['POS']]
                
                push_to_github(DB_PATH, "Update Skygge/Pos", df_full.to_csv(index=False), sha)
                st.success("Ændringer gemt!")
                st.rerun()

    # --- TAB 3: SKYGGELISTE (TAKTISK) ---
    with t3:
        st.subheader("Taktisk vurdering af Skyggehold")
        df_s = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        
        if not df_s.empty:
            h_s = min(len(df_s) * 35 + 45, 600)
            ed_s = st.data_editor(
                df_s[['Navn', 'POS_343', 'POS_433', 'POS_352', 'KONTRAKT']].style.apply(style_kontrakt, axis=None), 
                hide_index=True, use_container_width=True, height=h_s,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY", disabled=True)
                }, disabled=['Navn']
            )
            
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_s[['POS_343', 'POS_433', 'POS_352']]):
                for _, row in ed_s.iterrows():
                    df_full.loc[df_full['Navn'] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                
                push_to_github(DB_PATH, "Update Tactical POS", df_full.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Marker spillere som 'Skygge' i oversigten for at se dem her.")

    # --- TAB 4: BANEVISNING ---
    with t4:
        df_pitch = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        if not df_pitch.empty:
            f = st.session_state.form_skygge
            p_col = f"POS_{f.replace('-', '')}"
            
            c_p, c_m = st.columns([5, 1])
            with c_m:
                st.write("**System**")
                for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(opt, key=f"btn_{opt}", use_container_width=True, type="primary" if f == opt else "secondary"):
                        st.session_state.form_skygge = opt
                        st.rerun()
            
            with c_p:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(9, 6))
                
                # Koordinater for labels
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=7, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_pitch[df_pitch[p_col].astype(str) == str(pid)]
                    for i, (_, p) in enumerate(players.iterrows()):
                        bg = "white"
                        if pd.notna(p['KONTRAKT']):
                            diff = (p['KONTRAKT'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        ax.text(x, y+(i*3.5), p['Navn'], size=7, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor='#333', alpha=0.9, boxstyle='square,pad=0.1'))
                st.pyplot(fig)
        else:
            st.info("Ingen spillere valgt til skyggehold.")

if __name__ == "__main__":
    vis_side()
