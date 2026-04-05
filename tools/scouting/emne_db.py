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

def get_status_color(val):
    """Returnerer hex-farve baseret på kontraktlængde"""
    try:
        if pd.isna(val): return None
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return None
        days = (dt - datetime.now()).days
        if days < 183: return ROD_ADVARSEL
        if days <= 365: return GUL_ADVARSEL
        return None
    except: return None

def get_color_by_date(val):
    """CSS-version til data_editor styling"""
    color = get_status_color(val)
    return f'background-color: {color}' if color else ""

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
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE'
        ]
        _, sha = get_github_file(path)
        export_df = df.copy()
        rev_map = {'Navn': 'NAVN', 'Klub': 'KLUB', 'Pos': 'POS', 'Vindue': 'TRANSFER_VINDUE', 
                   'Emne': 'ER_EMNE', 'Skyggehold': 'SKYGGEHOLD', 'Pos_343': 'POS_343', 
                   'Pos_433': 'POS_433', 'Pos_352': 'POS_352'}
        export_df = export_df.rename(columns=rev_map)
        for col in original_cols:
            if col not in export_df.columns: export_df[col] = ""
        export_df = export_df[original_cols]
        csv_content = export_df.to_csv(index=False)
        payload = {"message": "Update scout data", "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), "sha": sha}
        requests.put(f"https://api.github.com/repos/{REPO}/contents/{path}", headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        st.toast("✅ Gemt på GitHub", icon="💾")
        return True
    except Exception as e:
        st.error(f"Fejl ved gem: {e}"); return False

# --- 3. DATA PROCESSING ---
def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    for col in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False).str.strip()
            df[col] = df[col].replace(['nan', 'None', '0', ''], "")

    if 'BIRTHDATE' in df.columns:
        df['Fødselsdato'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
        df['Alder'] = df['Fødselsdato'].apply(calculate_age_str)
    
    if 'KONTRAKT' in df.columns:
        df['Kontrakt'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')

    col_map = {'KLUB': 'Klub', 'POS': 'Pos', 'TRANSFER_VINDUE': 'Vindue', 'ER_EMNE': 'Emne', 
               'SKYGGEHOLD': 'Skyggehold', 'POS_343': 'Pos_343', 'POS_433': 'Pos_433', 'POS_352': 'Pos_352'}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    df['IS_HIF'] = df['Klub'].str.contains("Hvidovre", case=False, na=False) if 'Klub' in df.columns else False
    
    for c in ['Emne', 'Skyggehold']:
        if c in df.columns:
            df[c] = df[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False}).fillna(False)
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.set_page_config(layout="wide", page_title="HIF Scouting")
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, sha = get_github_file(SCOUT_DB_PATH)
    if content is None: return
    df_all = prepare_df(content)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])
    date_cfg = {"Fødselsdato": st.column_config.DateColumn("Fødselsdato", format="DD/MM/YYYY"), 
                "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY")}

    with t1:
        cols_t1 = ['Navn', 'Alder', 'Klub', 'Pos', 'Kontrakt', 'Vindue', 'Emne', 'Skyggehold']
        source = df_all[~df_all['IS_HIF']][cols_t1]
        st.data_editor(source.set_index('Navn').style.applymap(get_color_by_date, subset=['Kontrakt']), column_config=date_cfg, use_container_width=True, height=600)

    with t2:
        cols_t2 = ['Navn', 'Alder', 'Klub', 'Pos', 'Kontrakt', 'Emne', 'Skyggehold']
        hif = df_all[df_all['IS_HIF']][cols_t2]
        st.data_editor(hif.set_index('Navn').style.applymap(get_color_by_date, subset=['Kontrakt']), column_config=date_cfg, use_container_width=True, height=600)

    with t3:
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
            disabled=["Navn", "Klub", "Pos"], use_container_width=True, key="sky_edit_final"
        )
        if st.session_state.get("sky_edit_final") and st.session_state.sky_edit_final.get("edited_rows"):
            for idx_str, updated_cols in st.session_state.sky_edit_final["edited_rows"].items():
                p_name = sky_df.iloc[int(idx_str)]['Navn']
                for col, val in updated_cols.items():
                    if col in ['Pos_343', 'Pos_433', 'Pos_352'] and val and str(val) != "3.5" and "." not in str(val):
                        val = f"{val}.0"
                    df_all.loc[df_all['Navn'] == p_name, col] = val
            if save_to_github(df_all, SCOUT_DB_PATH): st.rerun()

    with t4:
        c_pitch, c_ctrl = st.columns([8.2, 1.8])
        with c_ctrl:
            sel_v = st.selectbox("Vindue", ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27"])
            # st.markdown fjernet herfra da den nu er på banen
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()

        with c_pitch:
            f_suffix = st.session_state.form_skygge.replace('-', '')
            p_col = f"Pos_{f_suffix}"
            df_f = df_all[df_all['IS_HIF']].copy() if sel_v == "Nuværende trup" else df_all[(df_all['Skyggehold'] == True) & ((df_all['IS_HIF']) | (df_all['Vindue'] == sel_v))].copy()
            
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # --- LEGENDS (VENSTRE) ---
            ax.text(1, 2, " < 6 mdr ", size=8, fontweight='bold', va='bottom', bbox=dict(facecolor=ROD_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(12, 2, " 6-12 mdr ", size=8, fontweight='bold', va='bottom', bbox=dict(facecolor=GUL_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(25, 2, " Transfer ", size=8, fontweight='bold', va='bottom', bbox=dict(facecolor=GRON_NY, edgecolor='#ccc', boxstyle='round,pad=0.2'))

            # --- VINDUE STATUS (HØJRE) ---
            # x=99 placerer den i højre side, ha='right' sikrer den ikke ryger ud af billedet
            ax.text(99, 2, f" Vindue: {sel_v} ", size=9, fontweight='bold', va='bottom', ha='right', 
                    bbox=dict(facecolor='white', edgecolor='#333', boxstyle='round,pad=0.3'))

            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            if p_col in df_f.columns:
                for pid, (px, py, lbl) in m.items():
                    ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    plist = df_f[df_f[p_col].astype(str) == str(pid)]
                    for i, (_, p_row) in enumerate(plist.iterrows()):
                        k_color = get_status_color(p_row['Kontrakt'])
                        bg = k_color if k_color else ("white" if p_row['IS_HIF'] else GRON_NY)
                        ax.text(px, py + (i * 3.2), p_row['Navn'], size=7.5, ha='center', weight='bold', bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2'))
            
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
