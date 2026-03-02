import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_team_color

def vis_side(df_raw=None, colors_map=None): 
    # --- 1. DATA INITIALISERING ---
    # Vi bruger 'dp' i stedet for 'data_package' for at matche HIF_dash.py
    if "dp" not in st.session_state:
        st.error("Data pakken blev ikke fundet. Genstart venligst appen.")
        return
        
    dp = st.session_state["dp"]
    
    if df_raw is None or df_raw.empty:
        df_raw = dp.get("team_stats_full", pd.DataFrame())

    if df_raw.empty:
        st.warning("Ingen data fundet for den valgte sæson og liga.")
        return

    # --- 2. CSS & STYLING ---
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; font-family: sans-serif; font-size: 0.85rem; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; font-weight: bold; }
            /* Hvidovre Rød farve på tabs */
            button[data-baseweb='tab'][aria-selected='true'] { color: #cc0000 !important; border-bottom-color: #cc0000 !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. DATA PREPARATION ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)
    
    # Vi tager fat i den nuværende sæson fra data pakken
    df_liga = df[df['SEASONNAME'] == dp['SEASONNAME']].copy()

    # --- 4. TABS STRUKTUR ---
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["📊 Ligaoversigt", "⚔️ Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        
        def render_html_table(dataframe, columns, rename_dict):
            temp_df = dataframe[columns].copy()
            if 'IMAGEDATAURL' in temp_df.columns:
                temp_df['IMAGEDATAURL'] = temp_df['IMAGEDATAURL'].apply(lambda x: f'<img src="{x}" width="25">')
            temp_df = temp_df.rename(columns=rename_dict)
            st.write(temp_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        with l_gen:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'GOALS', 'CONCEDEDGOALS', 'TOTALPOINTS']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'MATCHES': 'K', 'TOTALWINS': 'V', 'TOTALDRAWS': 'U', 
                       'TOTALLOSSES': 'T', 'GOALS': 'M+', 'CONCEDEDGOALS': 'M-', 'TOTALPOINTS': 'P'}
            render_html_table(df_liga.sort_values('TOTALPOINTS', ascending=False), cols, renames)
        
        with l_off:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XGSHOT', 'SHOTS', 'PASSESTOFINALTHIRD']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'GOALS': 'MÅL', 'XGSHOT': 'xG', 'SHOTS': 'SKUD', 'PASSESTOFINALTHIRD': 'PASS 3.DEL'}
            render_html_table(df_liga.sort_values('GOALS', ascending=False), cols, renames)

        with l_def:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'CONCEDEDGOALS': 'MÅL IMOD', 'XGSHOTAGAINST': 'xG IMOD', 'PPDA': 'PPDA'}
            render_html_table(df_liga.sort_values('CONCEDEDGOALS', ascending=True), cols, renames)

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", hold_navne, index=hold_navne.index("Hvidovre") if "Hvidovre" in hold_navne else 0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]
        
        h2h_sub_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2, per_match=False):
            fig = go.Figure()
            
            y1_vals = [t1[m] / t1['MATCHES'] if per_match and t1['MATCHES'] > 0 and m != 'PPDA' else t1[m] for m in metrics]
            y2_vals = [t2[m] / t2['MATCHES'] if per_match and t2['MATCHES'] > 0 and m != 'PPDA' else t2[m] for m in metrics]
            
            # Farver hentes dynamisk fra get_team_color
            color1 = get_team_color(n1)
            color2 = get_team_color(n2)
            
            fig.add_trace(go.Bar(name=n1, x=labels, y=y1_vals, marker_color=color1, text=[f"{v:.1f}" for v in y1_vals], textposition='auto'))
            fig.add_trace(go.Bar(name=n2, x=labels, y=y2_vals, marker_color=color2, text=[f"{v:.1f}" for v in y2_vals], textposition='auto'))
        
            fig.update_layout(
                barmode='group', height=350, margin=dict(t=40, b=40, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with h2h_sub_tabs[0]: 
            create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_sub_tabs[1]: 
            create_h2h_plot(['GOALS', 'XGSHOT', 'PASSESTOFINALTHIRD'], ['Mål/k', 'xG/k', 'Pass 3.del/k'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_sub_tabs[2]: 
            create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål imod/k', 'xG Imod/k', 'PPDA'], t1_stats, t2_stats, team1, team2, per_match=True)
