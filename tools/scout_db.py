import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    # Fjerner .0 og tvinger det til en ren tekst-streng
    return str(val).split('.')[0].strip()

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        v = float(str(val).replace(',', '.'))
        return int(v) if v <= 6 else 6
    except: return 0

def map_position(row):
    pos_val = rens_id(row.get('POS', row.get('POSITION', '')))
    pos_dict = {"1": "MM", "2": "HB", "3": "VB", "4": "VCB", "5": "HCB", "6": "DMC", "7": "HK", "8": "MC", "9": "ANG", "10": "OMC", "11": "VK"}
    return pos_dict.get(pos_val, "Ukendt")

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):    
    clean_p_id = rens_id(p_data.get('PLAYER_WYID', ''))
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    if 'DATO_DT' in historik.columns:
        historik = historik.sort_values('DATO_DT', ascending=True)
    nyeste = historik.iloc[-1] if not historik.empty else p_data
    
    h1, h2 = st.columns([1, 4])
    with h1:
        st.image(p_data.get('VIS_BILLEDE', ""), width=115)
    with h2:
        st.markdown(f"## {nyeste.get('NAVN', 'Ukendt')}")
        st.caption(f"{nyeste.get('KLUB', 'Ingen klub')} | {nyeste.get('POSITION_VISNING', 'Ukendt')} | Snit: {nyeste.get('RATING_AVG', 0)}")

    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        metrics = [("Teknik", "TEKNIK"), ("Fart", "FART"), ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
                   ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")]
        m_cols = st.columns(4)
        for i, (label, col) in enumerate(metrics):
            m_cols[i % 4].metric(label, f"{rens_metrik_vaerdi(nyeste.get(col, 0))}")
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
        with c2: st.warning(f"**Udvikling**\n\n{nyeste.get('UDVIKLING', '-')}")
        with c3: st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        if not historik.empty:
            for _, row in historik.iloc[::-1].iterrows():
                with st.expander(f"Dato: {row.get('DATO')} | Rating: {row.get('RATING_AVG')}"):
                    st.write(row.get('VURDERING', 'Ingen kommentar'))

    with t3:
        if len(historik) > 1:
            fig_line = go.Figure(go.Scatter(x=historik['DATO_DT'], y=historik['RATING_AVG'], mode='lines+markers', line=dict(color='#df003b')))
            fig_line.update_layout(yaxis=dict(range=[0, 6.5]), height=250, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_line, use_container_width=True)

    with t4:
        st.subheader("Karriere Stats")
        if career_df is not None and not career_df.empty:
            temp_career = career_df.copy()
            # Tving alle navne til store bogstaver for en sikkerheds skyld
            temp_career.columns = [str(c).upper().strip() for c in temp_career.columns]
            
            # Rens ID'er
            temp_career['PLAYER_WYID'] = temp_career['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
            df_p = temp_career[temp_career['PLAYER_WYID'] == str(clean_p_id)].copy()
            
            if not df_p.empty:
                # DISSE NAVNE MATCHER DIT DATA-DUMP:
                kolonner = [
                    'SEASONNAME', 'TEAMNAME', 'APPEARANCES', 
                    'MINUTESPLAYED', 'GOAL', 
                    'YELLOWCARD', 'REDCARDS'
                ]
                
                # Oversæt til noget lækkert i UI'en
                pretty_map = {
                    'SEASONNAME': 'Sæson', 
                    'TEAMNAME': 'Hold', 
                    'APPEARANCES': 'Kampe', 
                    'MINUTESPLAYED': 'Minutter', 
                    'GOAL': 'Mål', 
                    'YELLOWCARD': 'Gule kort', 
                    'REDCARDS': 'Røde kort'
                }
                
                # Sikkerheds-check: Tag kun de kolonner der faktisk findes i df_p
                final_cols = [c for c in kolonner if c in df_p.columns]
                
                st.dataframe(
                    df_p[final_cols].rename(columns=pretty_map), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning(f"Ingen stats fundet for ID: {clean_p_id}")
        else:
            st.error("Ingen data modtaget fra Snowflake.")

    with t5:
        categories = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        v = [rens_metrik_vaerdi(nyeste.get(k, 0)) for k in keys]
        fig_radar = go.Figure(go.Scatterpolar(r=v + [v[0]], theta=categories + [categories[0]], fill='toself', fillcolor='rgba(223, 0, 59, 0.3)', line=dict(color='#df003b')))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400, margin=dict(l=60, r=60, t=40, b=40))
        st.plotly_chart(fig_radar, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    if scout_df is None or scout_df.empty:
        st.info("Ingen spejder-rapporter fundet.")
        return
    
    df = scout_df.copy()
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
    billed_map = {}
    if sql_players is not None and not sql_players.empty:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].astype(str), sql_players['IMAGEDATAURL']))

    df['VIS_BILLEDE'] = df['PLAYER_WYID'].apply(lambda x: billed_map.get(x, "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"))
    df['POSITION_VISNING'] = df.apply(map_position, axis=1)
    df['DATO_DT'] = pd.to_datetime(df['DATO'], errors='coerce')
    
    f_df = df.sort_values('DATO_DT', ascending=True).groupby('PLAYER_WYID').tail(1).copy()
    
    search = st.text_input("Søg i databasen...", placeholder="Navn eller klub...")
    if search:
        f_df = f_df[f_df['NAVN'].str.contains(search, case=False, na=False) | f_df['KLUB'].str.contains(search, case=False, na=False)]

    col_map = {'VIS_BILLEDE': ' ', 'NAVN': 'Navn', 'POSITION_VISNING': 'Pos', 'KLUB': 'Klub', 'RATING_AVG': 'Rating', 'STATUS': 'Status', 'SCOUT': 'Scout'}
    disp = f_df[list(col_map.keys())].rename(columns=col_map)
    
    calc_height = (len(disp) + 1) * 35 + 3
    
    event = st.dataframe(
        disp, 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        height=min(calc_height, 5000),
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Rating": st.column_config.NumberColumn(format="%.1f")
        }
    )
    
    if len(event.selection.rows) > 0:
        valgt_index = event.selection.rows[0]
        spiller_data = f_df.iloc[valgt_index]
        # HER SKAL career_df TILFØJES SOM DET TREDJE ARGUMENT:
        vis_profil(spiller_data, df, career_df)
