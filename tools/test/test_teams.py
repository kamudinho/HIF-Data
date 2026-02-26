import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

# 0. Konfiguration af Farver
TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},
    "B.93": {"primary": "#0000ff", "secondary": "#ffffff"},
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},
    "Horsens": {"primary": "#ffff00", "secondary": "#000000"},
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},
    "Kolding IF": {"primary": "#ffffff", "secondary": "#0000ff"},
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"}
}

def vis_side(df_raw=None): 
    # --- 1. DATA INITIALISERING ---
    if df_raw is None or df_raw.empty:
        if "data_package" not in st.session_state:
            st.session_state["data_package"] = get_data_package()
        
        dp = st.session_state["data_package"]
        df_raw = load_snowflake_query("team_stats_full", dp["comp_filter"], dp["season_filter"])

    if df_raw is None or df_raw.empty:
        st.warning("⚠️ Ingen data fundet. Tjek om tabellerne 'WYSCOUT_TEAMSADVANCEDSTATS_TOTAL' er opdateret.")
        return

    # --- 2. DATA PREPARATION ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)
    
    # Filtrer til nyeste sæson i datasættet
    saesoner = sorted(df['SEASONNAME'].unique().tolist())
    df_liga = df[df['SEASONNAME'] == saesoner[-1]].copy()

    # --- 3. CSS & STYLING ---
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; font-family: sans-serif; font-size: 0.9rem; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; font-weight: bold; }
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TABS STRUKTUR ---
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["📊 Ligaoversigt", "⚔️ Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensiv & Pass", "Defensiv"])
        
        def render_html_table(dataframe, columns, rename_dict):
            temp_df = dataframe[columns].copy()
            if 'IMAGEDATAURL' in temp_df.columns:
                temp_df['IMAGEDATAURL'] = temp_df['IMAGEDATAURL'].apply(lambda x: f'<img src="{x}" width="25">')
            temp_df = temp_df.rename(columns=rename_dict)
            st.write(temp_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        with l_gen:
            # CONCEDEDGOALS FJERNET - Vi bruger TOTALPOINTS direkte fra din nye SQL
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS', 'GOALS']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'MATCHES': 'K', 'TOTALWINS': 'V', 'TOTALDRAWS': 'U', 'TOTALLOSSES': 'T', 'TOTALPOINTS': 'P', 'GOALS': 'M+'}
            render_html_table(df_liga.sort_values('TOTALPOINTS', ascending=False), cols, renames)
        
        with l_off:
            # Bruger de nye pasnings-kolonner fra din query
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XGSHOT', 'PASSESTOFINALTHIRD', 'FORWARDPASSES']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'GOALS': 'MÅL', 'XGSHOT': 'xG', 'PASSESTOFINALTHIRD': 'PASS 3.DEL', 'FORWARDPASSES': 'FREM. PASS'}
            render_html_table(df_liga.sort_values('GOALS', ascending=False), cols, renames)

        with l_def:
            # Rent defensivt fokus
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'XGSHOTAGAINST', 'PPDA']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'XGSHOTAGAINST': 'xG IMOD', 'PPDA': 'PPDA'}
            render_html_table(df_liga.sort_values('XGSHOTAGAINST', ascending=True), cols, renames)

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", hold_navne, index=0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]
        
        h2h_sub_tabs = st.tabs(["Overblik", "Angreb & Pasninger", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2, per_match=False):
            fig = go.Figure()
            for name, stats in [(n1, t1), (n2, t2)]:
                c = TEAM_COLORS.get(name, {"primary": "#808080", "secondary": "#000000"})
                y_vals = []
                for m in metrics:
                    val = stats[m]
                    if per_match and stats['MATCHES'] > 0 and m not in ['PPDA', 'TOTALPOINTS']:
                        val = val / stats['MATCHES']
                    y_vals.append(val)
                
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=y_vals, 
                    marker_color=c["primary"], marker_line_color=c["secondary"], 
                    marker_line_width=1, text=[f"{v:.2f}" if per_match else fmt_val(v) for v in y_vals], textposition='auto'
                ))
            
            fig.update_layout(barmode='group', height=400, margin=dict(t=30, b=20, l=10, r=10),
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with h2h_sub_tabs[0]: 
            create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_sub_tabs[1]: 
            create_h2h_plot(['GOALS', 'XGSHOT', 'PASSESTOFINALTHIRD'], ['Mål/kamp', 'xG/kamp', 'Pass 3.del/kamp'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_sub_tabs[2]: 
            create_h2h_plot(['XGSHOTAGAINST', 'PPDA'], ['xG Imod/kamp', 'PPDA (Pres)'], t1_stats, t2_stats, team1, team2, per_match=True)
