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
    if pd.isna(born): return "-"
    try:
        today = datetime.now()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return f"{int(age)} år"
    except: return "-"

def get_color_by_date(val):
    try:
        if pd.isna(val): return ""
        # Håndter både strings og datetime objekter
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return ""
        days = (dt - datetime.now()).days
        if days < 183: return f'background-color: {ROD_ADVARSEL}'
        if days <= 365: return f'background-color: {GUL_ADVARSEL}'
        return ""
    except: return ""

def get_github_file(path):
    try:
        # Vi beholder tidsstemplet i URL for at sikre, at GitHub ikke sender gammelt data
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
    
    # 1. Konverter BIRTHDATE og beregn Alder
    if 'BIRTHDATE' in df.columns:
        df['Fødselsdato'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
        df['Alder'] = df['Fødselsdato'].apply(calculate_age_str)
    else:
        df['Fødselsdato'] = pd.NaT
        df['Alder'] = "-"

    # 2. Håndter Kontrakt/Udløb
    k_src = 'UDLØB' if 'UDLØB' in df.columns else 'KONTRAKT'
    if k_src in df.columns:
        df['Kontrakt'] = pd.to_datetime(df[k_src], dayfirst=True, errors='coerce')
    else:
        df['Kontrakt'] = pd.NaT

    # 3. Map øvrige kolonner
    col_map = {
        'KLUB': 'Klub', 'POS': 'Pos', 'TRANSFER_VINDUE': 'Vindue',
        'ER_EMNE': 'Emne', 'SKYGGEHOLD': 'Skyggehold',
        'POS_343': 'Pos_343', 'POS_433': 'Pos_433', 'POS_352': 'Pos_352'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    if 'Vindue' in df.columns:
        df['Vindue'] = df['Vindue'].replace(['Nu', 'nu', 'NU'], 'Nuværende trup').fillna("Sommer 26")
    
    for c in ['Emne', 'Skyggehold']:
        if c in df.columns:
            df[c] = df[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False, 'TRUE':True, 'FALSE':False}).fillna(False)
    
    df['IS_HIF'] = is_hif
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.markdown("""<style>
        .stAppViewBlockContainer { padding-top: 0px !important; } 
        div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        div.stButton > button { height: 2.2em !important; font-size: 0.85rem !important; }
    </style>""", unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    s_c, _ = get_github_file(SCOUT_DB_PATH)
    h_c, _ = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)
    df_all = pd.concat([df_scout, df_hif], ignore_index=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])
    
    date_cfg = {
        "Fødselsdato": st.column_config.DateColumn("Fødselsdato", format="DD/MM/YYYY"),
        "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY")
    }

    with t1: # EMNER
        source = df_scout[df_scout['Emne']==True]
        if not source.empty:
            cols = ['Navn', 'Alder', 'Fødselsdato', 'Klub', 'Pos', 'Kontrakt', 'Vindue', 'Emne', 'Skyggehold']
            display = source[[c for c in cols if c in source.columns]].set_index('Navn')
            st.data_editor(display.style.applymap(get_color_by_date, subset=['Kontrakt']), 
                           column_config=date_cfg, use_container_width=True, height=600)

    with t2: # HIF
        if not df_hif.empty:
            cols = ['Navn', 'Alder', 'Fødselsdato', 'Pos', 'Kontrakt', 'Skyggehold']
            display = df_hif[[c for c in cols if c in df_hif.columns]].set_index('Navn')
            st.data_editor(display.style.applymap(get_color_by_date, subset=['Kontrakt']), 
                           column_config=date_cfg, use_container_width=True, height=600)

    with t3: # SKYGGELISTE
        sky = df_all[df_all['Skyggehold'] == True].drop_duplicates(subset=['Navn'])
        if not sky.empty:
            cols = ['Navn', 'Alder', 'Klub', 'Pos', 'Kontrakt', 'Pos_343', 'Pos_433', 'Pos_352']
            display = sky[[c for c in cols if c in sky.columns]].set_index('Navn')
            st.data_editor(display.style.applymap(get_color_by_date, subset=['Kontrakt']), 
                           column_config=date_cfg, use_container_width=True, height=600)

    with t4: # BANE
        c_pitch, c_ctrl = st.columns([8.2, 1.8])
        with c_ctrl:
            sel_v = st.selectbox("Vindue", ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27"], key="v_bane")
            st.write("")
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()

        with c_pitch:
            f_suffix = st.session_state.form_skygge.replace('-', '')
            p_col = f"Pos_{f_suffix}" if f"Pos_{f_suffix}" in df_all.columns else f"POS_{f_suffix}"
            
            if sel_v == "Nuværende trup":
                df_f = df_hif.copy()
            else:
                h_part = df_hif[df_hif['Skyggehold'] == True]
                s_part = df_scout[(df_scout['Skyggehold'] == True) & (df_scout['Vindue'] == sel_v)]
                df_f = pd.concat([h_part, s_part]).drop_duplicates(subset=['Navn'])

            if 'PRIOR' in df_f.columns:
                df_f = df_f.sort_values(by='PRIOR', ascending=True)

            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            ax.text(118, 2, f"Vindue: {sel_v}", size=10, weight='bold', color=HIF_ROD, ha='right')
            ax.text(2, 2, "< 6 mdr", size=8, weight='bold', bbox=dict(facecolor=ROD_ADVARSEL, edgecolor='#333', boxstyle='round,pad=0.2'))
            ax.text(14, 2, "6-12 mdr", size=8, weight='bold', bbox=dict(facecolor=GUL_ADVARSEL, edgecolor='#333', boxstyle='round,pad=0.2'))
            ax.text(28, 2, "Transfer", size=8, weight='bold', bbox=dict(facecolor=GRON_NY, edgecolor='#333', boxstyle='round,pad=0.2'))

            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            if p_col in df_f.columns:
                df_f[p_col] = df_f[p_col].astype(str).str.replace('.0', '', regex=False).str.strip()
                for pid, (px, py, lbl) in m.items():
                    ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    plist = df_f[df_f[p_col] == str(pid)]
                    for i, (_, p_row) in enumerate(plist.iterrows()):
                        bg = "white"
                        u_val = p_row.get('Kontrakt')
                        if not p_row['IS_HIF']: bg = GRON_NY
                        else:
                            try:
                                if pd.notna(u_val):
                                    days = (u_val - datetime.now()).days
                                    if days < 183: bg = ROD_ADVARSEL
                                    elif days <= 365: bg = GUL_ADVARSEL
                            except: pass
                        if str(p_row.get('PRIOR', '')).upper() == 'L': bg = LEJE_GRA
                        ax.text(px, py + (i * 3.2), p_row['Navn'], size=7.5, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2'))
            
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
