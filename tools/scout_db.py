import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- DIALOG / POPUP VINDU ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(spiller_data, billed_map, career_df):
    pid = rens_id(spiller_data.get('PLAYER_WYID'))
    navn = spiller_data.get('Navn', 'Ukendt')
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Layout i popup
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(navn)
        st.write(f"**Klub:** {spiller_data.get('Klub', 'Hvidovre IF')} | **Pos:** {spiller_data.get('Position', 'Ukendt')}")
        st.write(f"**Rating:** {spiller_data.get('Rating_Avg', 0)} ⭐ | **Scout:** {spiller_data.get('Scout', 'Ukendt')}")

    t1, t2, t3 = st.tabs(["📝 Rapport", "📊 Radar", "📈 Karriere"])
    
    with t1:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### Færdigheder")
            metrics = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
            for m in metrics:
                val = spiller_data.get(m, 0)
                st.write(f"**{m}:** {val}")
        
        with col_right:
            st.markdown("### Bemærkninger")
            st.success(f"**Styrker:**\n\n{spiller_data.get('Styrker', '-')}")
            st.warning(f"**Udvikling:**\n\n{spiller_data.get('Udvikling', '-')}")
            st.info(f"**Vurdering:**\n\n{spiller_data.get('Vurdering', '-')}")

    with t2:
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
        fig.update_layout(polar=dict(gridshape='linear', radialaxis=dict(visible=True, range=[0, 6])), height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & 
                            (career_df['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            if not c_m.empty:
                st.table(c_m[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']])
            else:
                st.write("Ingen stats fundet for den valgte sæson.")

# --- HOVEDFUNKTION (Matching main.py) ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    """
    Denne funktion modtager nu de 4 argumenter som main.py sender:
    1. dp['scout_reports']
    2. dp['players']
    3. dp['sql_players']
    4. dp['career']
    """
    # 1. Load Data
    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
        df_s['Dato'] = pd.to_datetime(df_s['Dato']).dt.date
    except Exception as e:
        st.error(f"Fejl ved indlæsning af scouting_db.csv: {e}")
        return

    # Billed-mapping
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # 2. Oversigtstabel (Custom layout for at få knapper)
    st.markdown("### 📋 Scouting Database")
    
    # Overskrifter
    h_cols = st.columns([1.5, 2.5, 2, 1.5, 1, 1.5])
    h_cols[0].markdown("**Dato**")
    h_cols[1].markdown("**Navn**")
    h_cols[2].markdown("**Klub**")
    h_cols[3].markdown("**Pos**")
    h_cols[4].markdown("**Rating**")
    h_cols[5].markdown("**Handling**")
    st.divider()

    # Rækker
    for i, row in df_s.sort_values('Dato', ascending=False).iterrows():
        r_cols = st.columns([1.5, 2.5, 2, 1.5, 1, 1.5])
        r_cols[0].write(str(row['Dato']))
        r_cols[1].write(row['Navn'])
        r_cols[2].write(row['Klub'])
        r_cols[3].write(row['Position'])
        r_cols[4].write(f"{row['Rating_Avg']} ⭐")
        
        # Knappen der åbner Popup'en
        if r_cols[5].button("Åbn Profil", key=f"btn_{i}", use_container_width=True):
            vis_spiller_modal(row, billed_map, career_df)
