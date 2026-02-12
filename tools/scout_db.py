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
        df['Dato_Str'] = df['Dato'].astype(str)
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

        # --- DATA BEHANDLING ---
        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest_reports, rapport_counts, on='ID')
        
        if search_query:
            final_df = final_df[final_df['Navn'].str.contains(search_query, case=False, na=False) | final_df['Klub'].str.contains(search_query, case=False, na=False)]
        if st.session_state.f_pos: final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]
        if st.session_state.f_status: final_df = final_df[final_df['Status'].isin(st.session_state.f_status)]
        final_df = final_df[final_df['Rating_Avg'] >= st.session_state.f_rating]
        final_df = final_df.sort_values('Dato', ascending=False)

        # --- MASTER-TABEL (DYNAMISK HØJDE) ---
        tabel_hoejde = (len(final_df) * 35) + 40
        
        event = st.dataframe(
            final_df[["Navn", "Position", "Klub", "Rating_Avg", "Status", "Rapporter", "Dato"]],
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row",
            height=tabel_hoejde,
            column_config={
                "_selected": st.column_config.CheckboxColumn("Vis", width="small"),
                "Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f"),
                "Rapporter": st.column_config.NumberColumn("Rapporter", format="%d"),
                "Dato": st.column_config.DateColumn("Seneste")
            }
        )

        def vis_metrikker(data_row, title="Parametre"):
            st.markdown(f"**{title}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Beslutsomhed", f"{data_row['Beslutsomhed']:.1f}" if isinstance(data_row['Beslutsomhed'], float) else data_row['Beslutsomhed'])
            c2.metric("Fart", f"{data_row['Fart']:.1f}" if isinstance(data_row['Fart'], float) else data_row['Fart'])
            c3.metric("Aggresivitet", f"{data_row['Aggresivitet']:.1f}" if isinstance(data_row['Aggresivitet'], float) else data_row['Aggresivitet'])
            c4.metric("Attitude", f"{data_row['Attitude']:.1f}" if isinstance(data_row['Attitude'], float) else data_row['Attitude'])
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Udholdenhed", f"{data_row['Udholdenhed']:.1f}" if isinstance(data_row['Udholdenhed'], float) else data_row['Udholdenhed'])
            c6.metric("Lederegenskaber", f"{data_row['Lederegenskaber']:.1f}" if isinstance(data_row['Lederegenskaber'], float) else data_row['Lederegenskaber'])
            c7.metric("Teknik", f"{data_row['Teknik']:.1f}" if isinstance(data_row['Teknik'], float) else data_row['Teknik'])
            c8.metric("Spilintelligens", f"{data_row['Spilintelligens']:.1f}" if isinstance(data_row['Spilintelligens'], float) else data_row['Spilintelligens'])
            st.divider()

        # --- DIALOG (PROFIL) ---
        if len(event.selection.rows) > 0:
            @st.dialog("Spillerprofil", width="large")
            def vis_profil(p_data, full_df):
                # Header layout
                st.markdown(f"### {p_data['Navn']} | {p_data['Position']}")
                st.markdown(f"**{p_data['Klub']}**")
                st.caption(f"Spiller ID: {p_data['ID']}")
                st.divider()

                historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato')
                
                tab1, tab2, tab3, tab4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstatistik"])
                
                with tab1:
                    s = historik.iloc[-1]
                    vis_metrikker(s)
                    st.info(f"**Styrker**\n\n{s['Styrker']}")
                    st.warning(f"**Udvikling**\n\n{s['Udvikling']}")
                    st.success(f"**Vurdering**\n\n{s['Vurdering']}")

                with tab2:
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"Rapport fra {row['Dato']} | Snit: {row['Rating_Avg']}"):
                            vis_metrikker(row)
                            st.write(f"**Vurdering:** {row['Vurdering']}")

                with tab3:
                    if len(historik) < 2:
                        st.info("Kræver mindst to rapporter.")
                    else:
                        param_liste = ["Rating_Avg", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                        v_o = st.selectbox("Vælg område", options=param_liste)
                        fig = px.line(historik, x='Dato_Str', y=v_o, markers=True, range_y=[0.5, 6.5])
                        fig.update_xaxes(type='category')
                        st.plotly_chart(fig, use_container_width=True)

                with tab4:
                    st.markdown("**Gennemsnit af alle rapporter i denne sæson**")
                    # Beregn gennemsnit for denne specifikke spiller
                    avg_stats = historik[["Rating_Avg", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]].mean()
                    
                    # Vis det i det velkendte metrik-format
                    vis_metrikker(avg_stats, title=f"Sæsongennemsnit ({len(historik)} rapporter)")
                    
                    st.metric("Samlet Sæson Snit", f"{avg_stats['Rating_Avg']:.2f}")

            row_idx = event.selection.rows[0]
            vis_profil(final_df.iloc[row_idx], df)

    except Exception as e:
        st.info("Databasen er tom.")
