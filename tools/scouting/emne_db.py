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
LEJE_GRA = "#e0e0e0"

# --- 2. HJÆLPEFUNKTIONER ---
def calculate_age_str(born):
    try:
        if pd.isna(born) or str(born).strip() in ["", "nan", "-"]: return "-"
        born_dt = pd.to_datetime(born, dayfirst=True, errors='coerce')
        if pd.isna(born_dt): return "-"
        today = datetime.now()
        age = today.year - born_dt.year - ((today.month, today.day) < (born_dt.month, born_dt.day))
        return str(int(age))
    except: return "-"

def get_color_by_date(val):
    try:
        if pd.isna(val) or str(val).strip() in ["", "-", "nan"]: return ""
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return ""
        days = (dt - datetime.now()).days
        if days < 183: return f'background-color: {ROD_ADVARSEL}'
        if days <= 365: return f'background-color: {GUL_ADVARSEL}'
        return ""
    except: return ""

def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except: pass
    return None, None

# --- 3. DATA PROCESSING ---
def prepare_df(content, is_hif=False):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    if 'Navn' not in df.columns: return pd.DataFrame()
    
    df = df.dropna(subset=['Navn'])
    
    # Alder som string for at kunne vise "-"
    if 'BIRTHDATE' in df.columns:
        df['Alder'] = df['BIRTHDATE'].apply(calculate_age_str)
    else:
        df['Alder'] = "-"

    # Rens dato-kolonner for visning
    k_col = 'UDLØB' if 'UDLØB' in df.columns else 'KONTRAKT'
    if k_col in df.columns:
        df[k_col] = df[k_col].fillna("-")

    if 'TRANSFER_VINDUE' in df.columns:
        df['TRANSFER_VINDUE'] = df['TRANSFER_VINDUE'].replace(['Nu', 'nu', 'NU'], 'Nuværende trup').fillna("Sommer 26")
    
    for c in ['ER_EMNE', 'SKYGGEHOLD']:
        if c not in df.columns: df[c] = False
        else:
            df[c] = df[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, 'TRUE':True, 'FALSE':False}).fillna(False)
    
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352', 'PRIOR']:
        if c not in df.columns: df[c] = "0"
        df[c] = df[c].astype(str).str.replace('.0', '', regex=False).replace(['nan', 'None', ''], '0').str.strip()
    
    df['IS_HIF'] = is_hif
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.markdown("""<style>
        .stAppViewBlockContainer { padding-top: 0px !important; } 
        div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        div.stButton > button { height: 2.2em !important; font-size: 0.85rem !important; margin-bottom: 0.1rem !important; }
    </style>""", unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)
    df_all = pd.concat([df_scout, df_hif], ignore_index=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])
    vindue_options = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

    # TAB 1: EMNER
    with t1:
        source_df = df_scout[df_scout['ER_EMNE']==True]
        if not source_df.empty:
            cols = ['Navn', 'Alder', 'BIRTHDATE', 'KLUB', 'POS', 'KONTRAKT', 'TRANSFER_VINDUE', 'ER_EMNE', 'SKYGGEHOLD']
            sub = source_df[[c for c in cols if c in source_df.columns or c in ['Navn', 'Alder']]].set_index('Navn')
            st.data_editor(sub.style.applymap(get_color_by_date, subset=['KONTRAKT'] if 'KONTRAKT' in sub.columns else []), use_container_width=True, height=600)

    # TAB 2: HIF
    with t2:
        if not df_hif.empty:
            k_col = 'UDLØB' if 'UDLØB' in df_hif.columns else 'KONTRAKT'
            cols = ['Navn', 'Alder', 'BIRTHDATE', 'POS', k_col, 'SKYGGEHOLD']
            sub = df_hif[[c for c in cols if c in df_hif.columns or c in ['Navn', 'Alder']]].set_index('Navn')
            st.data_editor(sub.style.applymap(get_color_by_date, subset=[k_col] if k_col in sub.columns else []), use_container_width=True, height=600)

    # TAB 3: SKYGGELISTE
    with t3:
        df_sky = df_all[df_all['SKYGGEHOLD'] == True].drop_duplicates(subset=['Navn'])
        if not df_sky.empty:
            k_col = 'UDLØB' if 'UDLØB' in df_sky.columns else 'KONTRAKT'
            cols = ['Navn', 'Alder', 'KLUB', 'POS', k_col, 'POS_343', 'POS_433', 'POS_352']
            sub = df_sky[[c for c in cols if c in df_sky.columns or c in ['Navn', 'Alder']]].set_index('Navn')
            st.data_editor(sub.style.applymap(get_color_by_date, subset=[k_col] if k_col in sub.columns else []), use_container_width=True, height=600)

    # TAB 4: BANE
    with t4:
        # Bredere dropdown kolonne (1.7 i stedet for 1.2)
        c_pitch, c_ctrl = st.columns([8.3, 1.7])
        with c_ctrl:
            sel_v = st.selectbox("Vindue", vindue_options, key="v_bane")
            st.write("") 
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()

        with c_pitch:
            p_col = f"POS_{st.session_state.form_skygge.replace('-', '')}"
            df_f = df_hif if sel_v == "Nuværende trup" else pd.concat([df_hif[df_hif['SKYGGEHOLD']==True], df_scout[(df_scout['SKYGGEHOLD']==True) & (df_scout['TRANSFER_VINDUE']==sel_v)]]).drop_duplicates(subset=['Navn'])
            
            if 'PRIOR' in df_f.columns:
                df_f = df_f.sort_values(by='PRIOR', ascending=True)

            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formations-koordinater
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            for pid, (px, py, lbl) in m.items():
                ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)]
                for i, (_, p_row) in enumerate(plist.iterrows()):
                    bg = "white"
                    u_val = p_row.get('UDLØB') if pd.notna(p_row.get('UDLØB')) and p_row.get('UDLØB') != "-" else p_row.get('KONTRAKT')
                    
                    if not p_row['IS_HIF']: 
                        bg = GRON_NY
                    else:
                        try:
                            if u_val and u_val != "-":
                                days = (pd.to_datetime(u_val, dayfirst=True) - datetime.now()).days
                                if days < 183: bg = ROD_ADVARSEL
                                elif days <= 365: bg = GUL_ADVARSEL
                        except: pass
                    
                    if str(p_row.get('PRIOR', '')).upper() == 'L': bg = LEJE_GRA
                        
                    ax.text(px, py + (i * 2.8), p_row['Navn'], size=7.5, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2'))

            ax.text(2, 2.3, " < 6 mdr ", size=7, weight='bold', bbox=dict(facecolor=ROD_ADVARSEL))
            ax.text(12, 2.3, " 6-12 mdr ", size=7, weight='bold', bbox=dict(facecolor=GUL_ADVARSEL))
            ax.text(23, 2.3, " Transfer ", size=7, weight='bold', bbox=dict(facecolor=GRON_NY))
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
