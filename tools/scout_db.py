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
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(navn)
        st.write(f"**Klub:** {spiller_data.get('Klub', 'Ukendt')} | **Pos:** {spiller_data.get('Position', 'Ukendt')}")
        st.write(f"**Rating:** {spiller_data.get('Rating_Avg', 0)} ⭐ | **Potentiale:** {spiller_data.get('Potentiale', '-')}")

    # Nye faner baseret på dine ønsker
    t1, t2, t3, t4 = st.tabs(["📊 Seneste Rapport & Radar", "📜 Historik", "📈 Udvikling", "⚽ Stats"])
    
    with t1:
        # Rapport og Radar i én tab
        col_text, col_radar = st.columns([1, 1.2])
        with col_text:
            st.markdown(f"**Dato:** {spiller_data.get('Dato')}")
            st.success(f"**Styrker:**\n\n{spiller_data.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{spiller_data.get('Vurdering', '-')}")
            st.warning(f"**Fokus:**\n\n{spiller_data.get('Udvikling', '-')}")
            
        with col_radar:
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            r_values = [float(str(spiller_data.get(k, 0)).replace(',', '.')) for k in keys]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=r_values + [r_values[0]], theta=labels + [labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])), height=350, margin=dict(l=30, r=30, t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        # Historik - Viser alle rapporter for denne spiller
        st.markdown(f"**Alle rapporter for {navn}**")
        hist = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato', ascending=False)
        st.dataframe(hist[['Dato', 'Rating_Avg', 'Status', 'Vurdering', 'Scout']], use_container_width=True, hide_index=True)

    with t3:
        # Udvikling - Gennemsnitsrating over tid
        st.markdown("**Rating-udvikling**")
        hist_plot = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato')
        if len(hist_plot) > 1:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=hist_plot['Dato'], y=hist_plot['Rating_Avg'], mode='lines+markers', line_color='#df003b'))
            fig_line.update_layout(height=300, yaxis=dict(range=[0, 6]), margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.write(f"Nuværende gennemsnit: {hist_plot['Rating_Avg'].mean():.2f} ⭐")
            st.caption("Kræver mere end én rapport for at tegne en graf.")

    with t4:
        # Stats - Player Career
        if career_df is not None and not career_df.empty:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not p_stats.empty:
                st.dataframe(p_stats[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], use_container_width=True, hide_index=True)
            else:
                st.write("Ingen karriere-data fundet.")

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
        df_s = df_s.sort_values('Dato', ascending=False)
    except:
        st.error("Kunne ikke læse databasen.")
        return

    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Databaseoversigt
    st.markdown("### 📋 Scouting Database")
    h_cols = st.columns([0.8, 2, 1.5, 1, 1, 1])
    headers = ["Profil", "Navn", "Klub", "Pos", "Rating", "Pot."]
    for i, h in enumerate(headers): h_cols[i].markdown(f"**{h}**")
    st.divider()

    for i, row in df_s.iterrows():
        r_cols = st.columns([0.8, 2, 1.5, 1, 1, 1])
        if r_cols[0].button("Se", key=f"v_{i}", use_container_width=True):
            vis_spiller_modal(row, billed_map, career_df, df_s)
        
        r_cols[1].write(row.get('Navn', '-'))
        r_cols[2].write(row.get('Klub', '-'))
        r_cols[3].write(row.get('Position', '-'))
        r_cols[4].write(f"{row.get('Rating_Avg', 0)} ⭐")
        r_cols[5].write(row.get('Potentiale', '-'))
