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
        st.warning("Ingen data fundet for den valgte sæson og liga.")
        return

    # --- 2. CSS & STYLING (Helt rent design) ---
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; font-family: sans-serif; font-size: 0.9rem; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; font-weight: bold; }
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            div[data-testid="stExpander"] { border: none !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">BETINIA LIGAEN: ANALYSE OG H2H</h3>
    </div>""", unsafe_allow_html=True)

    # --- 3. DATA PREPARATION ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)
    
    saesoner = sorted(df['SEASONNAME'].unique().tolist())
    df_liga = df[df['SEASONNAME'] == saesoner[-1]].copy()

    # --- 4. TABS STRUKTUR ---
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

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
            # Her er CONCEDEDGOALS med igen
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'GOALS', 'CONCEDEDGOALS', 'TOTALPOINTS']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'MATCHES': 'K', 'TOTALWINS': 'V', 'TOTALDRAWS': 'U', 
                       'TOTALLOSSES': 'T', 'GOALS': 'M+', 'CONCEDEDGOALS': 'M-', 'TOTALPOINTS': 'P'}
            render_html_table(df_liga.sort_values('TOTALPOINTS', ascending=False), cols, renames)
        
        with l_off:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XGSHOT', 'SHOTS', 'PASSESTOFINALTHIRD']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'GOALS': 'MÅL', 'XGSHOT': 'xG', 'SHOTS': 'SKUD', 'PASSESTOFINALTHIRD': 'PASS 3.DEL'}
            render_html_table(df_liga.sort_values('GOALS', ascending=False), cols, renames)

        with l_def:
            # Her er CONCEDEDGOALS også med i den defensive tabel
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'CONCEDEDGOALS': 'MÅL IMOD', 'XGSHOTAGAINST': 'xG IMOD', 'PPDA': 'PPDA'}
            render_html_table(df_liga.sort_values('CONCEDEDGOALS', ascending=True), cols, renames)

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", hold_navne, index=0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]
        
        h2h_sub_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2, per_match=False):
            fig = go.Figure()
            
            # Beregn værdier for begge hold
            y1 = [t1[m] / t1['MATCHES'] if per_match and t1['MATCHES'] > 0 and m != 'PPDA' else t1[m] for m in metrics]
            y2 = [t2[m] / t2['MATCHES'] if per_match and t2['MATCHES'] > 0 and m != 'PPDA' else t2[m] for m in metrics]
            
            # Tilføj Bar for Hold 1
            c1 = TEAM_COLORS.get(n1, {"primary": "#808080", "secondary": "#000000"})
            fig.add_trace(go.Bar(
                name=n1, x=labels, y=y1,
                marker_color=c1["primary"], marker_line_color=c1["secondary"],
                marker_line_width=1, showlegend=False,
                text=[f"{v:.1f}" for v in y1], textposition='auto'
            ))
        
            # Tilføj Bar for Hold 2
            c2 = TEAM_COLORS.get(n2, {"primary": "#808080", "secondary": "#000000"})
            fig.add_trace(go.Bar(
                name=n2, x=labels, y=y2,
                marker_color=c2["primary"], marker_line_color=c2["secondary"],
                marker_line_width=1, showlegend=False,
                text=[f"{v:.1f}" for v in y2], textposition='auto'
            ))
        
            # --- PLACERING AF MINI-IKONER ---
            # Vi placerer ikonerne manuelt over hver bar ved hjælp af annotations
            icon_size = 25  # Størrelse i pixels
            
            for i, label in enumerate(labels):
                # Logo over Hold 1's bar (forskudt lidt til venstre i gruppen)
                fig.add_layout_image(
                    dict(
                        source=t1['IMAGEDATAURL'],
                        xref="x", yref="y",
                        x=label, y=y1[i],
                        sizex=0.2, sizey=max(max(y1), max(y2)) * 0.1, # Skalerer ift. data
                        xanchor="right", yanchor="bottom",
                        opacity=0.9
                    )
                )
                # Logo over Hold 2's bar (forskudt lidt til højre i gruppen)
                fig.add_layout_image(
                    dict(
                        source=t2['IMAGEDATAURL'],
                        xref="x", yref="y",
                        x=label, y=y2[i],
                        sizex=0.2, sizey=max(max(y1), max(y2)) * 0.1,
                        xanchor="left", yanchor="bottom",
                        opacity=0.9
                    )
                )
        
            # Find max værdi for at sætte aksen korrekt så der er plads til ikonerne
            max_val = max(max(y1), max(y2))
            
            fig.update_layout(
                barmode='group',
                height=400,
                margin=dict(t=50, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                yaxis=dict(range=[0, max_val * 1.3], showgrid=False) # Giver 30% ekstra plads i toppen
            )
            
            st.plotly_chart(fig, use_container_width=True)

        with h2h_sub_tabs[0]: 
            create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_sub_tabs[1]: 
            create_h2h_plot(['GOALS', 'XGSHOT', 'PASSESTOFINALTHIRD'], ['Mål/kamp', 'xG/kamp', 'Pass 3.del/kamp'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_sub_tabs[2]: 
            # CONCEDEDGOALS er nu med i H2H defensiv grafen
            create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål imod/kamp', 'xG Imod/kamp', 'PPDA'], t1_stats, t2_stats, team1, team2, per_match=True)
