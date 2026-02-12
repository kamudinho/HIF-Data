import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

# Stier til dine filer
REPO = "Kamudinho/HIF-data"
SCOUT_FILE = "scouting_db.csv"
STATS_FILE = "data/sæsonoverblik.csv" 

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent Scouting Data
        scout_url = f"https://raw.githubusercontent.com/{REPO}/main/{SCOUT_FILE}?nocache={uuid.uuid4()}"
        df = pd.read_csv(scout_url)
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # 2. Hent Sæsonstatistik Data
        try:
            stats_url = f"https://raw.githubusercontent.com/{REPO}/main/{STATS_FILE}?nocache={uuid.uuid4()}"
            stats_df = pd.read_csv(stats_url)
        except:
            stats_df = pd.DataFrame()

        # --- FILTRERING ---
        if 'f_pos' not in st.session_state: st.session_state.f_pos = []
        if 'f_status' not in st.session_state: st.session_state.f_status = []
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        with c2:
            with st.popover("Filtre"):
                st.session_state.f_pos = st.multiselect("Positioner", options=sorted(df['Position'].dropna().unique().tolist()))
                st.session_state.f_status = st.multiselect("Status", options=sorted(df['Status'].dropna().unique().tolist()))

        # --- DATA BEHANDLING ---
        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest_reports, rapport_counts, on='ID')
        
        if search:
            final_df = final_df[final_df['Navn'].str.contains(search, case=False)]
        if st.session_state.f_pos:
            final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]

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

        # Hjælpefunktion til metrikker
        def vis_metrikker(row):
            m_cols = st.columns(4)
            metrics = [
                ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
                ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
                ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
                ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
            ]
            for i, (label, col) in enumerate(metrics):
                m_cols[i % 4].metric(label, row[col])

        # --- DIALOG (PROFIL) ---
        if len(event.selection.rows) > 0:
            @st.dialog("Spillerprofil", width="large")
            def vis_profil(p_data, full_df, s_df):
                st.markdown(f"### {p_data['Navn']} | {p_data['Position']}")
                st.markdown(f"**{p_data['Klub']}**")
                st.caption(f"Spiller ID / PLAYER_WYID: {p_data['ID']}")
                st.divider()

                historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato')
                tab1, tab2, tab3, tab4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstatistik"])
                
                with tab1:
                    s = historik.iloc[-1]
                    vis_metrikker(s)
                    st.info(f"**Vurdering:**\n\n{s['Vurdering']}")

                with tab2:
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"Rapport fra {row['Dato']} (Rating: {row['Rating_Avg']})"):
                            vis_metrikker(row)
                            st.write(f"**Vurdering:** {row['Vurdering']}")

                with tab3:
                    fig = px.line(historik, x='Dato_Str', y='Rating_Avg', markers=True, range_y=[1, 7])
                    fig.update_xaxes(type='category', title="Dato")
                    st.plotly_chart(fig, use_container_width=True)

                with tab4:
                    if s_df.empty:
                        st.info("Filen data/sæsonoverblik.csv blev ikke fundet.")
                    else:
                        # Matcher ID mod PLAYER_WYID
                        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str)
                        spiller_stats = s_df[s_df['PLAYER_WYID'] == str(p_data['ID'])].copy()
                        
                        if spiller_stats.empty:
                            st.warning(f"Ingen kampdata fundet for PLAYER_WYID: {p_data['ID']}")
                        else:
                            st.markdown("**Kampdata (Wyscout)**")
                            vis_cols = ["KAMPE", "MINUTESONFIELD", "GOALS", "ASSISTS", "DUELS", "DUELSWON"]
                            # Sikrer at vi kun tager de kolonner der findes
                            eksisterende = [c for c in vis_cols if c in spiller_stats.columns]
                            
                            st.dataframe(
                                spiller_stats[eksisterende],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "MINUTESONFIELD": "Minutter",
                                    "GOALS": "Mål",
                                    "DUELSWON": "Dueller vundne"
                                }
                            )
                            
                            # Eksempel på avanceret data
                            with st.expander("Se avanceret data (xG, Interceptions, osv.)"):
                                adv_cols = ["XGSHOT", "XGASSIST", "INTERCEPTIONS", "PROGRESSIVEPASSES"]
                                eks_adv = [c for c in adv_cols if c in spiller_stats.columns]
                                st.write(spiller_stats[eks_adv])

            vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df)

    except Exception as e:
        st.error(f"Der skete en fejl: {e}")
