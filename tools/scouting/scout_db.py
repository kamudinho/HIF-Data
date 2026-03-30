import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import base64
from io import StringIO
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    df_modal = alle_rapporter.copy()
    mapping = {
        'KLUB': 'Klub', 'POSITION': 'Position', 'RATING_AVG': 'Rating_Avg',
        'STATUS': 'Status', 'SCOUT': 'Scout', 'DATO': 'DATO', 'POTENTIALE': 'Potentiale',
        'STYRKER': 'Styrker', 'UDVIKLING': 'Udvikling', 'VURDERING': 'Vurdering',
        'BESLUTSOMHED': 'Beslutsomhed', 'FART': 'Fart', 'AGGRESIVITET': 'Aggresivitet',
        'ATTITUDE': 'Attitude', 'UDHOLDENHED': 'Udholdenhed', 'LEDEREGENSKABER': 'Lederegenskaber',
        'TEKNIK': 'Teknik', 'SPILINTELLIGENS': 'Spilintelligens', 'PLAYER_WYID': 'PLAYER_WYID'
    }
    current_cols = {c.upper(): c for c in df_modal.columns}
    rename_dict = {current_cols[k]: v for k, v in mapping.items() if k in current_cols}
    df_modal = df_modal.rename(columns=rename_dict)

    spiller_historik = df_modal[df_modal['Navn'] == valgt_navn].sort_values('DATO', ascending=True)
    if spiller_historik.empty:
        st.error("Data ikke fundet.")
        return
        
    nyeste = spiller_historik.iloc[-1]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"Klub: {nyeste.get('Klub', '-')} | Pos: {nyeste.get('Position', '-')} | ID: {pid}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    keys = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']

    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys:
                val = nyeste.get(k, "-")
                st.write(f"{k}: {val}")
        with col_radar:
            r_vals = []
            for k in keys:
                try:
                    v = float(str(nyeste.get(k, 1)).replace(',', '.'))
                    r_vals.append(v)
                except: r_vals.append(1.0)
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=keys + [keys[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 5])), showlegend=False, height=300, margin=dict(l=40,r=40,t=30,b=30))
            st.plotly_chart(fig, use_container_width=True)
        with col_text:
            st.write("**Styrker**")
            st.info(nyeste.get('Styrker', '-'))
            st.write("**Vurdering**")
            st.success(nyeste.get('Vurdering', '-'))

    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.markdown("### Rating over tid")
        fig_evol = go.Figure(go.Scatter(x=spiller_historik['DATO'], y=spiller_historik['Rating_Avg'], mode='lines+markers', line_color='#df003b'))
        fig_evol.update_layout(yaxis=dict(range=[1, 5.5]))
        st.plotly_chart(fig_evol, use_container_width=True)

    # --- TAB 4: SÆSONSTATS (Aggregeret korrekt) ---
    with t4:
        st.markdown("### Karriereoversigt (Aggregeret)")
        if career_df is not None:
            c_df = career_df.copy()
            
            # 1. Rens ID og klargør data
            id_col = 'PLAYER_WYID' if 'PLAYER_WYID' in c_df.columns else 'wyId'
            c_df['match_id'] = c_df[id_col].apply(rens_id)
            
            # Filtrer på spilleren
            stats = c_df[c_df['match_id'] == pid].copy()
            
            if not stats.empty:
                # 2. Konverter kolonner til tal for at undgå fejl i summering
                for col in ['MATCHES', 'MINUTES', 'GOALS', 'YELLOWCARD', 'REDCARDS']:
                    if col in stats.columns:
                        stats[col] = pd.to_numeric(stats[col], errors='coerce').fillna(0)

                # 3. Definer hvordan vi runder af/samler data
                # Vi grupperer på Sæson, Hold og Turnering
                # Hvis der er dubletter, tager vi gennemsnittet eller den første værdi 
                # for at undgå at tælle 300 kampe.
                
                group_cols = ['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME']
                act_group = [c for c in group_cols if c in stats.columns]
                
                # Her er "tricket": Vi bruger .max() eller .first() hvis data 
                # i forvejen ER totaler, men optræder flere gange.
                # Hvis rækkerne er enkelte kampe, skal vi bruge .sum() - men kun på mål/minutter.
                
                stats_grouped = stats.groupby(act_group).agg({
                    'MATCHES': 'max',    # Vi tager den højeste værdi (hvis det er totaler)
                    'MINUTES': 'max',    # Vi tager den højeste værdi
                    'GOALS': 'max',      # Vi tager den højeste værdi
                    'YELLOWCARD': 'max',
                    'REDCARDS': 'max'
                }).reset_index()
                
                # Sorter efter nyeste sæson
                stats_grouped = stats_grouped.sort_values('SEASONNAME', ascending=False)

                vis_mapping = {
                    'SEASONNAME': 'Saeson',
                    'TEAMNAME': 'Hold',
                    'COMPETITIONNAME': 'Turnering',
                    'MATCHES': 'Kampe',
                    'MINUTES': 'Minutter',
                    'GOALS': 'Mål',
                    'YELLOWCARD': 'Gult',
                    'REDCARDS': 'Roedt'
                }
                
                st.dataframe(
                    stats_grouped.rename(columns=vis_mapping), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning(f"Ingen data fundet for ID: {pid}")
                
# --- HOVEDSIDE ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente database.")
        return
    
    df_raw = pd.read_csv(StringIO(content))
    
    # --- SIKKER KOLONNE-HÅNDTERING ---
    # Tving alle eksisterende kolonner til UPPERCASE for sammenligning
    df_raw.columns = [c.upper().strip() for c in df_raw.columns]
    
    # Hvis ER_EMNE mangler i CSV'en, opret den som False
    if 'ER_EMNE' not in df_raw.columns:
        df_raw['ER_EMNE'] = False

    # Mapping til de navne koden bruger internt
    mapping = {
        'PLAYER_WYID': 'PLAYER_WYID', 
        'DATO': 'DATO', 
        'NAVN': 'Navn', 
        'KLUB': 'Klub', 
        'RATING_AVG': 'Rating_Avg', 
        'ER_EMNE': 'ER_EMNE'
    }
    
    # Omdøb kun de kolonner der rent faktisk findes
    rename_dict = {k: v for k, v in mapping.items() if k in df_raw.columns}
    df_raw = df_raw.rename(columns=rename_dict)

    # Formatér data
    df_raw['DATO'] = pd.to_datetime(df_raw['DATO'], dayfirst=True, errors='coerce')
    
    # Konverter ER_EMNE til rigtige Booleans (True/False)
    df_raw['ER_EMNE'] = df_raw['ER_EMNE'].astype(str).str.lower().map(
        {'true': True, 'false': False, '1': True, '0': False, 'nan': False}
    ).fillna(False)
    
    # Lav unik oversigt (nyeste rapport pr. spiller)
    df_unique = df_raw.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    df_unique['Dato_Visning'] = df_unique['DATO'].dt.date

    # Forbered visning til data_editor
    df_display = df_unique[['Navn', 'Klub', 'Rating_Avg', 'Dato_Visning', 'ER_EMNE']].copy()
    df_display.insert(0, "Se", False)
    
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Se Profil", width="small"), 
            "ER_EMNE": st.column_config.CheckboxColumn("Emne", width="small"),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        disabled=['Navn', 'Klub', 'Rating_Avg', 'Dato_Visning'],
        hide_index=True, 
        use_container_width=True, 
        height=600,
        key=f"scout_editor_{st.session_state.editor_key}"
    )

    # Gem ændringer i "ER_EMNE" (Tjek om noget er ændret)
    if not ed_result['ER_EMNE'].equals(df_display['ER_EMNE']):
        with st.spinner("Opdaterer emne-status på GitHub..."):
            for _, row in ed_result.iterrows():
                df_raw.loc[df_raw['Navn'] == row['Navn'], 'ER_EMNE'] = row['ER_EMNE']
            
            # Gem med de oprindelige UPPERCASE navne for at bevare konsistens
            df_to_save = df_raw.copy()
            # Vend mapping om for at få de rigtige navne tilbage til CSV
            reverse_map = {v: k for k, v in mapping.items()}
            df_to_save = df_to_save.rename(columns=reverse_map)
            
            push_to_github(FILE_PATH, "Update ER_EMNE status", df_to_save.to_csv(index=False), sha)
            st.rerun()

    # Håndter "Se Profil" klik
    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['Navn']
        st.session_state.editor_key += 1 # Reset editor for at fjerne tjekket i "Se"
        st.rerun()

    if st.session_state.active_player:
        billed_map = {}
        if sql_players is not None:
            billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
