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
    
    # ENSRET KOLONNENAVNE (Gør dem ens for begge filer)
    rename_map = {
        'NAVN': 'Navn',
        'POS': 'POS',
        'CONTRACT': 'Kontrakt',
        'ROLECODE3': 'Position'
    }
    df = df.rename(columns=rename_map)

    # SIKR POS_TAL FINDES
    if 'POS' not in df.columns:
        df['POS'] = 0
    
    # ENSRET SKYGGEHOLD
    col_name = next((c for c in df.columns if c.lower() == 'skyggehold'), None)
    if col_name:
        df['Skyggehold'] = df[col_name].fillna(False).replace({'True': True, 'False': False, '1': True, '0': False, 1: True, 0: False})
        df['Skyggehold'] = df['Skyggehold'].astype(bool)
    else:
        df['Skyggehold'] = False
    
    if is_hif: 
        df['Klub'] = 'Hvidovre IF'
    elif 'Klub' not in df.columns:
        df['Klub'] = 'Ukendt'
        
    return df

def tegn_spiller_tabel(df_input, key_suffix, sha, path, kan_slettes=True):
    if df_input.empty:
        st.info("Ingen data tilgængelig.")
        return

    df_temp = df_input.copy()
    df_temp['ℹ️'] = False
    df_temp = df_temp.rename(columns={'Skyggehold': '🛡️'})
    
    # Hvilke kolonner vil vi gerne vise?
    desired_cols = ['Navn', 'Position', 'Klub', 'POS', 'Kontrakt', '🛡️']
    if kan_slettes: df_temp['🗑️'] = False; desired_cols.append('🗑️')
    
    # Vi viser kun de kolonner der rent faktisk findes i DF
    present_cols = [c for c in desired_cols if c in df_temp.columns]
    display_cols = ['ℹ️'] + present_cols

    ed_res = st.data_editor(
        df_temp[display_cols], 
        hide_index=True, 
        use_container_width=True, 
        key=f"ed_{key_suffix}",
        column_config={
            "ℹ️": st.column_config.CheckboxColumn("Info", width="small"),
            "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
            "🗑️": st.column_config.CheckboxColumn("Slet", width="small"),
            "POS": st.column_config.NumberColumn("POS", format="%d", width="small")
        },
        disabled=[c for c in present_cols if c not in ['🛡️', '🗑️']]
    )

    # Gem ændringer hvis '🛡️' ændres
    if not ed_res['🛡️'].equals(df_temp['🛡️']):
        for idx, row in ed_res.iterrows():
            df_input.loc[df_input['Navn'] == row['Navn'], 'Skyggehold'] = row['🛡️']
        push_to_github(path, "Update Skygge", df_input.to_csv(index=False), sha)
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

    # Samlet data til Skyggelisten
    s_e = df_emner[df_emner['Skyggehold'] == True].copy()
    s_h = df_hif[df_hif['Skyggehold'] == True].copy()
    df_samlet = pd.concat([s_e, s_h], ignore_index=True)

    with t_liste:
        if not df_samlet.empty:
            vis_cols = ['Navn', 'Position', 'Klub', 'POS', 'Kontrakt']
            st.dataframe(
                df_samlet[[c for c in vis_cols if c in df_samlet.columns]].sort_values('POS'), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Ingen spillere valgt til skyggehold.")

    with t_bane:
        if not df_samlet.empty:
            # --- 1. KONSTANTER & FARVER ---
            HIF_ROD = "#df003b"
            GUL_UDLOB = "#ffffcc"
            ROD_UDLOB = "#ffcccc"
            LEJE_GRA = "#d3d3d3"
            idag = datetime.now()

            col_pitch, col_menu = st.columns([6, 1])
            
            with col_menu:
                st.write("**Formation**")
                if 'form_skygge' not in st.session_state: 
                    st.session_state.form_skygge = "3-4-3"
                
                for f in ["3-4-3", "4-3-3", "3-5-2"]:
                    is_active = st.session_state.form_skygge == f
                    if st.button(f, key=f"btn_skygge_{f}", use_container_width=True, 
                                 type="primary" if is_active else "secondary"):
                        st.session_state.form_skygge = f
                        st.rerun()

            with col_pitch:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
                fig, ax = pitch.draw(figsize=(11, 8))
                
                form = st.session_state.form_skygge

                # --- 2. DYNAMISK POS_CONFIG ---
                if form == "3-4-3":
                    pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                                  5: (60, 10, 'VWB'), 6: (60, 30, 'DM'), 8: (60, 50, 'DM'), 2: (60, 70, 'HWB'), 
                                  11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (85, 65, 'HW')}
                elif form == "4-3-3":
                    pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                                  6: (50, 40, 'DM'), 8: (68, 25, 'VCM'), 10: (68, 55, 'HCM'),
                                  11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (85, 65, 'HW')}
                else: # 3-5-2
                    pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                                  5: (60, 10, 'VWB'), 6: (60, 40, 'DM'), 2: (60, 70, 'HWB'), 
                                  8: (70, 25, 'CM'), 10: (70, 55, 'CM'), 9: (100, 28, 'ANG'), 7: (100, 52, 'ANG')}

                # --- 3. TEGN SPILLERE ---
                for p_num, (x, y, label) in pos_config.items():
                    ax.text(x, y - 4.5, f" {label} ", size=9, color="white", fontweight='bold', ha='center',
                            bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    
                    if form == "4-3-3" and p_num == 4:
                        spillere = df_samlet[df_samlet['POS'].astype(float).isin([4, 3.5])]
                    elif form == "3-5-2" and p_num == 9:
                        spillere = df_samlet[df_samlet['POS'].astype(float).isin([9, 11])]
                    else:
                        spillere = df_samlet[df_samlet['POS'].astype(float) == float(p_num)]

                    spillere = spillere.sort_values(by=['Navn'])

                    for i, (_, p) in enumerate(spillere.iterrows()):
                        bg_color = "white"
                        # Tjekker prioritering eller kontrakt
                        if str(p.get('Klub', '')).upper() != 'HVIDOVRE IF':
                            bg_color = "#f0f0f0" # Grålig for emner/eksterne
                        
                        if pd.notna(p.get('Kontrakt')):
                            try:
                                k_dato = pd.to_datetime(p['Kontrakt'], dayfirst=True)
                                dage_til = (k_dato - idag).days
                                if dage_til < 183: bg_color = ROD_UDLOB
                                elif dage_til <= 365: bg_color = GUL_UDLOB
                            except: pass
                        
                        ax.text(x, (y - 1.5) + (i * 3.8), f" {p['Navn']} ", size=8, ha='center', va='top', 
                                fontweight='bold',
                                bbox=dict(facecolor=bg_color, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))
                
                st.pyplot(fig)
        else:
            st.info("Ingen spillere valgt til skyggehold.")
