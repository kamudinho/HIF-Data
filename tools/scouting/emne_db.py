import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
EMNE_PATH = "data/emneliste.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

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

# --- HJÆLPEFUNKTION: Rens og klargør DataFrame ---
def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    
    # Standardisér Navn
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    # VIGTIGT: Håndtering af Skyggehold kolonne
    # Vi tjekker både 'Skyggehold' og 'skyggehold'
    col_name = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    
    if col_name:
        # Konverter eksisterende kolonne til rene booleans
        df['Skyggehold'] = df[col_name].fillna(False).replace({'True': True, 'False': False, '1': True, '0': False, 1: True, 0: False})
        df['Skyggehold'] = df['Skyggehold'].astype(bool)
        if col_name != 'Skyggehold': df = df.drop(columns=[col_name])
    else:
        df['Skyggehold'] = False
        
    return df

# --- HJÆLPEFUNKTION: TEGN SPILLER TABEL ---
def tegn_spiller_tabel(df_input, key_suffix, sha, path, kan_slettes=True):
    df_temp = df_input.copy()
    df_temp['ℹ️'] = False
    
    # Omdøb til display (Emoji)
    df_temp = df_temp.rename(columns={'Skyggehold': '🛡️'})
    
    data_cols = ['Navn', 'Position', 'Klub', 'Pos_Tal', 'Pos_Prioritet', 'Prioritet', 'Lon', 'Kontrakt']
    present_cols = [c for c in data_cols if c in df_temp.columns]
    
    if kan_slettes:
        df_temp['🗑️'] = False
        display_cols = ['ℹ️'] + present_cols + ['🛡️', '🗑️']
    else:
        display_cols = ['ℹ️'] + present_cols + ['🛡️']

    ed_res = st.data_editor(
        df_temp[display_cols],
        column_config={
            "ℹ️": st.column_config.CheckboxColumn("Info", width="small"),
            "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
            "🗑️": st.column_config.CheckboxColumn("Slet", width="small"),
            "Pos_Tal": "POS"
        },
        disabled=present_cols,
        hide_index=True,
        use_container_width=True,
        key=f"ed_{key_suffix}"
    )

    # Gem logik
    if not ed_res['🛡️'].equals(df_temp['🛡️']):
        for idx, row in ed_res.iterrows():
            name_val = row['Navn']
            df_input.loc[df_input['Navn'] == name_val, 'Skyggehold'] = row['🛡️']
        push_to_github(path, "Update Skygge", df_input.to_csv(index=False), sha)
        st.rerun()

# --- HOVEDSIDE ---
def vis_side(dp):
    emne_c, emne_s = get_github_file(EMNE_PATH)
    hif_c, hif_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(emne_c)
    df_hif = prepare_df(hif_c)

    t_emner, t_hif, t_liste, t_bane = st.tabs(["🔍 Emner", "🔴 Hvidovre IF", "📋 Skyggeliste", "🏟️ Skyggehold"])

    with t_emner:
        if not df_emner.empty:
            tegn_spiller_tabel(df_emner, "emner", emne_s, EMNE_PATH, kan_slettes=True)

    with t_hif:
        if not df_hif.empty:
            tegn_spiller_tabel(df_hif, "hif", hif_s, HIF_PATH, kan_slettes=False)

    # Samlet liste til bane og oversigt
    s_e = df_emner[df_emner['Skyggehold'] == True] if 'Skyggehold' in df_emner.columns else pd.DataFrame()
    s_h = df_hif[df_hif['Skyggehold'] == True] if 'Skyggehold' in df_hif.columns else pd.DataFrame()
    if not s_h.empty: s_h['Klub'] = 'Hvidovre IF'
    df_samlet = pd.concat([s_e, s_h], ignore_index=True)

    with t_liste:
        if not df_samlet.empty:
            st.dataframe(df_samlet[['Pos_Tal', 'Navn', 'Position', 'Klub']].sort_values('Pos_Tal'), use_container_width=True, hide_index=True)
        else:
            st.info("Listen er tom.")

    with t_bane:
        if not df_samlet.empty:
            # Her kan du indsætte din Pitch-kode fra før
            st.write("Banen tegnes her baseret på df_samlet...")
