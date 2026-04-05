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
GUL_ADVARSEL = "#ffff99" # 6-12 mdr.
ROD_ADVARSEL = "#ffcccc" # < 6 mdr.

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
    
    # Beregn måneder til kontraktudløb for HIF spillere
    if is_hif and 'UDLØB' in df.columns:
        def calc_months(date_str):
            try:
                # Forventer format DD-MM-YYYY eller lignende
                expiry = pd.to_datetime(date_str, dayfirst=True)
                now = datetime.now()
                return (expiry.year - now.year) * 12 + (expiry.month - now.month)
            except:
                return 99
        df['MDR_TIL_UDLØB'] = df['UDLØB'].apply(calc_months)
    else:
        df['MDR_TIL_UDLØB'] = 99

    df['IS_HIF'] = is_hif
    return df

# --- 4. HOVEDFUNKTION ---
def vis_side(df):
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

    # Editører (Tab 1 & 2)
    for tab, source_df, p_path, k_base in [
        (tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "E"),
        (tabs[1], df_hif, HIF_PATH, "H")
    ]:
        with tab:
            if not source_df.empty:
                cols_to_show = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
                if 'UDLØB' in source_df.columns: cols_to_show.append('UDLØB')
                
                d_edit = source_df.set_index('Navn')[cols_to_show]
                ed = st.data_editor(d_edit, use_container_width=True, height=500, key=f"ed_{k_base}")
                
                if not ed.equals(d_edit):
                    raw, sha = get_github_file(p_path)
                    df_s = pd.read_csv(StringIO(raw))
                    df_s.columns = [str(x).upper().strip() for x in df_s.columns]
                    if 'NAVN' in df_s.columns: df_s = df_s.rename(columns={'NAVN': 'Navn'})
                    for n, r in ed.iterrows():
                        mask = df_s['Navn'].astype(str).str.strip() == str(n).strip()
                        df_s.loc[mask, cols_to_show] = [r[c] for c in cols_to_show]
                    push_to_github(p_path, f"Update {k_base}", df_s.to_csv(index=False), sha)
                    st.rerun()

    # Tab 3: Skyggeliste
    with tabs[2]:
        df_sky = df_all[df_all['SKYGGEHOLD'] == True].drop_duplicates(subset=['Navn'])
        if not df_sky.empty:
            d_sky_ed = df_sky.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']]
            ed_s = st.data_editor(d_sky_ed, use_container_width=True, height=500, key="sky_ed_final")
            if not ed_s.equals(d_sky_ed):
                for path in [SCOUT_DB_PATH, HIF_PATH]:
                    raw, sha = get_github_file(path)
                    if not raw: continue
                    df_tmp = pd.read_csv(StringIO(raw))
                    df_tmp.columns = [c.upper().strip() for c in df_tmp.columns]
                    if 'NAVN' in df_tmp.columns: df_tmp = df_tmp.rename(columns={'NAVN': 'Navn'})
                    changed = False
                    for n, r in ed_s.iterrows():
                        mask = df_tmp['Navn'].astype(str).str.strip() == str(n).strip()
                        if mask.any():
                            df_tmp.loc[mask, ['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']] = [r['TRANSFER_VINDUE'], r['POS_343'], r['POS_433'], r['POS_352']]
                            changed = True
                    if changed: push_to_github(path, "Skygge Update", df_tmp.to_csv(index=False), sha)
                st.rerun()

    # --- Tab 4: Bane ---
with tabs[3]:
    # 1. TRANSFERVINDUE-DROPDOWN ØVERST
    # Vi placerer den i en kolonne for at styre bredden, så den ikke fylder hele skærmen
    c_top1, c_top2 = st.columns([2, 3])
    with c_top1:
        # Antager at sel_v styres herinde eller hentes fra en overordnet variabel
        # Hvis sel_v er defineret uden for fanerne, kan du blot vise værdien eller lave en ny selectbox:
        ny_sel_v = st.selectbox("Vælg Transfervindue", ["Nuværende trup", "Sommer 2026", "Vinter 2027"], index=0, key="sb_vindue_tab4")
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. FORMATIONS-KNAPPER (Lige under dropdown)
    f = st.session_state.form_skygge
    p_col = f"POS_{f.replace('-', '')}"
    
    c_btn1, c_btn2, c_btn3, c_spacer = st.columns([1, 1, 1, 6])
    with c_btn1:
        if st.button("3-4-3", key="btn_343", use_container_width=True, type="primary" if f == "3-4-3" else "secondary"):
            st.session_state.form_skygge = "3-4-3"
            st.rerun()
    with c_btn2:
        if st.button("4-3-3", key="btn_433", use_container_width=True, type="primary" if f == "4-3-3" else "secondary"):
            st.session_state.form_skygge = "4-3-3"
            st.rerun()
    with c_btn3:
        if st.button("3-5-2", key="btn_352", use_container_width=True, type="primary" if f == "3-5-2" else "secondary"):
            st.session_state.form_skygge = "3-5-2"
            st.rerun()

    # 3. DATA-FILTRERING (Bruger ny_sel_v fra dropdownen)
    if ny_sel_v == "Nuværende trup":
        df_f = df_hif.drop_duplicates(subset=['Navn'])
    else:
        h_s = df_hif[df_hif['SKYGGEHOLD'] == True]
        e_s = df_scout[(df_scout['SKYGGEHOLD'] == True) & (df_scout['TRANSFER_VINDUE'] == ny_sel_v)]
        df_f = pd.concat([h_s, e_s], ignore_index=True).drop_duplicates(subset=['Navn'])

    # 4. BANE-VISNING (Pitch logik...)
    pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
    fig, ax = pitch.draw(figsize=(10, 7))
    # ... resten af din eksisterende ax.text og plotting logik ...

    # Husk at opdatere vindue-teksten nederst på banen til at bruge den nye variabel
    ax.text(118, 2.3, f"Vindue: {ny_sel_v}", size=9, weight='bold', ha='right', va='bottom', color=HIF_ROD)
    
    st.pyplot(fig, use_container_width=True)
if __name__ == "__main__":
    vis_side()
