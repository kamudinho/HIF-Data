import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import uuid

# Konfiguration
REPO = "Kamudinho/HIF-data"
SCOUT_FILE = "scouting_db.csv"
STATS_FILE = "data/season_stats.csv" 

POS_MAP = {
    1: "Målmand", 2: "HB", 3: "CB", 4: "VB", 
    5: "DM", 6: "CM", 7: "OM", 8: "HW", 
    9: "VW", 10: "ST"
}

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Dashboard</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent Data
        scout_url = f"https://raw.githubusercontent.com/{REPO}/main/{SCOUT_FILE}?nocache={uuid.uuid4()}"
        df = pd.read_csv(scout_url, sep=None, engine='python')
        
        df['Position'] = df['Position'].map(POS_MAP).fillna(df['Position'])
        df['Dato_Str'] = df['Dato'].astype(str)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        try:
            stats_url = f"https://raw.githubusercontent.com/{REPO}/main/{STATS_FILE}?nocache={uuid.uuid4()}"
            stats_df = pd.read_csv(stats_url, sep=None, engine='python')
        except:
            stats_df = pd.DataFrame()

        # --- FILTRERING ---
        if 'f_rating' not in st.session_state: st.session_state.f_rating = (1.0, 7.0)
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        with c2:
            with st.popover("Filtre"):
                st.session_state.f_pos = st.multiselect("Positioner", options=sorted(df['Position'].unique().tolist()))
                st.session_state.f_rating = st.slider("Rating (Snit)", 1.0, 7.0, st.session_state.f_rating, step=0.1)

        # --- DATA BEHANDLING ---
        hif_avg = df[df['Klub'].str.contains('Hvidovre', case=False, na=False)]['Rating_Avg'].mean()

        rapport_counts = df.groupby('ID').size().reset_index(name='Rapporter')
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1)
        final_df = pd.merge(latest_reports, rapport_counts, on='ID')
        
        if search:
            final_df = final_df[final_df['Navn'].str.contains(search, case=False) | final_df['Klub'].str.contains(search, case=False)]
        if st.session_state.f_pos:
            final_df = final_df[final_df['Position'].isin(st.session_state.f_pos)]
        
        final_df = final_df[(final_df['Rating_Avg'] >= st.session_state.f_rating[0]) & 
                            (final_df['Rating_Avg'] <= st.session_state.f_rating[1])]

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

        # Metrik funktion
        def vis_metrikker(row):
            m_cols = st.columns(4)
            metrics = [
                ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
                ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
                ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
                ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
            ]
            for i, (label, col) in enumerate(metrics):
                m_cols[i % 4].metric(label, f"{int(row[col])}")

        # --- PROFIL DIALOG ---
        @st.dialog("Spillerprofil", width="large")
        def vis_profil(p_data, full_df, s_df, avg_line):
            st.markdown(f"### {p_data['Navn']} | {p_data['Position']} | {p_data['Klub']}")
            st.divider()

            historik = full_df[full_df['ID'] == p_data['ID']].sort_values('Dato', ascending=True)
            tab1, tab2, tab3, tab4 = st.tabs(["Seneste rapport", "Historik", "Udvikling", "Sæsonstatistik"])
            
            with tab1:
                nyeste = historik.iloc[-1]
                vis_metrikker(nyeste)
                
                st.write("") # Lidt luft
                
                # Tre kolonner på samme linje
                col_s, col_u, col_v = st.columns(3)
                
                with col_s:
                    st.success("**Styrker**")
                    styrker_tekst = nyeste.get('Styrker', '')
                    st.write(styrker_tekst if pd.notna(styrker_tekst) else "Ingen data")
                    
                with col_u:
                    st.warning("**Udviklingspotentiale**")
                    udv_tekst = nyeste.get('Udvikling', '')
                    st.write(udv_tekst if pd.notna(udv_tekst) else "Ingen data")
                    
                with col_v:
                    st.info("**Vurdering**")
                    vurdering_tekst = nyeste.get('Vurdering', '')
                    st.write(vurdering_tekst if pd.notna(vurdering_tekst) else "Ingen data")

            with tab2:
                for _, row in historik.iloc[::-1].iterrows():
                    with st.expander(f"Rapport fra {row['Dato']} (Rating: {row['Rating_Avg']})"):
                        vis_metrikker(row)
                        st.write(f"**Vurdering:** {row['Vurdering']}")

            with tab3:
                # Grafen
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=historik['Dato_Str'], y=historik['Rating_Avg'],
                    mode='lines+markers', name=p_data['Navn'],
                    line=dict(color='#1f77b4', width=3)
                ))
                
                if not pd.isna(avg_line):
                    fig.add_hline(y=avg_line, line_dash="dash", line_color="red", 
                                  annotation_text="HIF Snit", annotation_position="top left")
                
                fig.update_layout(
                    height=300, 
                    yaxis=dict(range=[1, 7], showgrid=False),
                    xaxis=dict(showgrid=False),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

                if len(historik) > 1:
                    st.divider()
                    nyeste_h = historik.iloc[-1]
                    forrige_h = historik.iloc[-2]
                    
                    metrik_navne = ["Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"]
                    forskelle = []
                    for m in metrik_navne:
                        diff = int(nyeste_h[m]) - int(forrige_h[m])
                        forskelle.append({'navn': m, 'diff': diff})
                    
                    forskelle = sorted(forskelle, key=lambda x: x['diff'], reverse=True)
                    fremgang = [f"{f['navn']} (+{f['diff']})" for f in forskelle if f['diff'] > 0]
                    tilbagegang = [f"{f['navn']} ({f['diff']})" for f in forskelle if f['diff'] < 0]

                    rating_diff = nyeste_h['Rating_Avg'] - forrige_h['Rating_Avg']
                    status_tekst = "stabil"
                    if rating_diff > 0: status_tekst = f"opadgående (+{rating_diff:.1f})"
                    elif rating_diff < 0: status_tekst = f"nedadgående (-{abs(rating_diff):.1f})"
                    
                    st.markdown(f"**Udviklingsanalyse: {status_tekst}**")
                    cf, ct = st.columns(2)
                    with cf:
                        if fremgang:
                            st.write("**Fremgang:**")
                            for f in fremgang[:2]: st.write(f"- {f}")
                    with ct:
                        if tilbagegang:
                            st.write("**Tilbagegang:**")
                            for t in tilbagegang[:2]: st.write(f"- {t}")
                else:
                    st.info("Kræver to rapporter for analyse.")

            with tab4:
                if s_df.empty:
                    st.info("Ingen kampdata.")
                else:
                    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.strip()
                    sp_stats = s_df[s_df['PLAYER_WYID'] == str(p_data['ID']).strip()].copy()
                    st.dataframe(
                        sp_stats[["SEASONNAME", "TEAMNAME", "APPEARANCES", "MINUTESPLAYED", "GOAL"]].sort_values('SEASONNAME', ascending=False),
                        use_container_width=True, hide_index=True
                    )

        if len(event.selection.rows) > 0:
            vis_profil(final_df.iloc[event.selection.rows[0]], df, stats_df, hif_avg)

    except Exception as e:
        st.error(f"Fejl: {e}")
