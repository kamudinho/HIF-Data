import streamlit as st
import pandas as pd
import plotly.express as px
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def load_data():
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        df = pd.read_csv(raw_url)
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        return df
    except:
        return None

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    df = load_data()
    if df is None:
        st.info("Databasen er tom eller kunne ikke hentes.")
        return

    # --- NAVIGATION MELLEM SIDER ---
    menu = st.radio("Visning", ["Database", "Sæsonstatistik"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if menu == "Database":
        # --- FILTRERING ---
        if 'f_pos' not in st.session_state: st.session_state.f_pos = []
        if 'f_status' not in st.session_state: st.session_state.f_status = []
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Søg", placeholder="Spiller eller klub...", label_visibility="collapsed")
        with c2:
            with st.popover("Filtre"):
                st.session_state.f_pos = st.multiselect("Positioner", sorted(df['Position'].unique().tolist()))
                st.session_state.f_status = st.multiselect("Status", sorted(df['Status'].unique().tolist()))

        # --- DATA BEHANDLING ---
        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest, rapport_counts, on='ID')
        
        if search:
            final_df = final_df[final_df['Navn'].str.contains(search, case=False)]
        if st.session_state.f_pos:
            final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]

        # --- TABEL (DYNAMISK HØJDE) ---
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
            def vis_profil(p_data, full_df):
                # Header med Navn, Position, Klub og ID nedenfor
                st.markdown(f"### {p_data['Navn']} | {p_data['Position']}")
                st.markdown(f"**{p_data['Klub']}**")
                st.caption(f"Spiller ID: {p_data['ID']}")
                st.divider()

                historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato')
                t1, t2, t3 = st.tabs(["Seneste", "Historik", "Udvikling"])
                
                with t1:
                    s = historik.iloc[-1]
                    cols = st.columns(4)
                    metrics = ["Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                    for i, m in enumerate(metrics):
                        cols[i%4].metric(m, s[m])
                    st.info(f"**Vurdering:** {s['Vurdering']}")

                with t2:
                    for _, r in historik.iloc[::-1].iterrows():
                        with st.expander(f"Rapport - {r['Dato']} (Snit: {r['Rating_Avg']})"):
                            st.write(f"**Styrker:** {r['Styrker']}")
                            st.write(f"**Vurdering:** {r['Vurdering']}")

                with t3:
                    fig = px.line(historik, x='Dato_Str', y='Rating_Avg', markers=True, range_y=[1, 6])
                    fig.update_xaxes(type='category')
                    st.plotly_chart(fig, use_container_width=True)

            vis_profil(final_df.iloc[event.selection.rows[0]], df)

    elif menu == "Sæsonstatistik":
        st.subheader("Gennemsnit for sæsonen 2026")
        # Grupper alt data pr spiller og tag gennemsnit af alle tal-kolonner
        stats_df = df.groupby(['ID', 'Navn', 'Position', 'Klub']).agg({
            'Rating_Avg': 'mean',
            'Beslutsomhed': 'mean',
            'Fart': 'mean',
            'Aggresivitet': 'mean',
            'Attitude': 'mean',
            'Udholdenhed': 'mean',
            'Lederegenskaber': 'mean',
            'Teknik': 'mean',
            'Spilintelligens': 'mean',
            'ID': 'count' # Bruges til antal rapporter
        }).rename(columns={'ID': 'Antal'}).reset_index()

        stats_df = stats_df.sort_values('Rating_Avg', ascending=False)
        
        st.dataframe(
            stats_df,
            use_container_width=True,
            hide_index=True,
            height=(len(stats_df) * 35) + 40,
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("Sæson Snit", format="%.2f"),
                "Antal": st.column_config.NumberColumn("Rapporter")
            }
        )
