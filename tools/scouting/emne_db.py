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

# --- POSITIONSMULIGHEDER ---
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

# --- LOGIK ---
def style_kontrakt_kolonne(df):
    """ Farver KUN cellerne i kolonnen 'Kontrakt' baseret på udløb """
    styler = pd.DataFrame('', index=df.index, columns=df.columns)
    if 'Kontrakt' in df.columns:
        now = datetime.now().date()
        for idx in df.index:
            val = df.at[idx, 'Kontrakt']
            if pd.notna(val) and not isinstance(val, str):
                days = (val - now).days
                if days < 183:
                    styler.at[idx, 'Kontrakt'] = 'background-color: #ffcccc; color: black;'
                elif days <= 365:
                    styler.at[idx, 'Kontrakt'] = 'background-color: #ffffcc; color: black;'
    return styler

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df = df.rename(columns={'NAVN': 'Navn', 'POS': 'POS', 'KONTRAKT': 'Kontrakt'})
    
    # Konverter Kontrakt til date-objekter for at undgå String/Date mismatch fejl
    df['Kontrakt'] = pd.to_datetime(df['Kontrakt'], dayfirst=True, errors='coerce').dt.date
    
    # Sikr formations-kolonner
    for col in ['POS_343', 'POS_433', 'POS_352']:
        if col not in df.columns:
            df[col] = df['POS'].astype(str)
            
    df['POS'] = df['POS'].astype(str)
    col_name = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    if col_name:
        df['Skyggehold'] = df[col_name].fillna(False).replace({'True':True,'False':False,'1':True,'0':False,1:True,0:False}).astype(bool)
    else:
        df['Skyggehold'] = False
        
    df['Klub'] = 'Hvidovre IF' if is_hif else df.get('Klub', '-')
    return df

def tegn_spiller_tabel(df_input, key_suffix, sha, path):
    if df_input.empty:
        st.info("Ingen data fundet.")
        return
        
    df_temp = df_input.copy()
    df_temp = df_temp.rename(columns={'Skyggehold': '🛡️'})
    calc_height = (len(df_temp) + 2) * 35 + 45
    
    ed_res = st.data_editor(
        df_temp[['POS', 'Navn', 'Klub', 'Kontrakt', '🛡️']], 
        hide_index=True, use_container_width=True, height=calc_height, key=f"ed_{key_suffix}",
        column_config={
            "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
            "POS": st.column_config.SelectboxColumn("Pos", options=list(POS_OPTIONS.keys())),
            "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD.MM.YYYY")
        },
        disabled=['Navn', 'Klub']
    )
    
    # Tjek for ændringer
    if not ed_res['🛡️'].equals(df_temp['🛡️']) or not ed_res['POS'].equals(df_temp['POS']) or not ed_res['Kontrakt'].equals(df_temp['Kontrakt']):
        df_save = df_input.copy()
        df_save['Skyggehold'] = ed_res['🛡️'].values
        df_save['POS'] = ed_res['POS'].values
        # Konverter dato tilbage til streng før upload
        df_save['Kontrakt'] = pd.to_datetime(ed_res['Kontrakt']).dt.strftime('%d-%m-%Y')
        
        push_to_github(path, "Update Spillerdata", df_save.to_csv(index=False), sha)
        st.rerun()

# --- HOVEDSIDE ---
def vis_side():
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    emne_c, emne_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(emne_c)
    df_hif = prepare_df(h_c, is_hif=True)

    t_emner, t_hif, t_liste, t_bane = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    with t_emner: tegn_spiller_tabel(df_emner, "emner", emne_s, EMNE_PATH)
    with t_hif: tegn_spiller_tabel(df_hif, "hif", h_s, HIF_PATH)

    # Samlet skyggehold data
    s_e = df_emner[df_emner['Skyggehold'] == True]
    s_h = df_hif[df_hif['Skyggehold'] == True]
    df_samlet = pd.concat([s_e, s_h], ignore_index=True)

    active_form = st.session_state.form_skygge
    pos_col = f"POS_{active_form.replace('-', '')}"

    with t_liste:
        if not df_samlet.empty:
            st.subheader(f"Positioner for {active_form}")
            df_display = df_samlet[['Navn', pos_col, 'Klub', 'Kontrakt']].copy()
            calc_height = (len(df_display) + 2) * 35 + 45
            
            ed_skygge = st.data_editor(
                df_display.style.apply(style_kontrakt_kolonne, axis=None),
                hide_index=True, use_container_width=True, height=calc_height,
                column_config={
                    pos_col: st.column_config.SelectboxColumn(f"Position ({active_form})", options=list(POS_OPTIONS.keys())),
                    "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD.MM.YYYY")
                },
                disabled=['Navn', 'Klub', 'Kontrakt']
            )
            
            if not ed_skygge[pos_col].equals(df_display[pos_col]):
                for idx, row in ed_skygge.iterrows():
                    is_emne = row['Navn'] in df_emner['Navn'].values
                    target_df = df_emner if is_emne else df_hif
                    target_path = EMNE_PATH if is_emne else HIF_PATH
                    target_sha = emne_s if is_emne else h_s
                    
                    target_df.loc[target_df['Navn'] == row['Navn'], pos_col] = row[pos_col]
                    push_to_github(target_path, f"Update {pos_col}", target_df.to_csv(index=False), target_sha)
                st.rerun()
        else:
            st.info("Vælg spillere i 'Emner' eller 'Hvidovre IF' for at bygge din liste.")

    with t_bane:
        if not df_samlet.empty:
            col_pitch, col_menu = st.columns([6, 1])
            with col_menu:
                st.write("**Opstilling**")
                for f in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(f, key=f"btn_{f}", use_container_width=True, 
                                 type="primary" if active_form == f else "secondary"):
                        st.session_state.form_skygge = f
                        st.rerun()

            with col_pitch:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(11, 8))
                
                # Koordinater
                if active_form == "3-4-3": pos_map = {1:(10,40,'MM'), 4:(33,22,'VCB'), 3.5:(33,40,'CB'), 3:(33,58,'HCB'), 5:(60,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(60,70,'HWB'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                elif active_form == "4-3-3": pos_map = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(33,25,'VCB'), 3:(33,55,'HCB'), 2:(35,70,'HB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: pos_map = {1:(10,40,'MM'), 4:(33,22,'VCB'), 3.5:(33,40,'CB'), 3:(33,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(100,28,'ANG'), 7:(100,52,'ANG')}
                
                for p_num, (x, y, label) in pos_map.items():
                    ax.text(x, y-4.5, f" {label} ", size=9, color="white", fontweight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    
                    # Match spillere på den valgte formations position
                    sp = df_samlet[df_samlet[pos_col].astype(str) == str(p_num)].sort_values(by='Navn')
                    for i, (_, p) in enumerate(sp.iterrows()):
                        bg = "white"
                        if pd.notna(p['Kontrakt']):
                            diff = (p['Kontrakt'] - datetime.now().date()).days
                            if diff < 183: bg = "#ffcccc"
                            elif diff <= 365: bg = "#ffffcc"
                        
                        ax.text(x, (y-1.5)+(i*2.3), f" {p['Navn']} ", size=8, ha='center', va='top', fontweight='bold', bbox=dict(facecolor=bg, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
