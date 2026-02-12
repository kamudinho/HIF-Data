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
            filter_label = f"Filtre ({active_filters})" if active_filters > 0 else "Filtre"
            with st.popover(filter_label, use_container_width=True):
                all_positions = sorted(df['Position'].dropna().unique().tolist())
                st.session_state.f_pos = st.multiselect("Positioner", options=all_positions, default=st.session_state.f_pos)
                all_status = sorted(df['Status'].dropna().unique().tolist())
                st.session_state.f_status = st.multiselect("Status", options=all_status, default=st.session_state.f_status)
                st.session_state.f_rating = st.slider("Min. Rating", 1.0, 6.0, st.session_state.f_rating, 0.1)
                if st.button("Nulstil filtre", use_container_width=True):
                    st.session_state.f_pos, st.session_state.f_status, st.session_state.f_rating = [], [], 1.0
                    st.rerun()

        f_df = df.copy()
        if search_query:
            f_df = f_df[f_df['Navn'].str.contains(search_query, case=False, na=False) | f_df['Klub'].str.contains(search_query, case=False, na=False)]
        if st.session_state.f_pos: f_df = f_df[f_df['Position'].isin(st.session_state.f_pos)]
        if st.session_state.f_status: f_df = f_df[f_df['Status'].isin(st.session_state.f_status)]
        f_df = f_df[f_df['Rating_Avg'] >= st.session_state.f_rating]

        latest_reports = f_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)
        
        # --- TABEL MED VALG ---
        event = st.dataframe(
            latest_reports[["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]],
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row",
            column_config={"Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f")}
        )

        # --- AUTOMATISK ÅBNING AF PROFIL ---
        if len(event.selection.rows) > 0:
            row_idx = event.selection.rows[0]
            valgt_data = latest_reports.iloc[row_idx]
            valgt_id = valgt_data['ID']
            valgt_navn = valgt_data['Navn']
            
            # Vi bruger en expander, der altid er åben (expanded=True), når en række vælges
            with st.expander(f"Profil: {valgt_navn}", expanded=True):
                historik = df[df['ID'] == valgt_id].sort_values('Dato')
                tab_ny, tab_his, tab_gra = st.tabs(["Rapport", "Historik", "Udvikling"])
                
                with tab_ny:
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

                with tab_his:
                    for _, row in historik.iloc[::-1].iterrows():
                        with st.expander(f"{row['Dato']} | Snit: {row['Rating_Avg']}"):
                            st.write(f"**Vurdering:** {row['Vurdering']}")

                with tab_gra:
                    if len(historik) < 2:
                        st.write("Kræver flere rapporter for at vise trend.")
                    else:
                        områder = ["Rating_Avg", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                        valgt_o = st.selectbox("Vælg område", options=områder, key="graf_valg")
                        fig = px.line(historik, x='Dato', y=valgt_o, markers=True, range_y=[1, 6.5])
                        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                        
    except Exception:
        st.info("Databasen er tom.")
