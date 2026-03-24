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

def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    
    # Standardisering af Navn
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    # Synkronisering af Positionstal (POS = Pos_Tal)
    if is_hif and 'POS' in df.columns:
        df['Pos_Tal'] = df['POS']
    
    # Standardisering af Skyggehold kolonne
    col_name = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    if col_name:
        df['Skyggehold'] = df[col_name].fillna(False).replace({'True': True, 'False': False, '1': True, '0': False, 1: True, 0: False})
        df['Skyggehold'] = df['Skyggehold'].astype(bool)
        if col_name != 'Skyggehold': df = df.drop(columns=[col_name])
    else:
        df['Skyggehold'] = False
    
    if is_hif: df['Klub'] = 'Hvidovre IF'
    return df

def tegn_spiller_tabel(df_input, key_suffix, sha, path, kan_slettes=True):
    df_temp = df_input.copy()
    df_temp['ℹ️'] = False
    df_temp = df_temp.rename(columns={'Skyggehold': '🛡️'})
    
    # Definer kolonnerne for de to forskellige kilder
    if kan_slettes: # Emner
        data_cols = ['Navn', 'Position', 'Klub', 'Pos_Tal', 'Pos_Prioritet', 'Prioritet', 'Lon', 'Kontrakt']
    else: # Hvidovre IF
        # Mapper dine specifikke HIF-kolonner (ROLECODE3 er Position, POS er Pos_Tal)
        data_cols = ['Navn', 'ROLECODE3', 'POS', 'PRIOR', 'CONTRACT']
    
    present_cols = [c for c in data_cols if c in df_temp.columns]
    display_cols = ['ℹ️'] + present_cols + (['🛡️', '🗑️'] if kan_slettes else ['🛡️'])
    if kan_slettes: df_temp['🗑️'] = False

    ed_res = st.data_editor(
        df_temp[display_cols], 
        hide_index=True, 
        use_container_width=True, 
        key=f"ed_{key_suffix}",
        column_config={
            "ℹ️": st.column_config.CheckboxColumn("Info", width="small"),
            "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
            "🗑️": st.column_config.CheckboxColumn("Slet", width="small"),
            "POS": st.column_config.NumberColumn("POS", format="%d", width="small"),
            "Pos_Tal": st.column_config.NumberColumn("POS", format="%d", width="small")
        },
        disabled=present_cols
    )

    if not ed_res['🛡️'].equals(df_temp['🛡️']):
        for idx, row in ed_res.iterrows():
            df_input.loc[df_input['Navn'] == row['Navn'], 'Skyggehold'] = row['🛡️']
        push_to_github(path, "Opdateret Skygge-status", df_input.to_csv(index=False), sha)
        st.rerun()

# --- HOVEDSIDE ---
def vis_side(dp):
    emne_c, emne_s = get_github_file(EMNE_PATH)
    hif_c, hif_s = get_github_file(HIF_PATH)
    
    df_emner = prepare_df(emne_c, is_hif=False)
    df_hif = prepare_df(hif_c, is_hif=True)

    t_emner, t_hif, t_liste, t_bane = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    with t_emner:
        tegn_spiller_tabel(df_emner, "emner", emne_s, EMNE_PATH, True)

    with t_hif:
        tegn_spiller_tabel(df_hif, "hif", hif_s, HIF_PATH, False)

    # Samlet data (POS/Pos_Tal er nu ensrettet i prepare_df)
    s_e = df_emner[df_emner['Skyggehold'] == True].copy() if not df_emner.empty else pd.DataFrame()
    s_h = df_hif[df_hif['Skyggehold'] == True].copy() if not df_hif.empty else pd.DataFrame()
    
    # Sørg for at liste-kolonnerne matcher for concat
    df_samlet = pd.concat([s_e, s_h], ignore_index=True)

    with t_liste:
        if not df_samlet.empty:
            # Vælg de bedste kolonner til den samlede oversigt
            vis_cols = ['Navn', 'ROLECODE3', 'POS', 'PRIOR', 'CONTRACT']
            if 'CONTRACT' in df_samlet.columns: # Hvis HIF kontraktnavn findes
                df_samlet['Kontrakt'] = df_samlet['Kontrakt'].fillna(df_samlet['CONTRACT'])
            
            st.dataframe(
                df_samlet[[c for c in vis_cols if c in df_samlet.columns]].sort_values('Pos_Tal'), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Ingen spillere valgt til skyggeholdet.")

    with t_bane:
        if not df_samlet.empty:
            col_pitch, col_menu = st.columns([6, 1])
            
            with col_menu:
                st.write("**Formation**")
                if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"
                for f in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(f, use_container_width=True, type="primary" if st.session_state.form_skygge == f else "secondary"):
                        st.session_state.form_skygge = f
                        st.rerun()

            with col_pitch:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(11, 8))
                
                form = st.session_state.form_skygge
                if form == "4-3-3":
                    pos_map = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(33,25,'VCB'), 3:(33,55,'HCB'), 2:(35,70,'HB'), 
                               6:(50,40,'DM'), 8:(68,25,'VCM'), 10:(68,55,'HCM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
                elif form == "3-4-3":
                    pos_map = {1:(10,40,'MM'), 4:(33,20,'VCB'), 3:(33,40,'CB'), 2:(33,60,'HCB'), 5:(60,10,'VWB'), 
                               6:(60,30,'DM'), 8:(60,50,'DM'), 7:(60,70,'HWB'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 10:(85,65,'HW')}
                else: # 3-5-2
                    pos_map = {1:(10,40,'MM'), 4:(33,20,'VCB'), 3:(33,40,'CB'), 2:(33,60,'HCB'), 5:(60,10,'VWB'), 
                               6:(60,40,'DM'), 7:(60,70,'HWB'), 8:(75,25,'CM'), 10:(75,55,'CM'), 11:(100,30,'ANG'), 9:(100,50,'ANG')}

                for p_num, (x, y, label) in pos_map.items():
                    ax.text(x, y-4, label, color="white", size=8, fontweight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    
                    # Da POS og Pos_Tal er ensrettet, bruger vi Pos_Tal til filtrering
                    spillere = df_samlet[df_samlet['Pos_Tal'].astype(float) == float(p_num)]
                    for i, (_, p) in enumerate(spillere.iterrows()):
                        bg_color = "#ffebee" if p['Klub'] == 'Hvidovre IF' else "#f1f8e9"
                        ax.text(x, y + (i*3.5), p['Navn'], size=7.5, ha='center', va='top', fontweight='bold',
                                bbox=dict(facecolor=bg_color, edgecolor='#333', boxstyle='square,pad=0.2', alpha=0.9))
                
                st.pyplot(fig)
        else:
            st.info("Tilføj spillere til skyggeholdet via de andre faner.")
