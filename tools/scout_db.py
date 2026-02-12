import streamlit as st
import pandas as pd
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
        top_c1, top_c2 = st.columns([3, 1])
        
        with top_c1:
            search_query = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
            
        with top_c2:
            with st.popover("⚙️ Filtre"):
                st.markdown("**Filtrer visning**")
                
                # Multi-valg for Position
                all_positions = sorted(df['Position'].dropna().unique().tolist())
                filter_pos = st.multiselect("Positioner", options=all_positions, placeholder="Vælg...")
                
                # Multi-valg for Status
                all_status = sorted(df['Status'].dropna().unique().tolist())
                filter_status = st.multiselect("Status", options=all_status, placeholder="Vælg...")
                
                # Slider for Minimum Rating
                min_rating = st.slider("Minimum Rating Snit", 1.0, 6.0, 1.0, 0.1)

        # --- FILTRERING LOGIK ---
        f_df = df.copy()
        
        # Fritext søgning
        if search_query:
            f_df = f_df[f_df['Navn'].str.contains(search_query, case=False, na=False) | 
                        f_df['Klub'].str.contains(search_query, case=False, na=False)]
        
        # Multiselect filtrering (hvis listen ikke er tom)
        if filter_pos:
            f_df = f_df[f_df['Position'].isin(filter_pos)]
            
        if filter_status:
            f_df = f_df[f_df['Status'].isin(filter_status)]
            
        # Rating filtrering
        f_df = f_df[f_df['Rating_Avg'] >= min_rating]

        # --- MASTER-TABEL ---
        latest_reports = f_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)

        st.markdown(f"<p style='font-size: 12px; color: gray;'>Viser {len(latest_reports)} spillere</p>", unsafe_allow_html=True)
        
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]
        event = st.dataframe(
            latest_reports[vis_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("⭐ Snit", format="%.1f"),
                "Dato": st.column_config.DateColumn("Senest"),
            }
        )

        # --- DETALJE-VISNING ---
        if len(event.selection.rows) > 0:
            row_idx = event.selection.rows[0]
            valgt_id = latest_reports.iloc[row_idx]['ID']
            valgt_navn = latest_reports.iloc[row_idx]['Navn']
            
            historik = df[df['ID'] == valgt_id].sort_values('Dato', ascending=False)
            
            st.markdown("---")
            st.subheader(f"Profil: {valgt_navn}")
            
            tab_nyeste, tab_historik = st.tabs(["Seneste Rapport", f"Historik ({len(historik)})"])
            
            with tab_nyeste:
                s = historik.iloc[0]
                
                # Parametre (1-6)
                p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                p_col1.metric("Beslut.", s['Beslutsomhed'])
                p_col2.metric("Fart", s['Fart'])
                p_col3.metric("Aggres.", s['Aggresivitet'])
                p_col4.metric("Attitude", s['Attitude'])
                
                p_col5, p_col6, p_col7, p_col8 = st.columns(4)
                p_col5.metric("Udhold.", s['Udholdenhed'])
                p_col6.metric("Leder", s['Lederegenskaber'])
                p_col7.metric("Teknik", s['Teknik'])
                p_col8.metric("Intell.", s['Spilintelligens'])

                st.markdown("---")
                
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    st.markdown("**Styrker**")
                    st.info(s['Styrker'] if str(s['Styrker']) != 'nan' else "-")
                with t_col2:
                    st.markdown("**Udvikling**")
                    st.warning(s['Udvikling'] if str(s['Udvikling']) != 'nan' else "-")
                with t_col3:
                    st.markdown("**Vurdering**")
                    st.success(s['Vurdering'] if str(s['Vurdering']) != 'nan' else "-")
                
                st.caption(f"ID: {s['ID']} | Potentiale: {s['Potentiale']}")

            with tab_historik:
                for i, row in historik.iterrows():
                    with st.expander(f"Rapport fra {row['Dato']} | Snit: {row['Rating_Avg']}"):
                        st.write(f"**Vurdering:** {row['Vurdering']}")

    except Exception:
        st.info("💡 Databasen er tom. Gå til 'Input' for at oprette din første scoutingrapport.")
