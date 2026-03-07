import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
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
        st.write(f"Klub: {nyeste.get('Klub', 'Ukendt')} | Pos: {nyeste.get('Position', 'Ukendt')}")
        st.write(f"Rating: {nyeste.get('Rating_Avg', 0)} | Potentiale: {nyeste.get('Potentiale', '-')}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    keys = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
    labels = ['Beslut.', 'Fart', 'Aggres.', 'Attitude', 'Udhold.', 'Leder', 'Teknik', 'Intell.']

    # --- TAB 1: SENESTE RAPPORT ---
    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys:
                st.write(f"**{k}:** {nyeste.get(k, 1)}")
        with col_radar:
            r_vals = [float(str(nyeste.get(k, 1)).replace(',', '.')) for k in keys]
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=labels + [labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=300, margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col_text:
            st.success(f"**Styrker**\n\n{nyeste.get('Styrker', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('Udvikling', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('Vurdering', '-')}")

    # --- TAB 2: HISTORIK ---
    with t2:
        for idx, rapport in spiller_historik.iterrows():
            with st.expander(f"Rapport fra {rapport['Dato']}", expanded=(idx == spiller_historik.index[0])):
                cols = st.columns(len(keys))
                for i, k in enumerate(keys):
                    cols[i].metric(labels[i], rapport.get(k, 1))
                st.write("---")
                h1, h2, h3 = st.columns(3)
                h1.markdown(f"**Styrker:**\n{rapport.get('Styrker', '-')}")
                h2.markdown(f"**Udvikling:**\n{rapport.get('Udvikling', '-')}")
                h3.markdown(f"**Vurdering:**\n{rapport.get('Vurdering', '-')}")

    # --- TAB 3: UDVIKLING ---
    with t3:
        hist_evo = spiller_historik.sort_values('Dato')
        fig_evo = go.Figure()
        fig_evo.add_trace(go.Scatter(x=hist_evo['Dato'], y=hist_evo['Rating_Avg'], mode='lines+markers', line_color='#df003b'))
        fig_evo.update_layout(yaxis=dict(range=[1, 6]), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_evo, use_container_width=True)

    # --- TAB 4: SÆSONSTATS (PLAYER_CAREER) ---
    with t4:
        if career_df is not None:
            # 1. Forbered data
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            
            # 2. Filtrér på PLAYER_WYID
            p_stats = cdf[cdf['PLAYER_WYID'].apply(rens_id) == pid].copy()
            
            if not p_stats.empty:
                # 3. Aggregér data så hver sæson/hold/turnering kun optræder én gang
                # Vi bruger sum() på de numeriske værdier
                agg_stats = p_stats.groupby(['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME']).agg({
                    'MATCHES': 'sum',
                    'MINUTES': 'sum',
                    'GOALS': 'sum',
                    'YELLOWCARD': 'sum',
                    'REDCARDS': 'sum'
                }).reset_index()

                # Sortér så nyeste sæson er øverst
                agg_stats = agg_stats.sort_values('SEASONNAME', ascending=False)

                # Omdøb til dansk visning
                mapping = {
                    'SEASONNAME': 'Sæson',
                    'TEAMNAME': 'Hold',
                    'COMPETITIONNAME': 'Turnering',
                    'MATCHES': 'Kampe',
                    'MINUTES': 'Min.',
                    'GOALS': 'Mål',
                    'YELLOWCARD': 'Gule',
                    'REDCARDS': 'Røde'
                }
                st.dataframe(agg_stats.rename(columns=mapping), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen historisk karrierestatistik fundet.")

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    try:
        df_raw = pd.read_csv('data/scouting_db.csv')
        df_raw['PLAYER_WYID'] = df_raw['PLAYER_WYID'].apply(rens_id)
        df_raw['Dato'] = pd.to_datetime(df_raw['Dato'])
        df_unique = df_raw.sort_values('Dato', ascending=False).drop_duplicates('Navn').copy()
        df_unique['Dato'] = df_unique['Dato'].dt.date
    except:
        return

    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    df_display = df_unique[['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato']].copy()
    df_display.insert(0, "Se", False)

    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        disabled=['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato'],
        hide_index=True,
        use_container_width=True,
        key=f"editor_v{st.session_state.editor_key}"
    )

    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['Navn']
        st.session_state.editor_key += 1
        st.rerun()

    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
