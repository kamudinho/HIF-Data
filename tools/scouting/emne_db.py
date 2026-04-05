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
LEJE_GRA = "#e0e0e0"

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

# --- 4. HOVEDFUNKTION ---
def vis_side():
    st.markdown("""
        <style>
            .stAppViewBlockContainer { padding-top: 20px !important; } 
            div.block-container { padding-top: 1rem !important; max-width: 98% !important; }
            .stTabs { margin-top: 0px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    if 'form_skygge' not in st.session_state: 
        st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)
    df_all = pd.concat([df_scout, df_hif], ignore_index=True)

    t1, t2, t3, t4 = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # Tab 1, 2, 3 (Uændret redigering) ...
    with t1:
        source_df = df_scout[df_scout['ER_EMNE']==True]
        if not source_df.empty:
            cols_to_show = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
            d_edit = source_df.set_index('Navn')[cols_to_show]
            ed = st.data_editor(d_edit, use_container_width=True, height=500, key="ed_E")
            if not ed.equals(d_edit):
                raw, sha = get_github_file(SCOUT_DB_PATH); df_s = pd.read_csv(StringIO(raw))
                df_s.columns = [str(x).upper().strip() for x in df_s.columns]
                if 'NAVN' in df_s.columns: df_s = df_s.rename(columns={'NAVN': 'Navn'})
                for n, r in ed.iterrows():
                    mask = df_s['Navn'].astype(str).str.strip() == str(n).strip()
                    df_s.loc[mask, cols_to_show] = [r[c] for c in cols_to_show]
                push_to_github(SCOUT_DB_PATH, "Update Emner", df_s.to_csv(index=False), sha); st.rerun()

    with t2:
        if not df_hif.empty:
            cols_to_show = ['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']
            date_col = 'UDLØB' if 'UDLØB' in df_hif.columns else 'KONTRAKT'
            cols_to_show.append(date_col)
            d_edit = df_hif.set_index('Navn')[cols_to_show]
            ed = st.data_editor(d_edit, use_container_width=True, height=500, key="ed_H")
            if not ed.equals(d_edit):
                raw, sha = get_github_file(HIF_PATH); df_s = pd.read_csv(StringIO(raw))
                df_s.columns = [str(x).upper().strip() for x in df_s.columns]
                if 'NAVN' in df_s.columns: df_s = df_s.rename(columns={'NAVN': 'Navn'})
                for n, r in ed.iterrows():
                    mask = df_s['Navn'].astype(str).str.strip() == str(n).strip()
                    df_s.loc[mask, cols_to_show] = [r[c] for c in cols_to_show]
                push_to_github(HIF_PATH, "Update HIF", df_s.to_csv(index=False), sha); st.rerun()

    with t3:
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
    with t4:
        c_pitch, c_ctrl = st.columns([9, 3])
        
        with c_ctrl:
            # Låst rækkefølge
            vindue_options = ["Nuværende trup", "Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
            sel_v = st.selectbox("Vælg Transfervindue", vindue_options, key="sb_skygg_top")
            
            st.write("**Formation:**")
            f = st.session_state.form_skygge
            c_b1, c_b2, c_b3 = st.columns(3)
            if c_b1.button("3-4-3", use_container_width=True, type="primary" if f == "3-4-3" else "secondary"):
                st.session_state.form_skygge = "3-4-3"; st.rerun()
            if c_b2.button("4-3-3", use_container_width=True, type="primary" if f == "4-3-3" else "secondary"):
                st.session_state.form_skygge = "4-3-3"; st.rerun()
            if c_b3.button("3-5-2", use_container_width=True, type="primary" if f == "3-5-2" else "secondary"):
                st.session_state.form_skygge = "3-5-2"; st.rerun()

        with c_pitch:
            p_col = f"POS_{f.replace('-', '')}"
            if sel_v == "Nuværende trup":
                df_f = df_hif.drop_duplicates(subset=['Navn'])
            else:
                h_s = df_hif[df_hif['SKYGGEHOLD'] == True]
                e_s = df_scout[(df_scout['SKYGGEHOLD'] == True) & (df_scout['TRANSFER_VINDUE'] == sel_v)]
                df_f = pd.concat([h_s, e_s], ignore_index=True).drop_duplicates(subset=['Navn'])

            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formation mapping
            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,40,'DM'), "2":(55,70,'HWB'), "8":(75,28,'CM'), "10":(75,52,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[f]

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)]
                for i, (_, p_row) in enumerate(plist.iterrows()):
                    bg_color = "white"
                    if not p_row['IS_HIF']: bg_color = GRON_NY
                    elif str(p_row.get('PRIOR', '')).upper() == 'L': bg_color = LEJE_GRA
                    else:
                        u_val = p_row.get('UDLØB') if pd.notna(p_row.get('UDLØB')) else p_row.get('KONTRAKT')
                        try:
                            days = (pd.to_datetime(u_val, dayfirst=True) - datetime.now()).days
                            if days < 183: bg_color = ROD_ADVARSEL
                            elif days <= 365: bg_color = GUL_ADVARSEL
                        except: bg_color = "white"
                    ax.text(x, y + (i * 2.8), p_row['Navn'], size=7.5, ha='center', va='center', weight='bold', bbox=dict(facecolor=bg_color, edgecolor="#333", alpha=0.9, boxstyle='square,pad=0.2', linewidth=0.5))

            # --- Legends & Info (Nederst) ---
            ax.text(2, 2.3, " < 6 mdr ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=ROD_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(12, 2.3, " 6-12 mdr ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=GUL_ADVARSEL, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(23, 2.3, " Transfer ", size=7, weight='bold', va='bottom', bbox=dict(facecolor=GRON_NY, edgecolor='#ccc', boxstyle='round,pad=0.2'))
            ax.text(118, 2.3, f"Vindue: {sel_v}", size=9, weight='bold', ha='right', va='bottom', color=HIF_ROD)

            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
