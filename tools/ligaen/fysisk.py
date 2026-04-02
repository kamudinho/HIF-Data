import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time
from datetime import datetime

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 
GUL_ADVARSEL = "#ffff99" 
ROD_ADVARSEL = "#ffcccc" 
LEJE_GRA = "#d3d3d3"

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
    
    # --- NY OMREGNING LOGIK ---
    # 1. MIN_SEC til rene minutter (f.eks. 5400 sek -> 90 min)
    if 'MIN_SEC' in df.columns:
        df['MINUTTER'] = pd.to_numeric(df['MIN_SEC'], errors='coerce') / 60
        df['MINUTTER'] = df['MINUTTER'].fillna(0).round(0)

    # 2. DISTANCE (meter) til KM
    if 'DISTANCE' in df.columns:
        df['DISTANCE_KM'] = pd.to_numeric(df['DISTANCE'], errors='coerce') / 1000
        df['DISTANCE_KM'] = df['DISTANCE_KM'].fillna(0).round(1)

    # Standardisering af vinduer og positioner
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
    
    # Kontrakt-udløb beregning
    df['IS_HIF'] = is_hif
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 40px !important; } 
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
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

    # Tab 1 & 2: Editorer
    for tab, source_df, p_path, k_base in [
        (tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "E"),
        (tabs[1], df_hif, HIF_PATH, "H")
    ]:
        with tab:
            if not source_df.empty:
                cols_to_show = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
                # Tilføj de nye beregnede kolonner til visning hvis de findes
                display_cols = cols_to_show + ([c for c in ['MINUTTER', 'DISTANCE_KM'] if c in source_df.columns])
                
                d_edit = source_df.set_index('Navn')[display_cols]
                st.data_editor(d_edit, use_container_width=True, height=500, key=f"ed_{k_base}")

    # Tab 3: Skyggeliste
    with tabs[2]:
        df_sky = df_all[df_all['SKYGGEHOLD'] == True].drop_duplicates(subset=['Navn'])
        if not df_sky.empty:
            d_sky_ed = df_sky.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']]
            st.data_editor(d_sky_ed, use_container_width=True, height=500, key="sky_ed_final")

    # Tab 4: Bane (Med rettet Legends og Vindue)
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
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98) 
            
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[f]

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)].sort_values('PRIOR', ascending=True)
                for i, (_, p_row) in enumerate(plist.iterrows()):
                    bg = "white"
                    if p_row['IS_HIF'] == False: bg = GRON_NY
                    elif str(p_row.get('PRIOR', '')).upper() == 'L': bg = LEJE_GRA
                    else:
                        u_val = p_row.get('UDLØB') if pd.notna(p_row.get('UDLØB')) else p_row.get('KONTRAKT')
                        try:
                            days = (pd.to_datetime(u_val, dayfirst=True) - datetime.now()).days
                            if days < 183: bg = ROD_ADVARSEL
                            elif days <= 365: bg = GUL_ADVARSEL
                        except: bg = "white"
                    
                    ax.text(x, y + (i * 2.8), p_row['Navn'], size=7.5, ha='center', va='center', weight='bold', 
                            bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2', linewidth=0.5))

            # LEGENDS PLACERET PÅ BANEN
            ax.text(2, 2, " < 6 mdr ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=ROD_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(12, 2, " 6-12 mdr ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=GUL_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(25, 2, " Ny/Emne ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=GRON_NY, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(38, 2, " Leje ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=LEJE_GRA, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            
            # VINDUE TEKST
            ax.text(118, 2, f"Vindue: {sel_v}", size=9, weight='bold', ha='right', va='bottom', color=HIF_ROD)
            
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
