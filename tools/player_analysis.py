import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data fra pakken
    df_xg = dp.get("xg_agg")
    df_lb = dp.get("linebreaks")
    df_players = dp.get("players")

    # Sikkerhedstjek: Stop hvis data mangler helt
    if df_players is None or df_players.empty:
        st.error("❌ FEJL: 'players.csv' kunne ikke indlæses. Tjek stien i data_load.py")
        return
    
    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet i Snowflake for den valgte periode.")
        return

    # 2. Robust Mapping (Vi ved de er UPPERCASE pga. din data_load.py)
    # Vi tjekker hvad de faktiske kolonnenavne er for at undgå gætteleg
    cols = list(df_players.columns)
    
    # Find ID kolonnen (Typisk PLAYER_UUID eller OPTA_UUID)
    id_col = next((c for c in cols if "UUID" in c), None)
    # Find Navne kolonnen (Typisk NAVN eller NAME)
    name_col = next((c for c in cols if c in ["NAVN", "NAME", "PLAYER_NAME"]), None)

    if not id_col or not name_col:
        st.error(f"❌ Kolonne-fejl i players.csv. Fundne kolonner: {cols}")
        return

    # Lav navne-ordbogen { 'uuid': 'Navn' }
    name_map = dict(zip(df_players[id_col].astype(str), df_players[name_col]))
    
    # 3. Spiller-valg (Dropdown)
    # Vi bruger PLAYER_OPTAUUID fra din SQL query
    available_uuids = df_xg['PLAYER_OPTAUUID'].unique()
    
    # Byg liste med navne til dropdown
    dropdown_options = {uuid: name_map.get(str(uuid), f"Ukendt ({str(uuid)[:5]})") for uuid in available_uuids}
    sorted_uuids = sorted(dropdown_options.keys(), key=lambda x: dropdown_options[x])

    col_sel, col_empty = st.columns([1, 2])
    with col_sel:
        selected_uuid = st.selectbox(
            "Vælg Spiller", 
            options=sorted_uuids, 
            format_func=lambda x: dropdown_options[x]
        )

    # 4. Filtrering af data
    p_xg = df_xg[df_xg['PLAYER_OPTAUUID'] == selected_uuid].copy()
    p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy() if df_lb is not None else pd.DataFrame()

    # Sørg for at STAT_VALUE er et tal (float), ellers kan vi ikke lave matematik
    p_xg['STAT_VALUE'] = pd.to_numeric(p_xg['STAT_VALUE'], errors='coerce').fillna(0)

    # --- 5. VISNING I TABS ---
    tab1, tab2, tab3 = st.tabs(["🎯 OFFENSIV IMPACT", "🚀 LINEBREAKS", "📋 RÅ DATA"])

    with tab1:
        m1, m2, m3, m4 = st.columns(4)
        
        # Funktion til at hente specifikke værdier
        def get_v(stat): return p_xg[p_xg['STAT_TYPE'] == stat]['STAT_VALUE'].sum()

        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Non-Penalty xG", f"{get_v('expectedGoalsNonpenalty'):.2f}")
        m3.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m4.metric("Minutter", int(get_v('minsPlayed')))

        # Visualisering af xG kilder
        xg_cats = ['expectedGoalsHd', 'expectedGoalsOpenplay', 'expectedGoalsSetplay']
        xg_plot = p_xg[p_xg['STAT_TYPE'].isin(xg_cats)].groupby('STAT_TYPE')['STAT_VALUE'].sum().reset_index()
        
        if not xg_plot.empty and xg_plot['STAT_VALUE'].sum() > 0:
            fig_xg = px.bar(xg_plot, x='STAT_TYPE', y='STAT_VALUE', 
                            title="xG Fordeling", color_discrete_sequence=['#df003b'])
            st.plotly_chart(fig_xg, use_container_width=True)

    with tab2:
        if not p_lb.empty:
            # Vi sikrer os at tallene er numeriske
            p_lb['STAT_FH'] = pd.to_numeric(p_lb['STAT_FH'], errors='coerce').fillna(0)
            p_lb['STAT_SH'] = pd.to_numeric(p_lb['STAT_SH'], errors='coerce').fillna(0)
            
            lb_types = ['defenceLineBroken', 'midfieldLineBroken', 'attackingLineBroken']
            lb_data = p_lb[p_lb['STAT_TYPE'].isin(lb_types)]

            fig_lb = px.bar(lb_data, y='STAT_TYPE', x=['STAT_FH', 'STAT_SH'],
                            orientation='h', title="Linjebrud pr. Halvleg",
                            color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'})
            st.plotly_chart(fig_lb, use_container_width=True)
        else:
            st.info("Ingen linebreak-data fundet for denne spiller.")

    with tab3:
        st.dataframe(p_xg[['MATCH_DATE', 'STAT_TYPE', 'STAT_VALUE']].sort_values('MATCH_DATE', ascending=False), 
                     use_container_width=True, hide_index=True)
