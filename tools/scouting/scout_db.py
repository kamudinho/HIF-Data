import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    try:
        # Tilføj tidsstempel for at undgå GitHub cache-problemer
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"Fejl ved hentning fra GitHub: {e}")
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
    # Fjerner .0 hvis ID'et er indlæst som float
    return str(val).split('.')[0].strip()

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    df_modal = alle_rapporter.copy()
    
    # Standardisering af navne for filtrering
    spiller_historik = df_modal[df_modal['NAVN'] == valgt_navn].sort_values('DATO', ascending=True)
    
    if spiller_historik.empty:
        st.error(f"Ingen data fundet for {valgt_navn}")
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
        st.write(f"Klub: {nyeste.get('KLUB', '-')} | Pos: {nyeste.get('POSITION', '-')} | ID: {pid}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']

    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys:
                val = nyeste.get(k, "-")
                st.write(f"{k.capitalize()}: {val}")
        
        with col_radar:
            r_vals = []
            for k in keys:
                try:
                    v = float(str(nyeste.get(k, 1)).replace(',', '.'))
                    r_vals.append(v)
                except: r_vals.append(1.0)
            
            fig = go.Figure(data=go.Scatterpolar(
                r=r_vals + [r_vals[0]], 
                theta=[k.capitalize() for k in keys] + [keys[0].capitalize()], 
                fill='toself', 
                line_color='#df003b'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[1, 6])), 
                showlegend=False, height=300, margin=dict(l=40,r=40,t=30,b=30)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_text:
            st.write("**Styrker**")
            st.info(nyeste.get('STYRKER', '-'))
            st.write("**Vurdering**")
            st.success(nyeste.get('VURDERING', '-'))

    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.markdown("### Rating over tid")
        fig_evol = go.Figure(go.Scatter(
            x=spiller_historik['DATO'], 
            y=spiller_historik['RATING_AVG'], 
            mode='lines+markers', 
            line_color='#df003b'
        ))
        fig_evol.update_layout(yaxis=dict(range=[1, 6]))
        st.plotly_chart(fig_evol, use_container_width=True)

    with t4:
        st.markdown("### Karriereoversigt")
        if career_df is not None:
            stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not stats.empty:
                st.dataframe(stats, use_container_width=True, hide_index=True)
            else:
                st.warning("Ingen karrieredata fundet i Wyscout-filen.")

# --- HOVEDSIDE ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente database fra GitHub.")
        return
    
    df_raw = pd.read_csv(StringIO(content), low_memory=False)
    
    # 1. Standardisering: Gør alle kolonnenavne STORE
    df_raw.columns = [c.upper().strip() for c in df_raw.columns]
    
    # 2. Sikr at de kritiske kolonner findes
    for col in ['ER_EMNE', 'SKYGGEHOLD', 'KONTRAKT', 'PLAYER_WYID', 'NAVN', 'DATO', 'RATING_AVG']:
        if col not in df_raw.columns:
            df_raw[col] = False if col in ['ER_EMNE', 'SKYGGEHOLD'] else ""

    # 3. Rens data-typer
    for col in ['ER_EMNE', 'SKYGGEHOLD']:
        df_raw[col] = df_raw[col].astype(str).str.lower().map(
            {'true': True, 'false': False, '1': True, '0': False, 'nan': False}
        ).fillna(False)

    # 4. UNIK LISTE (Vigtigt: Vi bruger PLAYER_WYID for at undgå at slette spillere med samme navn)
    df_raw = df_raw.sort_values('DATO', ascending=False)
    
    # Vi dropper dubletter, men gemmer de nyeste rapporter
    df_unique = df_raw.drop_duplicates(subset=['PLAYER_WYID']).copy()
    
    # Sorter efter kontraktudløb
    df_unique = df_unique.sort_values('KONTRAKT', ascending=True, na_position='last')

    # --- FORBERED VISNING I EDITOR ---
    # Vi vælger de kolonner vi vil vise (brug de STORE navne her)
    display_cols = ['NAVN', 'KLUB', 'RATING_AVG', 'KONTRAKT', 'ER_EMNE', 'SKYGGEHOLD']
    df_display = df_unique[display_cols].copy()
    df_display.insert(0, "SE", False)
    
    st.subheader("Scouting Database")
    
    ed_result = st.data_editor(
        df_display,
        column_config={
            "SE": st.column_config.CheckboxColumn("Profil", width="small"), 
            "ER_EMNE": st.column_config.CheckboxColumn("Emne", width="small"),
            "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", width="small"),
            "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f"),
            "KONTRAKT": st.column_config.TextColumn("Kontrakt", width="medium"),
            "NAVN": st.column_config.TextColumn("Navn", width="large"),
            "KLUB": st.column_config.TextColumn("Klub", width="medium")
        },
        disabled=['NAVN', 'KLUB', 'RATING_AVG', 'KONTRAKT'],
        hide_index=True, 
        use_container_width=True, 
        height=700,
        key=f"scout_editor_{st.session_state.editor_key}"
    )

    # --- GEM ÆNDRINGER ---
    # Hvis brugeren har klikket på Emne eller Skygge
    if not ed_result[['ER_EMNE', 'SKYGGEHOLD']].equals(df_display[['ER_EMNE', 'SKYGGEHOLD']]):
        with st.spinner("Gemmer ændringer..."):
            # Opdater hoved-dataframe baseret på ændringer i editoren
            for i, row in ed_result.iterrows():
                p_name = row['NAVN']
                df_raw.loc[df_raw['NAVN'] == p_name, ['ER_EMNE', 'SKYGGEHOLD']] = [row['ER_EMNE'], row['SKYGGEHOLD']]
            
            # Gem tilbage til GitHub
            status_code = push_to_github(FILE_PATH, "Update Emne/Skygge status", df_raw.to_csv(index=False), sha)
            if status_code in [200, 201]:
                st.success("Status opdateret!")
                time.sleep(0.5)
                st.rerun()

    # --- MODAL HÅNDTERING ---
    valgte = ed_result[ed_result["SE"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['NAVN']
        st.session_state.editor_key += 1 # Reset editor så "SE" tjekboksen nulstilles
        st.rerun()

    if st.session_state.active_player:
        billed_map = {}
        if sql_players is not None:
            billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))
        
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
