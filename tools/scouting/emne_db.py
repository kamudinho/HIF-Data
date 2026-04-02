import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
SCOUT_DB_PATH = "data/scouting_db.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"
GRON_NY = "#ccffcc" 

VINDUE_OPTIONS_GLOBAL = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]

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

def vis_side():
    # CSS til at fjerne top-margin og optimere layout
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 0px !important; }
            div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }
            [data-testid="stVerticalBlock"] > div:first-child { margin-top: -1rem !important; }
            /* Gør dropdown mindre og fjerner label-plads */
            div[data-testid="stSelectbox"] > label { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    # 1. Hent data
    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)
    df_all = pd.concat([df_scout, df_hif], ignore_index=True)

    # 2. Header layout med dropdown til højre for tabs
    col_tabs, col_v = st.columns([4, 1])
    
    with col_v:
        sel_v = st.selectbox("Transfervindue", VINDUE_OPTIONS_GLOBAL, key="global_v_sel", index=1, label_visibility="collapsed")

    with col_tabs:
        tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # TAB 1 & 2: Editører (Emner og HIF)
    for tab, source_df, p_path, k_base in [
        (tabs[0], df_scout[df_scout['ER_EMNE']==True], SCOUT_DB_PATH, "E"),
        (tabs[1], df_hif, HIF_PATH, "H")
    ]:
        with tab:
            if not source_df.empty:
                d_edit = source_df.set_index('Navn')[['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']]
                ed = st.data_editor(d_edit, use_container_width=True, height=600, key=f"ed_{k_base}")
                if not ed.equals(d_edit):
                    raw, sha = get_github_file(p_path)
                    df_s = pd.read_csv(StringIO(raw))
                    df_s.columns = [str(x).upper().strip() for x in df_s.columns]
                    if 'NAVN' in df_s.columns: df_s = df_s.rename(columns={'NAVN': 'Navn'})
                    for n, r in ed.iterrows():
                        mask = df_s['Navn'].astype(str).str.strip() == str(n).strip()
                        df_s.loc[mask, ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']] = [r['TRANSFER_VINDUE'], r['POS'], r['SKYGGEHOLD']]
                    push_to_github(p_path, f"Update {k_base}", df_s.to_csv(index=False), sha)
                    st.rerun()

    # TAB 3: Skyggeliste
    with tabs[2]:
        df_sky = df_all[df_all['SKYGGEHOLD'] == True].drop_duplicates(subset=['Navn'])
        if not df_sky.empty:
            d_sky_ed = df_sky.set_index('Navn')[['TRANSFER_VINDUE', 'POS_343', 'POS_433', 'POS_352']]
            ed_s = st.data_editor(d_sky_ed, use_container_width=True, height=600, key="sky_ed_final")
            
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
                    if changed:
                        push_to_github(path, "Skygge Update", df_tmp.to_csv(index=False), sha)
                st.rerun()

    # TAB 4: Bane
    with tabs[3]:
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        if sel_v == "Nuværende trup":
            df_f = df_hif.drop_duplicates(subset=['Navn'])
        else:
            h_s = df_hif[df_hif['SKYGGEHOLD'] == True]
            e_s = df_scout[(df_scout['SKYGGEHOLD'] == True) & (df_scout['TRANSFER_VINDUE'] == sel_v)]
            df_f = pd.concat([h_s, e_s], ignore_index=True).drop_duplicates(subset=['Navn'])

        c_p, c_m = st.columns([8.5, 1.5])
        with c_m:
            for o in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(o, key=f"btn_{o}", use_container_width=True, type="primary" if f == o else "secondary"):
                    st.session_state.form_skygge = o
                    st.rerun()

        with c_p:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 6))
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(55,10,'VWB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "2":(55,70,'HWB'), "11":(80,15,'VW'), "9":(100,40,'ANG'), "7":(80,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,10,'VB'), "4":(30,25,'VCB'), "3":(30,55,'HCB'), "2":(35,70,'HB'), "6":(55,30,'DM'), "8":(55,50,'DM'), "10":(75,40,'CM'), "11":(85,15,'VW'), "9":(100,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(30,22,'VCB'), "3.5":(30,40,'CB'), "3":(30,58,'HCB'), "5":(45,10,'VWB'), "6":(60,30,'DM'), "8":(60,50,'DM'), "2":(45,70,'HWB'), "10":(75,40,'CM'), "9":(95,32,'ANG'), "7":(95,48,'ANG')}}[f]

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)]
                for i, (_, p_row) in enumerate(plist.iterrows()):
                    is_new = (p_row['IS_HIF'] == False)
                    ax.text(x, y + (i * 2.3), f"{p_row['Navn']}{'*' if is_new else ''}", size=7, ha='center', va='center', weight='bold', bbox=dict(facecolor=GRON_NY if is_new else "white", edgecolor="#333", alpha=0.8, boxstyle='square,pad=0.2'))
            st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
