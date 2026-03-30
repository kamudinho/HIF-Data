import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv" # NU KUN ÉN FIL
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Vælg", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
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
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
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

def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    
    # Rens kolonner
    df.columns = [str(c).upper().strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    # Tag kun den nyeste rapport pr. spiller
    df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
    df = df.sort_values('DATO', ascending=False).drop_duplicates('Navn')

    # Standardiser typer
    for col in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        if col not in df.columns: df[col] = "0"
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0')

    df['KONTRAKT'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce').dt.date
    df['SKYGGEHOLD'] = df['SKYGGEHOLD'].astype(str).str.strip().str.upper() == 'TRUE'
    
    return df

# --- APP ---
def vis_side():
    st.set_page_config(page_title="HIF Scouting", layout="wide")
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, sha = get_github_file(DB_PATH)
    df_all = prepare_df(content)

    if df_all.empty:
        st.error("Kunne ikke finde data i scouting_db.csv")
        return

    # Opdel data internt
    mask_hif = df_all['KLUB'].astype(str).str.contains("Hvidovre", case=False, na=False)
    df_hif = df_all[mask_hif]
    df_emner = df_all[~mask_hif]
    df_skygge = df_all[df_all['SKYGGEHOLD']]

    tab1, tab2, tab3, tab4 = st.tabs(["Emner", "Hvidovre IF", "📋 Skyggeliste", "🏟️ Bane"])

    # Tab 1 & 2: Lister
    for t, data, title in [(tab1, df_emner, "Emner"), (tab2, df_hif, "Hvidovre IF")]:
        with t:
            st.subheader(title)
            h = min(len(data) * 35 + 45, 500)
            ed = st.data_editor(
                data[['POS', 'Navn', 'KLUB', 'KONTRAKT', 'SKYGGEHOLD']].style.apply(style_kontrakt, axis=None),
                hide_index=True, use_container_width=True, height=h, key=f"ed_{title}",
                column_config={
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge"),
                    "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY")
                }, disabled=['Navn', 'KLUB']
            )
            
            # Gem hvis Skygge/Pos ændres
            if not ed['SKYGGEHOLD'].equals(data['SKYGGEHOLD']) or not ed['POS'].equals(data['POS']):
                # Her skal vi være forsigtige: Vi opdaterer den RÅ dataframe og gemmer alt
                raw_content, raw_sha = get_github_file(DB_PATH)
                df_to_save = pd.read_csv(StringIO(raw_content))
                for idx, row in ed.iterrows():
                    name = data.iloc[idx]['Navn']
                    df_to_save.loc[df_to_save['Navn'] == name, ['SKYGGEHOLD', 'POS']] = [row['SKYGGEHOLD'], row['POS']]
                push_to_github(DB_PATH, "Update Status", df_to_save.to_csv(index=False), raw_sha)
                st.rerun()

    # Tab 3: Skyggeliste (Taktik)
    with tab3:
        if not df_skygge.empty:
            ed_s = st.data_editor(
                df_skygge[['Navn', 'POS_343', 'POS_433', 'POS_352', 'KONTRAKT']].style.apply(style_kontrakt, axis=None),
                hide_index=True, use_container_width=True,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys())),
                    "KONTRAKT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY", disabled=True)
                }, disabled=['Navn']
            )
            
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_skygge[['POS_343', 'POS_433', 'POS_352']]):
                raw_content, raw_sha = get_github_file(DB_PATH)
                df_to_save = pd.read_csv(StringIO(raw_content))
                for _, row in ed_s.iterrows():
                    df_to_save.loc[df_to_save['Navn'] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                push_to_github(DB_PATH, "Update Taktik", df_to_save.to_csv(index=False), raw_sha)
                st.rerun()

    # Tab 4: Banevisning
    with tab4:
        if not df_skygge.empty:
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
                
                # Formationer
                if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
                elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

                for pid, (x, y, lbl) in m.items():
                    ax.text(x, y-4, lbl, size=7, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    players = df_skygge[df_skygge[p_col].astype(str) == str(pid)]
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
