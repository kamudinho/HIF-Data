import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    # Find historik for den specifikke spiller
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('Dato', ascending=False)
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', 'Ukendt')} | **Pos:** {nyeste.get('Position', 'Ukendt')}")
        st.write(f"**Rating:** {nyeste.get('Rating_Avg', 0)} ⭐ | **Potentiale:** {nyeste.get('Potentiale', '-')}")

    t1, t2, t3, t4 = st.tabs(["📊 Seneste & Radar", "📜 Historik", "📈 Udvikling", "⚽ Stats"])
    
    with t1:
        col_t, col_r = st.columns([1, 1.2])
        with col_t:
            st.markdown(f"**Dato for rapport:** {nyeste.get('Dato')}")
            st.success(f"**Styrker:**\n\n{nyeste.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{nyeste.get('Vurdering', '-')}")
            st.warning(f"**Fokus:**\n\n{nyeste.get('Udvikling', '-')}")
        with col_r:
            keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            r_vals = []
            for k in keys:
                try:
                    v = float(str(nyeste.get(k, 0)).replace(',', '.'))
                    r_values.append(v if v > 0 else 0.1)
                except: r_vals.append(0.1)
            
            # (Radar plot logik her...)
            # For overskuelighedens skyld udeladt i dette snippet, men bibeholdt i din fil

    with t2:
        st.dataframe(spiller_historik[['Dato', 'Rating_Avg', 'Status', 'Vurdering', 'Scout']], use_container_width=True, hide_index=True)

    with t3:
        hist_evo = spiller_historik.sort_values('Dato')
        st.line_chart(hist_evo.set_index('Dato')['Rating_Avg'])

    with t4:
        if career_df is not None:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            st.dataframe(p_stats[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], use_container_width=True, hide_index=True)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    st.markdown("### 📋 Scouting Database")

    # 1. Hent og forbered data
    try:
        df_raw = pd.read_csv('data/scouting_db.csv')
        df_raw['PLAYER_WYID'] = df_raw['PLAYER_WYID'].apply(rens_id)
        df_raw['Dato'] = pd.to_datetime(df_raw['Dato'])
        df_unique = df_raw.sort_values('Dato', ascending=False).drop_duplicates('Navn').copy()
        df_unique['Dato'] = df_unique['Dato'].dt.date
    except:
        st.error("Kunne ikke indlæse databasen.")
        return

    # 2. Billeder
    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # 3. SINGLE-SELECT LOGIK via Session State
    if "sidste_valgte_navn" not in st.session_state:
        st.session_state.sidste_valgte_navn = None

    # Tilføj 'Se' kolonne (default False)
    df_display = df_unique[['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato']].copy()
    df_display.insert(0, "Se", False)

    # Vis editor
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f ⭐")
        },
        disabled=['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato'],
        hide_index=True,
        use_container_width=True,
        key="db_single_select"
    )

    # 4. Tjek for nye valg og håndter "Single Select"
    aktuelle_valg = ed_result[ed_result["Se"] == True]
    
    if not aktuelle_valg.empty:
        nyeste_valg = aktuelle_valg.iloc[-1]['Navn'] # Tag den sidste i listen hvis flere er valgt
        
        # Hvis det er en ny spiller, eller vi ikke har åbnet den endnu
        if nyeste_valg != st.session_state.sidste_valgte_navn:
            st.session_state.sidste_valgte_navn = nyeste_valg
            vis_spiller_modal(nyeste_valg, billed_map, career_df, df_raw)
            
            # Knap til at rydde alt, så tabellen nulstilles helt
            if st.button("Luk profil og ryd alle markeringer", use_container_width=True):
                st.session_state.sidste_valgte_navn = None
                st.rerun()
