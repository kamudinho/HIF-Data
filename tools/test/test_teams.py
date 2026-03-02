import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_team_color

def vis_side(df_raw=None, colors_map=None): 
    # --- 1. DATA INITIALISERING ---
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet. Genstart venligst appen.")
        return
        
    dp = st.session_state["dp"]
    logo_map = dp.get("logo_map", {})
    
    if df_raw is None or df_raw.empty:
        df_raw = dp.get("team_stats_full", pd.DataFrame())

    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 2. CSS & STYLING ---
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; font-size: 0.85rem; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; font-weight: bold; }
            button[data-baseweb='tab'][aria-selected='true'] { color: #cc0000 !important; border-bottom-color: #cc0000 !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. DATA PREPARATION ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df_liga = df[df['SEASONNAME'] == dp['SEASONNAME']].copy()

    # --- 4. TABS STRUKTUR ---
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT (Som før) ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        def render_table(d, cols, renames):
            t = d[cols].copy()
            if 'IMAGEDATAURL' in t.columns:
                t['IMAGEDATAURL'] = t['IMAGEDATAURL'].apply(lambda x: f'<img src="{x}" width="25">')
            st.write(t.rename(columns=renames).to_html(escape=False, index=False), unsafe_allow_html=True)

        with l_gen:
            render_table(df_liga.sort_values('TOTALPOINTS', ascending=False), 
                        ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS'],
                        {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'MATCHES': 'K', 'TOTALWINS': 'V', 'TOTALDRAWS': 'U', 'TOTALLOSSES': 'T', 'TOTALPOINTS': 'P'})
        # (Off og Def kodes på samme måde...)

    # --- SEKTION 2: HEAD-TO-HEAD (OPDATERET MED LOGOER) ---
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
        
        # Beregn værdier
        y1_vals = [t1[m] / t1['MATCHES'] if per_match and t1['MATCHES'] > 0 and m != 'PPDA' else t1[m] for m in metrics]
        y2_vals = [t2[m] / t2['MATCHES'] if per_match and t2['MATCHES'] > 0 and m != 'PPDA' else t2[m] for m in metrics]
        
        # Hent farve-objekter fra TEAM_COLORS (via data_load eller direkte fra dp["colors"])
        # Vi antager her, at get_team_color returnerer hele dict'en eller vi slår op i dp["colors"]
        c1 = dp["colors"].get(n1, {"primary": "#808080", "secondary": "#000000"})
        c2 = dp["colors"].get(n2, {"primary": "#808080", "secondary": "#000000"})
        
        # Søjle for Hold 1
        fig.add_trace(go.Bar(
            name=n1, 
            x=labels, 
            y=y1_vals, 
            marker_color=c1["primary"],
            marker_line_color=c1["secondary"], # Kantfarve til f.eks. Kolding
            marker_line_width=2,               # Gør kanten tydelig
            text=[f"{v:.1f}" for v in y1_vals], 
            textposition='auto',
            textfont=dict(color="white" if c1["primary"] != "#ffffff" else "black") # Tekstfarve-fix
        ))
        
        # Søjle for Hold 2
        fig.add_trace(go.Bar(
            name=n2, 
            x=labels, 
            y=y2_vals, 
            marker_color=c2["primary"],
            marker_line_color=c2["secondary"], # Kantfarve
            marker_line_width=2,
            text=[f"{v:.1f}" for v in y2_vals], 
            textposition='auto',
            textfont=dict(color="white" if c2["primary"] != "#ffffff" else "black")
        ))
    
        # Logo-logik (som før)
        for i in range(len(labels)):
            if n1 in logo_map:
                fig.add_layout_image(dict(source=logo_map[n1], xref="x", yref="paper", x=i - 0.18, y=1.1, sizex=0.12, sizey=0.12, xanchor="center", yanchor="middle"))
            if n2 in logo_map:
                fig.add_layout_image(dict(source=logo_map[n2], xref="x", yref="paper", x=i + 0.18, y=1.1, sizex=0.12, sizey=0.12, xanchor="center", yanchor="middle"))
    
        fig.update_layout(
            barmode='group',
            height=400,
            margin=dict(t=100, b=40, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            yaxis=dict(showgrid=False, zeroline=True, showticklabels=False)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Plot kald
        with h2h_sub_tabs[0]: create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_sub_tabs[1]: create_h2h_plot(['GOALS', 'XGSHOT', 'PASSESTOFINALTHIRD'], ['Mål/k', 'xG/k', 'Pass 3.del/k'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_sub_tabs[2]: create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål imod/k', 'xG Imod/k', 'PPDA'], t1_stats, t2_stats, team1, team2, per_match=True)
