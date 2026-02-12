import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

# Stier til dine filer
REPO = "Kamudinho/HIF-data"
SCOUT_FILE = "scouting_db.csv"
STATS_FILE = "data/season_stats.csv"

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent Scouting Data
        scout_url = f"https://raw.githubusercontent.com/{REPO}/main/{SCOUT_FILE}?nocache={uuid.uuid4()}"
        df = pd.read_csv(scout_url, sep=None, engine='python') # sep=None håndterer både , og ;
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # 2. Hent Sæsonstatistik Data
        try:
            stats_url = f"https://raw.githubusercontent.com/{REPO}/main/{STATS_FILE}?nocache={uuid.uuid4()}"
            # VIGTIGT: sep=None gør at den kan læse din SQL-fil uanset format
            stats_df = pd.read_csv(stats_url, sep=None, engine='python')
        except:
            stats_df = pd.DataFrame()

        # --- FILTRERING OG HOVEDTABEL ---
        # (Din eksisterende kode her er fin...)
        if 'f_pos' not in st.session_state: st.session_state.f_pos = []
        if 'f_status' not in st.session_state: st.session_state.f_status = []
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        with c2:
            with st.popover("Filtre"):
                st.session_state.f_pos = st.multiselect("Positioner", options=sorted(df['Position'].dropna().unique().tolist()))
                st.session_state.f_status = st.multiselect("Status", options=sorted(df['Status'].dropna().unique().tolist()))

        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest_reports, rapport_counts, on='ID')
        
        if search:
            final_df = final_df[final_df['Navn'].str.contains(search, case=False)]
        if st.session_state.f_pos:
            final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]

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
                        st.info("Sæsonstatistik kunne ikke indlæses fra GitHub.")
                    else:
                        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.strip()
                        valgt_id = str(p_data['ID']).strip()
                        
                        spiller_historik = s_df[s_df['PLAYER_WYID'] == valgt_id].copy()
                        
                        # VIGTIGT: Fjerner dubletter fra SQL-joinet
                        spiller_historik = spiller_historik.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME'])
                        
                        if spiller_historik.empty:
                            st.warning(f"Ingen kampdata fundet for ID: {valgt_id}")
                        else:
                            st.markdown(f"**Sæsonoverblik: {p_data['Navn']}**")
                            
                            # Opdateret med dine præcise kolonnenavne fra Wyscout
                            vis_cols = ["SEASONNAME", "TEAMNAME", "APPEARANCES", "MINUTESPLAYED", "GOAL"]
                            eksisterende = [c for c in vis_cols if c in spiller_historik.columns]
                            
                            st.dataframe(
                                spiller_historik[eksisterende].sort_values('SEASONNAME', ascending=False),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "SEASONNAME": "Sæson",
                                    "TEAMNAME": "Klub",
                                    "APPEARANCES": st.column_config.NumberColumn("K", format="%d"),
                                    "MINUTESPLAYED": st.column_config.NumberColumn("Min", format="%d"),
                                    "GOAL": st.column_config.NumberColumn("Mål", format="%d")
                                }
                            )

                            # --- GRAF ---
                            if "GOAL" in spiller_historik.columns:
                                st.divider()
                                graf_data = spiller_historik.sort_values('SEASONNAME')
                                fig_career = px.bar(
                                    graf_data, 
                                    x='SEASONNAME', 
                                    y='GOAL',
                                    title="Mål pr. sæson",
                                    labels={'GOAL': 'Mål', 'SEASONNAME': 'Sæson'}
                                )
                                st.plotly_chart(fig_career, use_container_width=True)

            vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df)

    except Exception as e:
        st.error(f"Der skete en fejl: {e}")
