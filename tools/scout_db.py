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

    t1, t2, t3, t4 = st.tabs(["📊 Seneste & Radar", "📜 Historik", "📈 Udvikling", "⚽ Stats"])
    
    with t1:
        col_t, col_r = st.columns([1, 1.2])
        with col_t:
            st.markdown(f"**Dato:** {spiller_data.get('Dato')}")
            st.success(f"**Styrker:**\n\n{spiller_data.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{spiller_data.get('Vurdering', '-')}")
            st.warning(f"**Fokus:**\n\n{spiller_data.get('Udvikling', '-')}")
        with col_r:
            keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            r_vals = [float(str(spiller_data.get(k, 0)).replace(',', '.')) for k in keys]
            fig = go.Figure(data=go.Scatterpolar(r=r_vals+[r_vals[0]], theta=labels+[labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=300, margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        hist = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato', ascending=False)
        st.dataframe(hist[['Dato', 'Rating_Avg', 'Status', 'Vurdering']], use_container_width=True, hide_index=True)

    with t3:
        # Udvikling baseret på gennemsnitsrating
        hist_evo = alle_rapporter[alle_rapporter['Navn'] == navn].sort_values('Dato')
        st.line_chart(hist_evo.set_index('Dato')['Rating_Avg'])

    with t4:
        if career_df is not None:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
            st.dataframe(p_stats[['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']], use_container_width=True, hide_index=True)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    st.markdown("### 📋 Scouting Database")

    # Initialiser session state til at styre pop-up
    if "valgt_spiller_index" not in st.session_state:
        st.session_state.valgt_spiller_index = None

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].apply(rens_id)
        # Vi laver en kopi til editoren med en checkbox kolonne
        df_display = df_s.copy()
        df_display.insert(0, "Se", False)
    except:
        st.error("Kunne ikke indlæse databasen.")
        return

    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Data Editor
    # Vi bruger 'on_change' eller tjekker output direkte
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "PLAYER_WYID": None,
            "Styrker": None, "Udvikling": None, "Vurdering": None # Skjul lange tekster i oversigten
        },
        disabled=[c for c in df_display.columns if c != "Se"],
        hide_index=True,
        use_container_width=True,
        key="db_viewer"
    )

    # Tjek om brugeren har klikket på en checkbox
    nye_valg = ed_result[ed_result["Se"] == True]
    
    if not nye_valg.empty:
        # Hent data for den valgte række
        spiller_data = nye_valg.iloc[0]
        
        # Åbn modal
        vis_spiller_modal(spiller_data, billed_map, career_df, df_s)
        
        # NU KOMMER TRICKET: 
        # Vi rydder editoren ved at tvinge en rerun, men først efter dialogen er defineret.
        # Da st.dialog kører med det samme, kan vi nulstille state her:
        if st.button("Luk profil og ryd valg", use_container_width=True):
            st.rerun()
