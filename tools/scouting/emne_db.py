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
    df = df.rename(columns={'NAVN': 'Navn', 'POS': 'POS', 'KONTRAKT': 'Kontrakt'})
    
    # Rens navne for at undgå dublet-fejl i mapping
    df['Navn'] = df['Navn'].astype(str).str.strip()
    
    # Konverter datoer
    df['Kontrakt'] = pd.to_datetime(df['Kontrakt'], dayfirst=True, errors='coerce').dt.date
    
    # Sikr formations-kolonner og rens dem for .0
    for col in ['POS_343', 'POS_433', 'POS_352', 'POS']:
        if col not in df.columns:
            df[col] = "0"
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace('nan', '0')
            
    col_name = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    df['Skyggehold'] = df[col_name].fillna(False).replace({'True':True,'False':False,'1':True,'0':False,1:True,0:False}).astype(bool) if col_name else False
    df['Klub'] = 'Hvidovre IF' if is_hif else df.get('Klub', '-')
    return df

def tegn_spiller_tabel(df_input, key_suffix, sha, path):
    if df_input.empty: return
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
    
    if not ed_res['🛡️'].equals(df_temp['🛡️']) or not ed_res['POS'].equals(df_temp['POS']):
        df_save = df_input.copy()
        df_save['Skyggehold'] = ed_res['🛡️'].values
        df_save['POS'] = ed_res['POS'].values
        df_save['Kontrakt'] = pd.to_datetime(df_input['Kontrakt']).dt.strftime('%d-%m-%Y')
        push_to_github(path, "Update Players", df_save.to_csv(index=False), sha)
        st.rerun()

# --- HOVEDSIDE ---
def vis_side(dp=None):
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
    
    emne_c, emne_s = get_github_file(EMNE_PATH)
    h_c, h_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(emne_c)
    df_hif = prepare_df(h_c, is_hif=True)

    t_emner, t_hif, t_liste, t_bane = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    with t_emner: tegn_spiller_tabel(df_emner, "emner", emne_s, EMNE_PATH)
    with t_hif: tegn_spiller_tabel(df_hif, "hif", h_s, HIF_PATH)

    # Samling af skyggehold - ignore_index=True løser "duplicate keys" fejlen
    s_e = df_emner[df_emner['Skyggehold']].copy()
    s_h = df_hif[df_hif['Skyggehold']].copy()
    df_samlet = pd.concat([s_e, s_h], ignore_index=True)

    with t_liste:
        if not df_samlet.empty:
            st.subheader("Konfigurer positioner (Dropdown)")
            cols_to_show = ['Navn', 'POS_343', 'POS_433', 'POS_352', 'Kontrakt']
            calc_height = (len(df_samlet) + 2) * 35 + 50
            
            # Editor med de 3 dropdown kolonner
            ed_skygge = st.data_editor(
                df_samlet[cols_to_show].style.apply(style_kontrakt_kolonne, axis=None),
                hide_index=True, use_container_width=True, height=calc_height,
                key="editor_skyggeliste_final",
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("Pos 3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("Pos 4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("Pos 3-5-2", options=list(POS_OPTIONS.keys())),
                    "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD.MM.YYYY", disabled=True)
                },
                disabled=['Navn']
            )
            
            # Tjek ændringer og gem
            changed = False
            for c in ['POS_343', 'POS_433', 'POS_352']:
                if not ed_skygge[c].equals(df_samlet[c]):
                    changed = True; break
            
            if changed:
                # Opdater de originale dataframes og gem
                for _, row in ed_skygge.iterrows():
                    name = row['Navn']
                    if name in df_emner['Navn'].values:
                        for c in ['POS_343', 'POS_433', 'POS_352']:
                            df_emner.loc[df_emner['Navn'] == name, c] = row[c]
                        save_df = df_emner.copy()
                        save_df['Kontrakt'] = pd.to_datetime(save_df['Kontrakt']).dt.strftime('%d-%m-%Y')
                        push_to_github(EMNE_PATH, "Update Pos", save_df.to_csv(index=False), emne_s)
                    elif name in df_hif['Navn'].values:
                        for c in ['POS_343', 'POS_433', 'POS_352']:
                            df_hif.loc[df_hif['Navn'] == name, c] = row[c]
                        save_df = df_hif.copy()
                        save_df['Kontrakt'] = pd.to_datetime(save_df['Kontrakt']).dt.strftime('%d-%m-%Y')
                        push_to_github(HIF_PATH, "Update Pos", save_df.to_csv(index=False), h_s)
                st.rerun()
        else:
            st.info("Vælg spillere i 'Emner' eller 'Hvidovre IF' først.")

    with t_bane:
        if not df_samlet.empty:
            active_f = st.session_state.form_skygge
            p_col = f"POS_{active_f.replace('-', '')}"
            col_pitch, col_menu = st.columns([6, 1])
            with col_menu:
                for f in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(f, key=f"b_{f}", use_container_width=True, type="primary" if active_f == f else "secondary"):
                        st.session_state.form_skygge = f
                        st.rerun()
            with col_pitch:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(11, 8))
                if active_f == "3-4-3": pos_map = {1:(10,40,'MM'), 4:(33,22,'VCB'), 3.5:(33,40,'CB'), 3:(33,58,'HCB'), 5:(60,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(60,70,'HWB'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                elif active_f == "4-3-3": pos_map = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(33,25,'VCB'), 3:(33,55,'HCB'), 2:(35,70,'HB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                else: pos_map = {1:(10,40,'MM'), 4:(33,22,'VCB'), 3.5:(33,40,'CB'), 3:(33,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(100,28,'ANG'), 7:(100,52,'ANG')}
                
                for p_num, (x, y, label) in pos_map.items():
                    ax.text(x, y-4.5, f" {label} ", size=9, color="white", fontweight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    sp = df_samlet[df_samlet[p_col].astype(str) == str(p_num)].sort_values(by='Navn')
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
