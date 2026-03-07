import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Konstanter fra dine specifikationer
SEASON_FILTER = "2025/2026"

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(spiller_data, billed_map, career_df):
    pid = rens_id(spiller_data.get('PLAYER_WYID'))
    navn = spiller_data.get('Navn', 'Ukendt')
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header sektion (Som på billede 1 og 3)
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(navn)
        st.write(f"Hvidovre IF | {spiller_data.get('Position', 'Ukendt')} | Snit: {spiller_data.get('Rating_Avg', 0)}")

    # Tabs præcis som dine screenshots
    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"**Detaljer**\nDato: {spiller_data.get('Dato')}\n\nScout: {spiller_data.get('Scout', 'KD')}")
            st.divider()
            metrics = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
            for m in metrics:
                st.write(f"**{m}:** {spiller_data.get(m, 0)}")
        with col_right:
            st.markdown("**Bemærkninger**")
            st.success(f"**Styrker**\n\n{spiller_data.get('Styrker', 'Afgørende i boksen')}")
            st.warning(f"**Udvikling**\n\n{spiller_data.get('Udvikling', 'Kan falde ud af kampe')}")
            st.info(f"**Vurdering**\n\n{spiller_data.get('Vurdering', 'Farlig når han bliver serviceret')}")

    with t4:
        st.markdown("### Karrierestatistik")
        if career_df is not None and not career_df.empty:
            # Sikrer at vi kan finde kolonnerne uanset store/små bogstaver
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            
            # Filtrering på PLAYER_WYID og Sæson
            p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & 
                          (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            
            if not p_stats.empty:
                # Vi bruger de præcise kolonnenavne fra fejlen
                display_cols = ['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']
                # Tjekker om de rent faktisk findes i denne instans
                existing = [c for c in display_cols if c in p_stats.columns]
                st.dataframe(p_stats[existing], use_container_width=True, hide_index=True)
            else:
                st.write("Ingen data fundet for denne spiller i den valgte sæson.")
        else:
            st.info("Ingen karriere-database tilgængelig.")

    with t5:
        # Radar Logik
        labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
        keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        r_values = [float(str(spiller_data.get(k, 0)).replace(',', '.')) for k in keys]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=r_values + [r_values[0]], theta=labels + [labels[0]], fill='toself', line_color='#df003b'))
        fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])), height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke læse 'data/scouting_db.csv'")
        return

    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Den røde header bar fra dit billede
    st.markdown("""<div style='background-color: #df003b; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold; margin-bottom: 20px;'>SCOUTING I DATABASE</div>""", unsafe_allow_html=True)
    
    # Kolonner i tabellen
    h_cols = st.columns([0.8, 2, 1.5, 1, 1, 1])
    headers = ["Profil", "Navn", "Klub", "Pos", "Rating", "Pot."]
    for i, h in enumerate(headers): h_cols[i].markdown(f"**{h}**")
    st.divider()

    for i, row in df_s.iterrows():
        r_cols = st.columns([0.8, 2, 1.5, 1, 1, 1])
        if r_cols[0].button("Se", key=f"v_{i}", use_container_width=True):
            vis_spiller_modal(row, billed_map, career_df)
        
        r_cols[1].write(row.get('Navn', '-'))
        r_cols[2].write(row.get('Klub', '-'))
        r_cols[3].write(row.get('Position', '-'))
        r_cols[4].write(f"{row.get('Rating_Avg', 0)} ⭐")
        r_cols[5].write(row.get('Potentiale', '-'))
