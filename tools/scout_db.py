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
        # Vi beholder datoen som tekst til grafen for at undgå tidslinje-skalering
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

        # --- MASTER-TABEL (INGEN SCROLL) ---
        # Vi beregner højden dynamisk: (antal rækker * 35px) + 40px til header
        tabel_hoejde = (len(final_df) * 35) + 40
        
        event = st.dataframe(
            final_df[["Navn", "Position", "Klub", "Rating_Avg", "Status", "Rapporter", "Dato"]],
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row",
            height=tabel_hoejde, # Dette fjerner scroll i scroll
            column_config={
                "_selected": st.column_config.CheckboxColumn("Vis", width="small"),
                "Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f"),
                "Rapporter": st.column_config.NumberColumn("Rapporter", format="%d"),
                "Dato": st.column_config.DateColumn("Seneste")
            }
        )

        def vis_metrikker(data_row):
            st.markdown("**Parametre**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Beslutsomhed", data_row['Beslutsomhed'])
            c2.metric("Fart", data_row['Fart'])
            c3.metric("Aggresivitet", data_row['Aggresivitet'])
            c4.metric("Attitude", data_row['Attitude'])
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Udholdenhed", data_row['Udholdenhed'])
            c6.metric("Lederegenskaber", data_row['Lederegenskaber'])
            c7.metric("Teknik", data_row['Teknik'])
            c8.metric("Spilintelligens", data_row['Spilintelligens'])
            st.divider()

        # --- DIALOG (PROFIL) ---
        if len(event.selection.rows) > 0:
            @st.dialog("Spillerprofil", width="large")
            def vis_profil(player_data, full_df):
                valgt_id = player_data['ID']
                # Sorter historik kronologisk for grafen
                historik = full_df[full_df['ID'] == valgt_id].sort_values('Dato')
                
                tab1, tab2, tab3 = st.tabs(["Seneste Rapport", "Historik", "Udvikling"])
                
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
                        
                        # GRAF UDEN TIDS-SKALERING (Bruger Dato_Str som kategori)
                        fig = px.line(
                            historik, 
                            x='Dato_Str', 
                            y=v_o, 
                            markers=True, 
                            range_y=[0.5, 6.5],
                            labels={'Dato_Str': 'Rapport Dato', v_o: 'Score'}
                        )
                        fig.update_xaxes(type='category') # Tvinger grafen til kun at vise rapport-datoer
                        st.plotly_chart(fig, use_container_width=True)

            row_idx = event.selection.rows[0]
            vis_profil(final_df.iloc[row_idx], df)

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
