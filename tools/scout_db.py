import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import uuid

# Opdateret filnavn
REPO = "Kamudinho/HIF-data"
SCOUT_FILE = "scouting_db.csv"
STATS_FILE = "data/season_stats.csv" 

# Mapping af positioner
POS_MAP = {
    1: "Målmand", 2: "HB", 3: "CB", 4: "VB", 
    5: "DM", 6: "CM", 7: "OM", 8: "HW", 
    9: "VW", 10: "ST"
}

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent Data
        scout_url = f"https://raw.githubusercontent.com/{REPO}/main/{SCOUT_FILE}?nocache={uuid.uuid4()}"
        df = pd.read_csv(scout_url, sep=None, engine='python')
        
        # Konverter positionstal til tekst
        df['Position'] = df['Position'].map(POS_MAP).fillna(df['Position'])
        
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        try:
            stats_url = f"https://raw.githubusercontent.com/{REPO}/main/{STATS_FILE}?nocache={uuid.uuid4()}"
            stats_df = pd.read_csv(stats_url, sep=None, engine='python')
        except:
            stats_df = pd.DataFrame()

        # --- FILTRERING ---
        if 'f_rating' not in st.session_state: st.session_state.f_rating = (1.0, 7.0)
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        with c2:
            with st.popover("Filtre"):
                st.session_state.f_pos = st.multiselect("Positioner", options=sorted(df['Position'].unique().tolist()))
                st.session_state.f_rating = st.slider("Rating (Snit)", 1.0, 7.0, st.session_state.f_rating, step=0.1)

        # --- DATA BEHANDLING ---
        # Beregn Hvidovre-gennemsnit (før filtrering)
        hif_avg = df[df['Klub'].str.contains('Hvidovre', case=False, na=False)]['Rating_Avg'].mean()

        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest_reports, rapport_counts, on='ID')
        
        # Anvend filtre
        if search:
            final_df = final_df[final_df['Navn'].str.contains(search, case=False) | final_df['Klub'].str.contains(search, case=False)]
        if st.session_state.f_pos:
            final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]
        
        final_df = final_df[(final_df['Rating_Avg'] >= st.session_state.f_rating[0]) & 
                            (final_df['Rating_Avg'] <= st.session_state.f_rating[1])]

        # --- HOVEDTABEL ---
        tabel_hoejde = (len(final_df) * 35) + 40
        event = st.dataframe(
            final_df[["Navn", "Position", "Klub", "Rating_Avg", "Status", "Rapporter", "Dato"]],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            height=tabel_hoejde,
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f"),
                "Dato": st.column_config.DateColumn("Seneste")
            }
        )

        # Hjælpefunktion til metrikker (HELE TAL)
        def vis_metrikker(row):
            m_cols = st.columns(4)
            metrics = [
                ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
                ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
                ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
                ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
            ]
            for i, (label, col) in enumerate(metrics):
                # .format(0.0f) sikrer at det vises som heltal
                m_cols[i % 4].metric(label, f"{int(row[col])}")

        @st.dialog("Spillerprofil", width="large")
            def vis_profil(p_data, full_df, s_df, avg_line):
                st.markdown(f"### {p_data['Navn']} | {p_data['Position']}")
                st.markdown(f"**{p_data['Klub']}**")
                st.divider()

                # Hent alle rapporter for denne spiller og sortér efter dato
                historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato', ascending=True)
                
                tab1, tab2, tab3, tab4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstatistik"])
                
                with tab1:
                    # Vis den nyeste rapport (sidste række i historikken)
                    nyeste = historik.iloc[-1]
                    vis_metrikker(nyeste)
                    st.info(f"**Seneste Vurdering:**\n\n{nyeste['Vurdering']}")

                with tab2:
                    # HER ER HISTORIEN: Vi løber baglæns gennem alle rapporter (nyeste øverst)
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"Rapport fra {row['Dato']} (Rating: {row['Rating_Avg']})"):
                            vis_metrikker(row) # Viser tallene som heltal jf. din funktion
                            st.write(f"**Vurdering:** {row['Vurdering']}")

                with tab3:
                    # Graf uden gridlines og med HIF-snit
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=historik['Dato_Str'], y=historik['Rating_Avg'],
                        mode='lines+markers', name=p_data['Navn'],
                        line=dict(color='#1f77b4', width=3)
                    ))
                    
                    if not pd.isna(avg_line):
                        fig.add_hline(y=avg_line, line_dash="dash", line_color="red", 
                                      annotation_text="HIF Snit", annotation_position="top left")
                    
                    fig.update_layout(
                        yaxis=dict(range=[1, 7], showgrid=False),
                        xaxis=dict(showgrid=False),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with tab4:
                    # Sæsonstatistik (Wyscout data)
                    if s_df.empty:
                        st.info("Ingen kampdata tilgængelig.")
                    else:
                        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.strip()
                        sp_stats = s_df[s_df['PLAYER_WYID'] == str(p_data['ID']).strip()].copy()
                        sp_stats = sp_stats.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME'])
                        
                        st.dataframe(
                            sp_stats[["SEASONNAME", "TEAMNAME", "APPEARANCES", "MINUTESPLAYED", "GOAL"]].sort_values('SEASONNAME', ascending=False),
                            use_container_width=True, hide_index=True,
                            column_config={
                                "APPEARANCES": st.column_config.NumberColumn("K", format="%d"),
                                "MINUTESPLAYED": st.column_config.NumberColumn("Min", format="%d"),
                                "GOAL": st.column_config.NumberColumn("Mål", format="%d")
                            }
                        )

            vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df, hif_avg)

    except Exception as e:
        st.error(f"Fejl: {e}")
