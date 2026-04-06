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
HIF_BLA = "#0057b7"
GRON_NY = "#ccffcc"
GUL_ADVARSEL = "#ffff99"    
ROD_ADVARSEL = "#ffcccc"

VINDUE_DATOER = {
    "Nuværende trup": datetime.now(),
    "Sommer 26": datetime(2026, 7, 1),
    "Vinter 26": datetime(2027, 1, 1),
    "Sommer 27": datetime(2027, 7, 1),
    "Vinter 27": datetime(2028, 1, 1)
}

VINDUE_ORDEN = ["Sommer 26", "Vinter 26", "Sommer 27", "Vinter 27"]
POS_OPTS = ["", "1", "2", "3", "3.5", "4", "5", "6", "7", "8", "9", "10", "11"]

# --- 2. GITHUB & DATA LOGIK ---
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

def save_to_github(df):
    try:
        original_cols = [
            'PLAYER_WYID','DATO','NAVN','KLUB','POSITION','RATING_AVG','STATUS',
            'POTENTIALE','STYRKER','UDVIKLING','VURDERING','BESLUTSOMHED','FART',
            'AGGRESIVITET','ATTITUDE','UDHOLDENHED','LEDEREGENSKABER','TEKNIK',
            'SPILINTELLIGENS','SCOUT','KONTRAKT','PRIORITET','FORVENTNING',
            'POS_PRIORITET','POS','LON','SKYGGEHOLD','KOMMENTAR','ER_EMNE',
            'TRANSFER_VINDUE','POS_343','POS_433','POS_352','BIRTHDATE'
        ]
        _, sha = get_github_file(SCOUT_DB_PATH)
        
        export_df = df.copy()
        rev_map = {
            'Navn': 'NAVN', 'Klub': 'KLUB', 'Pos': 'POS', 
            'Transfervindue': 'TRANSFER_VINDUE', 'Emne': 'ER_EMNE', 'Skyggehold': 'SKYGGEHOLD'
        }
        export_df = export_df.rename(columns=rev_map)
        
        for col in original_cols:
            if col not in export_df.columns: export_df[col] = ""
            
        csv_content = export_df[original_cols].to_csv(index=False)
        payload = {
            "message": "Auto-update scouting data", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        requests.put(f"https://api.github.com/repos/{REPO}/contents/{SCOUT_DB_PATH}", 
                     headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        st.toast("Gemt automatisk!", icon="✅")
    except Exception as e:
        st.error(f"Fejl ved automatisk gem: {e}")

def handle_auto_save(key, df_all, source_df):
    state_key = f"editable_{key}"
    if st.session_state.get(state_key) and st.session_state[state_key].get("edited_rows"):
        changes = st.session_state[state_key]["edited_rows"]
        for idx_str, updated_cols in changes.items():
            p_name = source_df.iloc[int(idx_str)]['Navn']
            for col, val in updated_cols.items():
                df_all.loc[df_all['Navn'] == p_name, col] = val
        
        save_to_github(df_all)
        st.session_state[state_key]["edited_rows"] = {}
        st.rerun()

# --- 3. DATA PROCESSING ---
def clean_pos_val(val):
    if pd.isna(val) or val == "" or str(val).lower() == "nan": return ""
    v = str(val).replace('.0', '').strip()
    return v if v in POS_OPTS else ""

def get_status_color(val, ref_date=None):
    if ref_date is None: ref_date = datetime.now()
    try:
        if pd.isna(val): return None
        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
        if pd.isna(dt): return None
        days = (dt - ref_date).days
        if days < 0: return "#444444" 
        if days < 183: return ROD_ADVARSEL
        if days <= 365: return GUL_ADVARSEL
        return None
    except: return None

def prepare_df(content):
    if not content: return pd.DataFrame()
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    if 'NAVN' in df.columns: df = df.rename(columns={'NAVN': 'Navn'})
    
    # FIX: Tvinger positioner til rene tal-strenge uden .0
    for c in ['POS', 'POS_343', 'POS_433', 'POS_352']:
        if c in df.columns: df[c] = df[c].apply(clean_pos_val)

    if 'BIRTHDATE' in df.columns:
        df['Fødselsdato'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
        df['Alder'] = df['Fødselsdato'].apply(lambda x: f"{int(datetime.now().year - x.year)} år" if pd.notna(x) else "-")
    
    if 'KONTRAKT' in df.columns:
        df['Kontrakt'] = pd.to_datetime(df['KONTRAKT'], dayfirst=True, errors='coerce')

    col_map = {'KLUB': 'Klub', 'POS': 'Pos', 'TRANSFER_VINDUE': 'Transfervindue', 
               'ER_EMNE': 'Emne', 'SKYGGEHOLD': 'Skyggehold', 
               'POS_343': 'Pos_343', 'POS_433': 'Pos_433', 'POS_352': 'Pos_352'}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    if 'Transfervindue' in df.columns:
        df['Transfervindue'] = df['Transfervindue'].astype(str).str.strip().apply(lambda x: x if x in VINDUE_ORDEN else None)

    df['IS_HIF'] = df['Klub'].str.contains("Hvidovre", case=False, na=False)
    for c in ['Emne', 'Skyggehold']:
        if c in df.columns: df[c] = df[c].map({True:True, False:False, 'True':True, 'False':False, 1:True, 0:False}).fillna(False)
    return df

# --- 4. UI ---
def vis_side():
    st.set_page_config(layout="wide", page_title="HIF Scouting")
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, _ = get_github_file(SCOUT_DB_PATH)
    if content is None: return
    df_all = prepare_df(content)

    t1, t2, t3, t4 = st.tabs(["Emneliste", "Hvidovre IF", "Skyggeliste", "Skyggehold"])

    cfg = {
        "Kontrakt": st.column_config.DateColumn("Kontrakt", format="DD/MM/YYYY"),
        "Transfervindue": st.column_config.SelectboxColumn("Vindue", options=VINDUE_ORDEN),
        "Emne": st.column_config.CheckboxColumn("Emne"),
        "Skyggehold": st.column_config.CheckboxColumn("Skygge"),
        "Pos_343": st.column_config.SelectboxColumn("3-4-3", options=POS_OPTS),
        "Pos_433": st.column_config.SelectboxColumn("4-3-3", options=POS_OPTS),
        "Pos_352": st.column_config.SelectboxColumn("3-5-2", options=POS_OPTS)
    }

    with t1:
        source_t1 = df_all[~df_all['IS_HIF']].copy()
        vindue_map = {val: i for i, val in enumerate(VINDUE_ORDEN)}
        source_t1['sort'] = source_t1['Transfervindue'].map(vindue_map).fillna(99)
        source_t1 = source_t1.sort_values('sort').reset_index(drop=True)
        st.data_editor(source_t1[['Navn', 'Alder', 'Klub', 'Pos', 'Kontrakt', 'Transfervindue', 'Emne', 'Skyggehold']],
                       column_config=cfg, use_container_width=True, key="editable_t1", on_change=handle_auto_save, args=("t1", df_all, source_t1))

    with t2:
        source_t2 = df_all[df_all['IS_HIF']].reset_index(drop=True)
        st.data_editor(source_t2[['Navn', 'Alder', 'Klub', 'Pos', 'Kontrakt', 'Emne', 'Skyggehold']],
                       column_config=cfg, use_container_width=True, key="editable_t2", on_change=handle_auto_save, args=("t2", df_all, source_t2))

    with t3:
        source_t3 = df_all[df_all['Skyggehold'] == True].reset_index(drop=True)
        st.data_editor(source_t3[['Navn', 'Klub', 'Pos', 'Pos_343', 'Pos_433', 'Pos_352', 'Skyggehold']],
                       column_config=cfg, use_container_width=True, key="editable_t3", on_change=handle_auto_save, args=("t3", df_all, source_t3))

    with t4:
        c_pitch, c_ctrl = st.columns([8.2, 1.8])
        with c_ctrl:
            sel_v = st.selectbox("Vindue", list(VINDUE_DATOER.keys()))
            f = st.session_state.form_skygge
            for form in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(form, use_container_width=True, type="primary" if f == form else "secondary"):
                    st.session_state.form_skygge = form; st.rerun()

        with c_pitch:
            ref_dt = VINDUE_DATOER.get(sel_v, datetime.now())
            f_suffix = st.session_state.form_skygge.replace('-', '')
            p_col = f"Pos_{f_suffix}"
            
            if sel_v == "Nuværende trup":
                df_f = df_all[df_all['IS_HIF']].copy()
            else:
                hif = df_all[df_all['IS_HIF']].copy()
                emner = df_all[(df_all['Skyggehold'] == True) & (~df_all['IS_HIF']) & (df_all['Transfervindue'] == sel_v)].copy()
                hif = hif[~((hif['Kontrakt'].notna()) & (hif['Kontrakt'] < ref_dt))]
                df_f = pd.concat([hif, emner])

            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1.2)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # --- LEGENDS (AX.TEXT) ---
            ax.text(1, 3, " < 6 mdr ", size=8, weight='bold', bbox=dict(facecolor=ROD_ADVARSEL))
            ax.text(12, 3, " 6-12 mdr ", size=8, weight='bold', bbox=dict(facecolor=GUL_ADVARSEL))
            ax.text(25, 3, " Transferfri ", size=8, weight='bold', bbox=dict(facecolor=GRON_NY))
            ax.text(40, 3, " Transferkøb ", size=8, weight='bold', color='white', bbox=dict(facecolor=HIF_BLA))

            m = {"3-4-3": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(58,10,'VWB'), "6":(58,32,'DM'), "8":(58,48,'DM'), "2":(58,70,'HWB'), "11":(82,15,'VW'), "9":(100,40,'ANG'), "7":(82,65,'HW')},
                 "4-3-3": {"1":(10,40,'MM'), "5":(35,12,'VB'), "4":(30,28,'VCB'), "3":(30,52,'HCB'), "2":(35,68,'HB'), "6":(55,40,'DM'), "8":(72,25,'VCM'), "10":(72,55,'HCM'), "11":(85,15,'VW'), "9":(105,40,'ANG'), "7":(85,65,'HW')},
                 "3-5-2": {"1":(10,40,'MM'), "4":(33,22,'VCB'), "3.5":(33,40,'CB'), "3":(33,58,'HCB'), "5":(55,10,'VWB'), "6":(55,32,'DM'), "2":(55,70,'HWB'), "8":(55,48,'DM'), "10":(75,40,'CM'), "9":(102,32,'ANG'), "7":(102,48,'ANG')}}[st.session_state.form_skygge]

            for pid, (px, py, lbl) in m.items():
                ax.text(px, py-4.5, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white'))
                plist = df_f[df_f[p_col].astype(str) == str(pid)]
                for i, (_, r) in enumerate(plist.iterrows()):
                    k_c = get_status_color(r['Kontrakt'], ref_date=ref_dt)
                    txt_c, bg = "black", "white"
                    if r['IS_HIF']:
                        bg = ROD_ADVARSEL if k_c == "#444444" else (k_c if k_c else "white")
                    else:
                        if k_c in ["#444444", ROD_ADVARSEL]: bg = GRON_NY
                        else: bg, txt_c = HIF_BLA, "white"
                    ax.text(px, py + (i * 3.2), r['Navn'], size=7.5, ha='center', weight='bold', color=txt_c, bbox=dict(facecolor=bg, edgecolor="#333", alpha=0.9))
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
