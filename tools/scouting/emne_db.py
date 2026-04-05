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
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 
GUL_ADVARSEL = "#ffff99" 
ROD_ADVARSEL = "#ffcccc" 

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

def save_to_github(df, path):
    try:
        _, sha = get_github_file(path)
        csv_content = df.to_csv(index=False)
        encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
        url = f"https://api.github.com/repos/{REPO}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
        payload = {"message": "Auto-update fra app", "content": encoded_content, "sha": sha}
        r = requests.put(url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            st.toast("✅ Gemt automatisk på GitHub", icon="💾")
            return True
    except: pass
    return False

# --- 3. DATA PROCESSING ---
def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content), dtype={'POS': str, 'POS_343': str, 'POS_433': str, 'POS_352': str})
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    if 'Navn' not in df.columns: return pd.DataFrame()
    
    # FIX: Fjern helt tomme rækker og rækker uden navn for at undgå Duplicate Keys fejl
    df = df.dropna(subset=['Navn'])
    df = df[df['Navn'].str.strip() != ""]
    df = df.drop_duplicates(subset=['Navn'], keep='first') # Sikrer unikke nøgler (Navne)
    
    # Rens alle POS-kolonner for .0 og fjern "0"
    pos_cols = [c for c in df.columns if 'POS' in c]
    for col in pos_cols:
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).str.strip()
        df[col] = df[col].replace(['nan', 'None', '<NA>', '0', '0.0'], "")

    if 'BIRTHDATE' in df.columns:
        df['Fødselsdato'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
        df['Alder'] = df['Fødselsdato'].apply(calculate_age_str)
    
    if 'KONTRAKT' in df.columns:
        df['Kontrakt'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')

    col_map = {'KLUB': 'Klub', 'POS': 'Pos', 'TRANSFER_VINDUE': 'Vindue', 'ER_EMNE': 'Emne', 'SKYGGEHOLD': 'Skyggehold', 'POS_343': 'Pos_343', 'POS_433': 'Pos_433', 'POS_352': 'Pos_352'}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    df['IS_HIF'] = df['Klub'].str.contains("Hvidovre", case=False, na=False)
    
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.set_page_config(layout="wide", page_title="Hvidovre Scouting")
    
    # CSS til at fjerne unødig luft i toppen
    st.markdown("""<style>
        .stAppViewBlockContainer { padding-top: 1rem !important; }
        div.block-container { max-width: 98% !important; }
    </style>""", unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, sha = get_github_file(SCOUT_DB_PATH)
    if content is None:
        st.error("Kunne ikke hente data fra GitHub")
        return

    df_all = prepare_df(content)
    
    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])
    date_cfg = {"Fødselsdato": st.column_config.DateColumn("Fødselsdato", format="DD/MM/YYYY"), "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY")}

    with t1:
        source = df_all[~df_all['IS_HIF']]
        st.data_editor(source.set_index('Navn').style.applymap(get_color_by_date, subset=['Kontrakt']), column_config=date_cfg, use_container_width=True, height=600, key="t1_editor")

    with t2:
        hif = df_all[df_all['IS_HIF']]
        st.data_editor(hif.set_index('Navn').style.applymap(get_color_by_date, subset=['Kontrakt']), column_config=date_cfg, use_container_width=True, height=600, key="t2_editor")

    with t3:        
        st.info("Ændringer gemmes automatisk i baggrunden.")
        display_options = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]
        sky_df = df_all[df_all['Skyggehold'] == True].copy()
        
        edited_sky = st.data_editor(
            sky_df[['Navn', 'Klub', 'Pos', 'Pos_343', 'Pos_433', 'Pos_352', 'Skyggehold']],
            column_config={
                "Pos_343": st.column_config.SelectboxColumn("Pos 3-4-3", options=display_options),
                "Pos_433": st.column_config.SelectboxColumn("Pos 4-3-3", options=display_options),
                "Pos_352": st.column_config.SelectboxColumn("Pos 3-5-2", options=display_options),
                "Skyggehold": st.column_config.CheckboxColumn("Aktiv"),
            },
            disabled=["Navn", "Klub", "Pos"],
            use_container_width=True,
            key="sky_editor"
        )
        
        # AUTOMATISK GEM-LOGIK
        if st.session_state.sky_editor["edited_rows"]:
            changes = st.session_state.sky_editor["edited_rows"]
            has_changed = False
            
            for idx_int, updated_cols in changes.items():
                # Find det rigtige navn baseret på rækkens index i det filtrerede sky_df
                real_idx = sky_df.index[int(idx_int)]
                player_name = sky_df.loc[real_idx, 'Navn']
                
                for col, val in updated_cols.items():
                    # Formater til .0 for at bevare din CSV-standard (undtagen 3.5 og tomme)
                    if col in ['Pos_343', 'Pos_433', 'Pos_352'] and val and val != "3.5" and "." not in str(val):
                        val = f"{val}.0"
                    df_all.loc[df_all['Navn'] == player_name, col] = val
                    has_changed = True
            
            if has_changed:
                if save_to_github(df_all, SCOUT_DB_PATH):
                    st.rerun()

    with t4:
        c_pitch, c_ctrl = st.columns([8.2, 1.8])
        with c_ctrl:
            sel_v = st.selectbox("Vindue", ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27"])
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()
        
        with c_pitch:
            f_suffix = st.session_state.form_skygge.replace('-', '')
            p_col = f"Pos_{f_suffix}"
            df_f = df_all[df_all['IS_HIF']].copy() if sel_v == "Nuværende tildeling" else df_all[(df_all['Skyggehold'] == True) & ((df_all['IS_HIF']) | (df_all['Vindue'] == sel_v))].copy()
            
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            if p_col in df_f.columns:
                # Vi bruger de allerede rensede data fra prepare_df
                for pid, (px, py, lbl) in m.items():
                    ax.text(px, py-4.5, str(lbl), size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    # Matcher den rensede pid (f.eks. "5" mod "5")
                    plist = df_f[df_f[p_col] == str(pid)]
                    for i, (_, p_row) in enumerate(plist.iterrows()):
                        bg = "white" if p_row['IS_HIF'] else GRON_NY
                        ax.text(px, py + (i * 3.2), p_row['Navn'], size=7.5, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2'))
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
