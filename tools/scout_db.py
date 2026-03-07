import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(spiller_data, billed_map, career_df, alle_rapporter):
    pid = rens_id(spiller_data.get('PLAYER_WYID'))
    navn = spiller_data.get('Navn', 'Ukendt')
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # 1. Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(navn)
        st.write(f"**Klub:** {spiller_data.get('Klub', 'Hvidovre IF')} | **Pos:** {spiller_data.get('Position', 'Ukendt')}")
        st.write(f"**Rating:** {spiller_data.get('Rating_Avg', 0)} ⭐ | **Potentiale:** {spiller_data.get('Potentiale', '-')}")

    # 2. Tabs
    t1, t2, t3, t4 = st.tabs(["📝 Rapport & Radar", "📜 Historik", "📈 Udvikling", "⚽ Stats"])
    
    with t1:
        col_text, col_radar = st.columns([1, 1.2])
        with col_text:
            st.markdown(f"**Seneste Dato:** {spiller_data.get('Dato')}")
            st.success(f"**Styrker:**\n\n{spiller_data.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{spiller_data.get('Vurdering', '-')}")
            st.warning(f"**Fokus:**\n\n{spiller_data.get('Udvikling', '-')}")
        
        with col_radar:
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            r_values = []
            for k in keys:
                try:
                    v = float(str(spiller_data.get(k, 0)).replace(',', '.'))
                    r_values.append(v if v > 0 else 0.1)
                except: r_values.append(0.1)
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=r_values + [r_values[0]], theta=labels + [labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=30, r=30, t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        hist = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato', ascending=False)
        st.dataframe(hist[['Dato', 'Rating_Avg', 'Status', 'Vurdering', 'Scout']], use_container_width=True, hide_index=True)

    with t3:
        hist_plot = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato')
        st.write(f"Gennemsnitsrating over tid for {navn}")
        st.line_chart(hist_plot.set_index('Dato')['Rating_Avg'])

    with t4:
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            st.dataframe(p_stats[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], use_container_width=True, hide_index=True)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    st.markdown("### 📋 Scouting Database")

    # Load data
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
        # Tilføj en midlertidig kolonne til checkboxen
        df_s.insert(0, "Åbn", False)
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        return

    # Billed-map
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Konfigurer kolonne-visning i Dataframe
    # Vi bruger data_editor så checkboxen kan klikkes
    ed_df = st.data_editor(
        df_s,
        column_config={
            "Åbn": st.column_config.CheckboxColumn("Profil", help="Klik for at åbne spillerprofilen", default=False),
            "PLAYER_WYID": None, # Skjul ID-kolonnen
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
        },
        disabled=[c for c in df_s.columns if c != "Åbn"], # Kun checkboxen må klikkes
        hide_index=True,
        use_container_width=True,
        key="db_editor"
    )

    # Tjek om en checkbox er blevet markeret
    # Vi finder rækken hvor 'Åbn' er True
    valgt_raekke = ed_df[ed_df['Åbn'] == True]
    
    if not valgt_raekke.empty:
        # Åbn modal for den første valgte række
        vis_spiller_modal(valgt_raekke.iloc[0], billed_map, career_df, df_s)
        # Reset checkboxen (valgfrit, men rart så man kan klikke igen)
        # st.rerun() # Kan tilføjes hvis nødvendigt
