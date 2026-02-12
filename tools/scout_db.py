import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)
    
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        df = pd.read_csv(raw_url)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # --- FILTRERING ---
        if 'f_pos' not in st.session_state: st.session_state.f_pos = []
        if 'f_status' not in st.session_state: st.session_state.f_status = []
        if 'f_rating' not in st.session_state: st.session_state.f_rating = 1.0

        top_c1, top_c2 = st.columns([3, 1])
        with top_c1:
            search_query = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        with top_c2:
            active_filters = len(st.session_state.f_pos) + len(st.session_state.f_status) + (1 if st.session_state.f_rating > 1.0 else 0)
            with st.popover(f"Filtre ({active_filters})" if active_filters > 0 else "Filtre", use_container_width=True):
                st.session_state.f_pos = st.multiselect("Positioner", options=sorted(df['Position'].dropna().unique().tolist()), default=st.session_state.f_pos)
                st.session_state.f_status = st.multiselect("Status", options=sorted(df['Status'].dropna().unique().tolist()), default=st.session_state.f_status)
                st.session_state.f_rating = st.slider("Min. Rating", 1.0, 6.0, st.session_state.f_rating, 0.1)
                if st.button("Nulstil filtre", use_container_width=True):
                    st.session_state.f_pos, st.session_state.f_status, st.session_state.f_rating = [], [], 1.0
                    st.rerun()

        # --- ANVEND FILTRE ---
        f_df = df.copy()
        if search_query:
            f_df = f_df[f_df['Navn'].str.contains(search_query, case=False, na=False) | f_df['Klub'].str.contains(search_query, case=False, na=False)]
        if st.session_state.f_pos: f_df = f_df[f_df['Position'].isin(st.session_state.f_pos)]
        if st.session_state.f_status: f_df = f_df[f_df['Status'].isin(st.session_state.f_status)]
        f_df = f_df[f_df['Rating_Avg'] >= st.session_state.f_rating]

        # --- KLARGØR DATA ---
        latest_reports = f_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False).copy()
        
        # Vi opretter en rigtig kolonne der hedder "Vis" med teksten "Klik"
        latest_reports['Vis'] = "Klik her"

        # --- TABEL ---
        # Nu inkluderer vi 'Vis' som den første kolonne i listen
        event = st.dataframe(
            latest_reports[["Vis", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]],
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row",
            column_config={
                "Vis": st.column_config.TextColumn("Vis", width="small"),
                "Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f"),
                "Dato": st.column_config.DateColumn("Senest")
            }
        )

        # --- DIALOG (PROFIL) ---
        if len(event.selection.rows) > 0:
            @st.dialog("Spillerprofil", width="large")
            def vis_profil(player_data, full_df):
                valgt_id = player_data['ID']
                valgt_navn = player_data['Navn']
                historik = full_df[full_df['ID'] == valgt_id].sort_values('Dato')
                
                tab1, tab2, tab3 = st.tabs(["Rapport", "Historik", "Udvikling"])
                
                with tab1:
                    s = historik.iloc[-1]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Beslut.", s['Beslutsomhed']); c2.metric("Fart", s['Fart'])
                    c3.metric("Aggres.", s['Aggresivitet']); c4.metric("Attitude", s['Attitude'])
                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("Udhold.", s['Udholdenhed']); c6.metric("Leder", s['Lederegenskaber'])
                    c7.metric("Teknik", s['Teknik']); c8.metric("Intell.", s['Spilintelligens'])
                    st.divider()
                    st.info(f"**Styrker**\n\n{s['Styrker'] if str(s['Styrker']) != 'nan' else '-'}")
                    st.warning(f"**Udvikling**\n\n{s['Udvikling'] if str(s['Udvikling']) != 'nan' else '-'}")
                    st.success(f"**Vurdering**\n\n{s['Vurdering'] if str(s['Vurdering']) != 'nan' else '-'}")

                with tab2:
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"{row['Dato']} | Snit: {row['Rating_Avg']}"):
                            st.write(f"**Vurdering:** {row['Vurdering']}")

                with tab3:
                    if len(historik) < 2:
                        st.info("Kræver mindst to rapporter.")
                    else:
                        param_liste = ["Rating_Avg", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                        v_o = st.selectbox("Område", options=param_liste)
                        fig = px.line(historik, x='Dato', y=v_o, markers=True, range_y=[1, 6.5])
                        st.plotly_chart(fig, use_container_width=True)

            row_idx = event.selection.rows[0]
            vis_profil(latest_reports.iloc[row_idx], df)

    except Exception:
        st.info("Databasen er tom.")
