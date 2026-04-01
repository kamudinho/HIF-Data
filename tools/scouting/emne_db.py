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
    else:
        df['TRANSFER_VINDUE'] = "Nuværende trup" if is_hif else "Sommer 26"

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

# --- NY FUNKTION: FIXER DUBLETTER I STATS ---
def vis_spiller_profil(player_row, df_all):
    st.markdown(f"## {player_row['Navn']}")
    st.write(f"**Klub:** {player_row.get('KLUB', 'Ukendt')} | **Pos:** {player_row.get('POSITION', 'N/A')} | **ID:** {player_row.get('PLAYER_WYID', '0')}")
    
    tab_rap, tab_his, tab_udv, tab_stats = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    with tab_stats:
        st.write("### Karriereoversigt")
        # Filtrer alle rækker for denne spiller
        p_id = player_row.get('PLAYER_WYID')
        if p_id:
            stats_df = df_all[df_all['PLAYER_WYID'] == p_id].copy()
            
            # KRITISK FIX: Fjern dubletter så hver sæson/klub kun vises én gang
            cols_to_show = ['PLAYER_WYID', 'SEASONNAME', 'COMPETITIONNAME', 'TEAMNAME', 'MATCHES', 'MINUTES', 'GOALS', 'YELLOWCARD', 'REDCARDS']
            # Vi fjerner dubletter baseret på de unikke sæson-nøgler
            display_stats = stats_df.drop_duplicates(subset=['SEASONNAME', 'COMPETITIONNAME', 'TEAMNAME'])
            
            # Sikr at kolonnerne findes før visning
            available_cols = [c for c in cols_to_show if c in display_stats.columns]
            st.dataframe(display_stats[available_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("Intet Player ID fundet - kan ikke hente stats.")

def vis_side():
    st.markdown("<style>.stAppViewBlockContainer { padding-top: 0px !important; } div.block-container { padding-top: 0.5rem !important; max-width: 98% !important; }</style>", unsafe_allow_html=True)
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    s_c, s_sha = get_github_file(SCOUT_DB_PATH)
    h_c, h_sha = get_github_file(HIF_PATH)
    
    df_scout = prepare_df(s_c, is_hif=False)
    df_hif = prepare_df(h_c, is_hif=True)

    # Master liste til visning og stats
    all_players_full = pd.concat([df_scout, df_hif], ignore_index=True)
    # Deduplikeret liste til selve oversigterne
    all_players_unique = all_players_full.drop_duplicates(subset=['Navn'], keep='first')

    _, t_col2 = st.columns([4, 1])
    sel_v = t_col2.selectbox("Vindue", VINDUE_OPTIONS_GLOBAL, key="global_v_sel", index=1)

    tabs = st.tabs(["Emner", "Hvidovre IF", "Skyggeliste", "Bane"])

    # Editør sektion (forkortet for overblik, men bibeholder din logik)
    with tabs[0]: # Emner
        df_emne = all_players_unique[(all_players_unique['ER_EMNE']==True) & (all_players_unique['IS_HIF']==False)]
        if not df_emne.empty:
            # Her kan du klikke på en række for at åbne profil (hvis du har implementeret det)
            # Men for nu fixer vi selve data-strukturen
            st.data_editor(df_emne.set_index('Navn')[['TRANSFER_VINDUE', 'POS', 'SKYGGEHOLD']], use_container_width=True)

    # Bane sektion
    with tabs[3]:
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        if sel_v == "Nuværende trup":
            df_f = all_players_unique[all_players_unique['IS_HIF'] == True]
        else:
            h_s = all_players_unique[(all_players_unique['IS_HIF'] == True) & (all_players_unique['SKYGGEHOLD'] == True)]
            e_s = all_players_unique[(all_players_unique['IS_HIF'] == False) & (all_players_unique['SKYGGEHOLD'] == True) & (all_players_unique['TRANSFER_VINDUE'] == sel_v)]
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
                    # Hvis man klikker her, kunne man kalde vis_spiller_profil(p_row, all_players_full)
                    ax.text(x, y + (i * 2.3), f"{p_row['Navn']}{'*' if is_new else ''}", size=7, ha='center', va='center', weight='bold', bbox=dict(facecolor=GRON_NY if is_new else "white", edgecolor="#333", alpha=0.8, boxstyle='square,pad=0.2'))
            st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
