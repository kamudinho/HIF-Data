import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO
import requests
import base64
from mplsoccer import Pitch

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Vælg", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return base64.b64decode(data['content']).decode('utf-8', errors='replace'), data['sha']
    return None, None

def push_to_github(path, message, content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    return requests.put(url, headers=headers, json=payload).status_code

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, df_full):
    spiller_data = df_full[df_full['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    nyeste = spiller_data.iloc[0]
    pid = str(nyeste.get('PLAYER_WYID', '')).split('.')[0]
    
    st.subheader(valgt_navn)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(f"https://cdn5.wyscout.com/photos/players/public/{pid}.png", width=150, fallback="https://via.placeholder.com/150")
    with col2:
        st.write(f"**Klub:** {nyeste.get('KLUB', '-')}")
        st.write(f"**Rating:** {nyeste.get('RATING_AVG', 0)}")
        st.write(f"**Prioritet:** {nyeste.get('PRIORITET', '-')}")
    st.write(f"**Vurdering:** {nyeste.get('VURDERING', '-')}")

def vis_side():
    st.set_page_config(page_title="HIF Scouting", layout="wide")
    if "active_player" not in st.session_state: st.session_state.active_player = None
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    content, sha = get_github_file(DB_PATH)
    if not content: return

    df_raw = pd.read_csv(StringIO(content))
    # Standardiser kolonner internt
    df = df_raw.copy()
    col_map = {c.upper().strip(): c for c in df.columns}
    
    # Hjælper til at finde kolonner uanset case
    def gc(target): return col_map.get(target.upper(), target)

    df['Navn'] = df[gc('Navn')]
    df['KLUB'] = df[gc('KLUB')].fillna('Ukendt')
    df['DATO'] = pd.to_datetime(df[gc('DATO')], errors='coerce')
    df['RATING_AVG'] = pd.to_numeric(df[gc('RATING_AVG')], errors='coerce').fillna(0)
    
    # Robust Skyggehold-tjek
    def to_bool(val): return str(val).lower().strip() in ['true', '1', 'yes']
    df['SKYGGE_BOOL'] = df[gc('SKYGGEHOLD')].apply(to_bool)

    # Unik liste
    df_unique = df.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()

    t1, t2, t3, t4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # --- TAB 1 & 2: LISTER ---
    for tab, is_hif, key in [(t1, False, "emner"), (t2, True, "hif")]:
        with tab:
            if is_hif:
                data = df_unique[df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)]
            else:
                data = df_unique[~df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)]
            
            if data.empty:
                st.info("Ingen spillere fundet.")
                continue

            df_editor = data[['Navn', 'KLUB', 'RATING_AVG', 'SKYGGE_BOOL']].copy()
            df_editor.insert(0, "Se", False)
            
            ed = st.data_editor(
                df_editor,
                column_config={"Se": st.column_config.CheckboxColumn("Profil", width="small"), "SKYGGE_BOOL": st.column_config.CheckboxColumn("Skygge", width="small")},
                disabled=['Navn', 'KLUB', 'RATING_AVG'], hide_index=True, use_container_width=True, key=f"ed_{key}"
            )

            if not ed['SKYGGE_BOOL'].equals(df_editor['SKYGGE_BOOL']):
                for idx, row in ed.iterrows():
                    df_raw.loc[df_raw[gc('Navn')] == row['Navn'], gc('SKYGGEHOLD')] = row['SKYGGE_BOOL']
                push_to_github(DB_PATH, "Update Skygge", df_raw.to_csv(index=False), sha)
                st.rerun()

            if ed["Se"].any():
                st.session_state.active_player = ed[ed["Se"] == True].iloc[-1]["Navn"]
                st.rerun()

    # --- TAB 3: SKYGGELISTE (TAKTISK) ---
    with t3:
        df_s = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        if not df_s.empty:
            t_cols = [gc('POS_343'), gc('POS_433'), gc('POS_352')]
            # Rens talværdier (3.5 -> "3.5")
            for c in t_cols:
                df_s[c] = df_s[c].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x).replace('nan', '0')

            ed_s = st.data_editor(
                df_s[['Navn'] + t_cols],
                column_config={c: st.column_config.SelectboxColumn(c.split('_')[-1], options=list(POS_OPTIONS.keys())) for c in t_cols},
                disabled=['Navn'], hide_index=True, use_container_width=True
            )
            
            if not ed_s[t_cols].equals(df_s[t_cols]):
                for _, row in ed_s.iterrows():
                    df_raw.loc[df_raw[gc('Navn')] == row['Navn'], t_cols] = row[t_cols].values
                push_to_github(DB_PATH, "Update Taktik", df_raw.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Ingen spillere markeret som Skygge.")

    # --- TAB 4: BANEVISNING ---
    with t4:
        df_pitch_data = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        f = st.session_state.form_skygge
        p_col = gc(f"POS_{f.replace('-', '')}")
        
        c1, c2 = st.columns([5, 1])
        with c2:
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, type="primary" if f == opt else "secondary", use_container_width=True):
                    st.session_state.form_skygge = opt
                    st.rerun()
        with c1:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
            fig, ax = pitch.draw(figsize=(10, 7))
            
            if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
            elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                # Match spillere
                players = df_pitch_data[df_pitch_data[p_col].astype(str).str.startswith(str(pid))]
                for i, (_, p) in enumerate(players.iterrows()):
                    ax.text(x, y+(i*4), p['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8, boxstyle='square,pad=0.1'))
            st.pyplot(fig)

    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, df)
        st.session_state.active_player = None

if __name__ == "__main__":
    vis_side()
