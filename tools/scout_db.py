import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

# Stier til dine filer
REPO = "Kamudinho/HIF-data"
SCOUT_FILE = "scouting_db.csv"
STATS_FILE = "data/sæsonoverblik.csv" # Din nye fil

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    try:
        # Hent Scouting Data
        scout_url = f"https://raw.githubusercontent.com/{REPO}/main/{SCOUT_FILE}?nocache={uuid.uuid4()}"
        df = pd.read_csv(scout_url)
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # Hent Sæsonstatistik Data (Kampdata)
        try:
            stats_url = f"https://raw.githubusercontent.com/{REPO}/main/{STATS_FILE}?nocache={uuid.uuid4()}"
            stats_df = pd.read_csv(stats_url)
        except:
            stats_df = pd.DataFrame() # Tom hvis filen mangler

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

        # --- TABEL ---
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

        # --- DIALOG (PROFIL) ---
        if len(event.selection.rows) > 0:
            @st.dialog("Spillerprofil", width="large")
            def vis_profil(p_data, full_df, s_df):
                st.markdown(f"### {p_data['Navn']} | {p_data['Position']}")
                st.markdown(f"**{p_data['Klub']}**")
                st.caption(f"Spiller ID: {p_data['ID']}")
                st.divider()

                historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato')
                tab1, tab2, tab3, tab4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstatistik"])
                
                with tab1:
                    s = historik.iloc[-1]
                    # Metrikker her (forkortet for overblik)
                    st.info(f"**Vurdering:** {s['Vurdering']}")

                with tab2:
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"Rapport fra {row['Dato']}"):
                            st.write(row['Vurdering'])

                with tab3:
                    fig = px.line(historik, x='Dato_Str', y='Rating_Avg', markers=True, range_y=[1, 6.5])
                    fig.update_xaxes(type='category')
                    st.plotly_chart(fig, use_container_width=True)

                with tab4:
    if s_df.empty:
        st.info("Kunne ikke finde filen: data/sæsonoverblik.csv")
    else:
        # Vi sikrer os at begge ID-kolonner behandles som strenge for at undgå match-fejl
        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str)
        valgt_id = str(p_data['ID'])
        
        # Filtrer data baseret på PLAYER_WYID
        spiller_stats = s_df[s_df['PLAYER_WYID'] == valgt_id].copy()
        
        if spiller_stats.empty:
            st.warning(f"Ingen kampdata fundet i systemet for PLAYER_WYID: {valgt_id}")
            # Lille hjælper til fejlfinding
            if st.checkbox("Vis alle tilgængelige ID'er i filen"):
                st.write(s_df['PLAYER_WYID'].unique())
        else:
            st.markdown(f"**Officiel Kampstatistik (Wyscout Data)**")
            
            # Vi udvælger de kolonner du bad om fra din lange liste
            # Bemærk: 'KAMPE' og 'MINUTESONFIELD' matcher dine kolonnenavne
            vis_df = spiller_stats[[
                "KAMPE", 
                "MINUTESONFIELD", 
                "GOALS", 
                "ASSISTS", 
                "DUELS", 
                "DUELSWON"
            ]].copy()
            
            # Beregn duelseffektivitet i % hvis du vil have det mere læseligt
            try:
                vis_df['DUEL_%'] = (vis_df['DUELSWON'] / vis_df['DUELS'] * 100).round(1).astype(str) + '%'
            except:
                vis_df['DUEL_%'] = "N/A"

            st.dataframe(
                vis_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "KAMPE": st.column_config.NumberColumn("Kampe", format="%d"),
                    "MINUTESONFIELD": st.column_config.NumberColumn("Minutter", format="%d"),
                    "GOALS": st.column_config.NumberColumn("Mål", format="%d"),
                    "ASSISTS": st.column_config.NumberColumn("Assists", format="%d"),
                    "DUELS": st.column_config.NumberColumn("Dueller (Total)", format="%d"),
                    "DUEL_%": st.column_config.TextColumn("Vundne %")
                }
            )
            
            # Avanceret overblik (Eksempel på hvordan vi kan bruge din store datamængde)
            with st.expander("Se udvidet data (Passes, XG, osv.)"):
                adv_cols = ["PASSES", "SUCCESSFULPASSES", "XGSHOT", "XGASSIST", "INTERCEPTIONS"]
                eksisterende = [c for c in adv_cols if c in spiller_stats.columns]
                st.write(spiller_stats[eksisterende])
            vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df)

    except Exception as e:
        st.error(f"Fejl: {e}")
