import streamlit as st
import pandas as pd
import plotly.graph_objects as go

SEASON_FILTER = "2025/2026"

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('Dato', ascending=False)
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"Klub: {nyeste.get('Klub', 'Ukendt')} | Pos: {nyeste.get('Position', 'Ukendt')}")
        st.write(f"Rating: {nyeste.get('Rating_Avg', 0)} | Potentiale: {nyeste.get('Potentiale', '-')}")

    t1, t2, t3, t4 = st.tabs(["Seneste & Radar", "Historik", "Udvikling", "Stats"])
    
    with t1:
        col_t, col_r = st.columns([1, 1.2])
        with col_t:
            st.markdown(f"**Dato:** {nyeste.get('Dato')}")
            st.success(f"**Styrker:**\n\n{nyeste.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{nyeste.get('Vurdering', '-')}")
            st.warning(f"**Fokus:**\n\n{nyeste.get('Udvikling', '-')}")
        with col_r:
            keys = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
            labels = ['Fart', 'Teknik', 'Beslutning', 'Intelligens', 'Aggres.', 'Leder', 'Attitude', 'Udhold.']
            r_vals = [float(str(nyeste.get(k, 0)).replace(',', '.')) for k in keys]
            fig = go.Figure(data=go.Scatterpolar(r=r_vals+[r_vals[0]], theta=labels+[labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=300, margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        st.dataframe(spiller_historik[['Dato', 'Rating_Avg', 'Status', 'Vurdering', 'Scout']], use_container_width=True, hide_index=True)

    with t3:
        hist_evo = spiller_historik.sort_values('Dato')
        st.line_chart(hist_evo.set_index('Dato')['Rating_Avg'])

    with t4:
        if career_df is not None:
            cdf = career_df.copy()
            cdf.columns = [str(c).upper() for c in cdf.columns]
            req = ['SEASONNAME', 'TEAMNAME', 'APPEARANCES', 'GOAL', 'MINUTESPLAYED']
            if all(col in cdf.columns for col in req):
                p_stats = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].astype(str).str.contains(SEASON_FILTER))]
                st.dataframe(p_stats[req], use_container_width=True, hide_index=True)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    # 1. Initialiser state-counter hvis den ikke findes
    if "db_key_counter" not in st.session_state:
        st.session_state.db_key_counter = 0

    try:
        df_raw = pd.read_csv('data/scouting_db.csv')
        df_raw['PLAYER_WYID'] = df_raw['PLAYER_WYID'].apply(rens_id)
        df_raw['Dato'] = pd.to_datetime(df_raw['Dato'])
        df_unique = df_raw.sort_values('Dato', ascending=False).drop_duplicates('Navn').copy()
        df_unique['Dato'] = df_unique['Dato'].dt.date
    except Exception as e:
        return

    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # Forbered visning
    df_display = df_unique[['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato']].copy()
    df_display.insert(0, "Se", False)

    # 2. Vis tabellen med en dynamisk KEY
    # Når key ændrer sig, nulstilles tabellen (og alle checkboxes)
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        disabled=['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato'],
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.db_key_counter}"
    )

    # 3. Logik for valg
    nye_valg = ed_result[ed_result["Se"] == True]
    
    if not nye_valg.empty:
        # Gem valget
        valgt_navn = nye_valg.iloc[-1]['Navn']
        
        # Åbn modalen
        vis_spiller_modal(valgt_navn, billed_map, career_df, df_raw)
        
        # 4. TRICKET: Tæl counteren op og kør rerun. 
        # Da dialogen (modal) allerede er åbnet, bliver den liggende, 
        # men baggrunden (tabellen) tegnes forfra og rydder alle flueben.
        st.session_state.db_key_counter += 1
        st.rerun()
