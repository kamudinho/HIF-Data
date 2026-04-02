import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 
GUL_ADVARSEL = "#ffff99" # Til 6-12 mdr.

VINDUE_OPTIONS_GLOBAL = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

# --- 2. GITHUB FUNKTIONER ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except:
        pass
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- 3. DATA PROCESSING ---
def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    if 'Navn' not in df.columns: return pd.DataFrame()
    df = df.dropna(subset=['Navn'])
    df['Navn'] = df['Navn'].astype(str).str.strip()
    
    if 'TRANSFER_VINDUE' in df.columns:
        df['TRANSFER_VINDUE'] = df['TRANSFER_VINDUE'].replace(['Nu', 'nu', 'NU'], 'Nuværende trup').fillna("Sommer 26")
    
    for c in ['ER_EMNE', 'SKYGGEHOLD']:
        if c not in df.columns: df[c] = False
        else:
            b_map = {True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, 'TRUE':True, 'FALSE':False}
            df[c] = df[c].map(b_map).fillna(False)
    
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        if c not in df.columns: df[c] = "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace(['nan', 'None', ''], '0').str.strip()
    
    df['IS_HIF'] = is_hif
    return df

# --- 4. HOVEDFUNKTION (VISNING) ---
def vis_side():
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 40px !important; } 
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
            [data-testid="stVerticalBlock"] > div:first-child { margin-top: 0rem !important; }
            div[data-testid="stSelectbox"] > label { display: none !important; }
            .stTabs { margin-top: -45px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: 
        st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)
    df_all = pd.concat([df_scout, df_hif], ignore_index=True)

    col_empty, col_v = st.columns([4, 1])
    with col_v:
        sel_v = st.selectbox("Vindue", VINDUE_OPTIONS_GLOBAL, key="global_v_sel", index=1, label_visibility="collapsed")

    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # (Tab 1, 2 og 3 koden er uændret...)
    with tabs[0]:
        if not df_scout[df_scout['ER_EMNE']==True].empty:
            st.data_editor(df_scout[df_scout['ER_EMNE']==True].set_index('Navn')[['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']], use_container_width=True, height=400, key="ed_E")
    
    with tabs[1]:
        if not df_hif.empty:
            st.data_editor(df_hif.set_index('Navn')[['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']], use_container_width=True, height=400, key="ed_H")

    # --- TAB 4: Bane med Legends ---
    with tabs[3]:
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        if sel_v == "Nuværende trup":
            df_f = df_hif.drop_duplicates(subset=['Navn'])
        else:
            h_s = df_hif[df_hif['SKYGGEHOLD'] == True]
            e_s = df_scout[(df_scout['SKYGGEHOLD'] == True) & (df_scout['TRANSFER_VINDUE'] == sel_v)]
            df_f = pd.concat([h_s, e_s], ignore_index=True).drop_duplicates(subset=['Navn'])

        c_p, c_m = st.columns([9, 1])
        with c_m:
            for o in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(o, key=f"btn_{o}", use_container_width=True, type="primary" if f == o else "secondary"):
                    st.session_state.form_skygge = o
                    st.rerun()

        with c_p:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 7)) # Øget højde lidt til legends
            fig.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.95)
            
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(55,10,'VWB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "2":(55,70,'HWB'), "11":(80,15,'VW'), "9":(100,40,'ANG'), "7":(80,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,10,'VB'), "4":(30,25,'VCB'), "3":(30,55,'HCB'), "2":(35,70,'HB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "10":(75,40,'CM'), "11":(85,15,'VW'), "9":(100,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(45,10,'VWB'), "6":(60,30,'DM'), "8":(60,50,'DM'), "2":(45,70,'HWB'), "10":(75,40,'CM'), "9":(95,32,'ANG'), "7":(95,48,'ANG')}}[f]

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)]
                for i, (_, p_row) in enumerate(plist.iterrows()):
                    # Farvelogik
                    bg_color = "white"
                    if p_row['IS_HIF'] == False:
                        bg_color = GRON_NY
                    # EKSEMPEL: Hvis du har en 'KONTRAKT_REST' kolonne (i måneder)
                    # elif p_row.get('KONTRAKT_REST', 24) < 6: bg_color = "#ffcccc" (Rød)
                    # elif p_row.get('KONTRAKT_REST', 24) <= 12: bg_color = GUL_ADVARSEL
                    
                    ax.text(x, y + (i * 2.5), p_row['Navn'], size=7, ha='center', va='center', weight='bold', 
                            bbox=dict(facecolor=bg_color, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2'))

            # --- LEGENDS (Venstre side) ---
            ax.text(2, -5, "LEGEND:", size=8, weight='bold', ha='left')
            ax.text(12, -5, "Ny Transfer", size=7, bbox=dict(facecolor=GRON_NY, edgecolor='#333', boxstyle='square,pad=0.2'))
            ax.text(28, -5, "6-12 mdr.", size=7, bbox=dict(facecolor=GUL_ADVARSEL, edgecolor='#333', boxstyle='square,pad=0.2'))
            ax.text(42, -5, "< 6 mdr.", size=7, bbox=dict(facecolor="#ffcccc", edgecolor='#333', boxstyle='square,pad=0.2'))

            # --- VINDUE TITEL (Højre side) ---
            ax.text(118, -5, f"Vindue: {sel_v}", size=9, weight='bold', ha='right', color=HIF_ROD)
            
            st.pyplot(fig, bbox_inches='tight', pad_inches=0.1)

if __name__ == "__main__":
    vis_side()
