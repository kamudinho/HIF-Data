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
        
        # --- TOP BAR: SØG + POPOVER FILTER ---
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
                st.session_state.f_rating = st.slider("Minimum Rating Snit", 1.0, 6.0, st.session_state.f_rating, 0.1)
                if st.button("Nulstil filtre", use_container_width=True):
                    st.session_state.f_pos, st.session_state.f_status, st.session_state.f_rating = [], [], 1.0
                    st.rerun()

        # --- FILTRERING ---
        f_df = df.copy()
        if search_query:
            f_df = f_df[f_df['Navn'].str.contains(search_query, case=False, na=False) | f_df['Klub'].str.contains(search_query, case=False, na=False)]
        if st.session_state.f_pos: f_df = f_df[f_df['Position'].isin(st.session_state.f_pos)]
        if st.session_state.f_status: f_df = f_df[f_df['Status'].isin(st.session_state.f_status)]
        f_df = f_df[f_df['Rating_Avg'] >= st.session_state.f_rating]

        # --- TABEL ---
        latest_reports = f_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)
        st.markdown(f"<p style='font-size: 12px; color: gray;'>Viser {len(latest_reports)} spillere</p>", unsafe_allow_html=True)
        
        event = st.dataframe(
            latest_reports[["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]],
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={"Rating_Avg": st.column_config.NumberColumn("Snit", format="%.1f")}
        )

        # --- DETALJE-VISNING MED GRAF ---
        if len(event.selection.rows) > 0:
            row_idx = event.selection.rows[0]
            valgt_id = latest_reports.iloc[row_idx]['ID']
            valgt_navn = latest_reports.iloc[row_idx]['Navn']
            historik = df[df['ID'] == valgt_id].sort_values('Dato') # Sorteres ældst til nyest for grafen
            
            st.markdown("---")
            st.markdown(f"**Profil: {valgt_navn}**")
            
            tab_nyeste, tab_historik, tab_graf = st.tabs(["Seneste Rapport", f"Historik ({len(historik)})", "Udvikling (Graf)"])
            
            with tab_nyeste:
                s = historik.iloc[-1] # Den nyeste (sidste i den sorterede liste)
                p_c1, p_c2, p_c3, p_c4 = st.columns(4)
                p_c1.metric("Beslut.", s['Beslutsomhed']); p_c2.metric("Fart", s['Fart'])
                p_c3.metric("Aggres.", s['Aggresivitet']); p_c4.metric("Attitude", s['Attitude'])
                p_c5, p_c6, p_c7, p_c8 = st.columns(4)
                p_c5.metric("Udhold.", s['Udholdenhed']); p_c6.metric("Leder", s['Lederegenskaber'])
                p_c7.metric("Teknik", s['Teknik']); p_c8.metric("Intell.", s['Spilintelligens'])
                st.markdown("---")
                t_c1, t_c2, t_c3 = st.columns(3)
                t_c1.info(f"**Styrker**\n\n{s['Styrker'] if str(s['Styrker']) != 'nan' else '-'}")
                t_c2.warning(f"**Udvikling**\n\n{s['Udvikling'] if str(s['Udvikling']) != 'nan' else '-'}")
                t_c3.success(f"**Vurdering**\n\n{s['Vurdering'] if str(s['Vurdering']) != 'nan' else '-'}")
                st.caption(f"ID: {s['ID']} | Potentiale: {s['Potentiale']}")

            with tab_historik:
                for _, row in historik.iloc[::-1].iterrows(): # Vis nyeste først i historik
                    with st.expander(f"Rapport fra {row['Dato']} | Snit: {row['Rating_Avg']}"):
                        st.write(f"**Vurdering:** {row['Vurdering']}")

            with tab_graf:
                if len(historik) < 2:
                    st.info("Der skal være mindst to rapporter for at vise en udvikling.")
                else:
                    områder = ["Rating_Avg", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                    valgt_område = st.selectbox("Vælg område", options=områder, label_visibility="collapsed")
                    
                    fig = px.line(historik, x='Dato', y=valgt_område, markers=True, range_y=[1, 6.5])
                    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=20, b=20))
                    fig.update_traces(line_color='#007BFF', marker_size=12, line_width=3)
                    st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("Databasen er tom. Gå til Input for at oprette din første rapport.")
