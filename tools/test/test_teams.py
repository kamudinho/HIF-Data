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
        st.warning("⚠️ Ingen data fundet for den valgte sæson og liga.")
        if st.button("Genindlæs systemet (Ryd Cache)"):
            st.cache_data.clear()
            st.rerun()
        return

    # --- 2. CSS & STYLING ---
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; font-family: sans-serif; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; }
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">BETINIA LIGAEN: ANALYSE & H2H</h3>
    </div>""", unsafe_allow_html=True)

    # --- 3. DATA PREPARATION ---
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)
    
    try:
        saesoner = sorted(df['SEASONNAME'].unique().tolist())
        nyeste_saeson = saesoner[-1]
        df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()
    except Exception as e:
        st.error(f"Fejl ved sortering af sæsoner: {e}")
        return

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
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS', 'GOALS', 'CONCEDEDGOALS']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'MATCHES': 'KAMPE', 'TOTALWINS': 'SEJR', 
                       'TOTALDRAWS': 'UAFGJORT', 'TOTALLOSSES': 'NEDERLAG', 'TOTALPOINTS': 'POINT', 'GOALS': 'MÅL FOR', 'CONCEDEDGOALS': 'MÅL MOD'}
            render_html_table(df_liga.sort_values('TOTALPOINTS', ascending=False), cols, renames)
        
        with l_off:
            df_off = df_liga.copy()
            df_off['XG_DIFF'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XG_DIFF', 'TOUCHINBOX']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'GOALS': 'MÅL', 'XG_DIFF': 'xG (DIFF)', 'TOUCHINBOX': 'BERØRINGER I FELTET'}
            render_html_table(df_off.sort_values('GOALS', ascending=False), cols, renames)

        with l_def:
            df_def = df_liga.copy()
            # CONCEDEDGOALS er fjernet herfra
            df_def['XG_MOD_DIFF'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f}", axis=1)
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'XG_MOD_DIFF', 'PPDA']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'XG_MOD_DIFF': 'xG MOD', 'PPDA': 'PPDA'}
            render_html_table(df_def.sort_values('XGSHOTAGAINST', ascending=True), cols, renames)

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        c1, c2 = st.columns(2)
        with c1: team1 = st.selectbox("Vælg Hold 1", hold_navne, index=0)
        with c2: team2 = st.selectbox("Vælg Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]
        
        h2h_sub_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2, per_match=False):
            fig = go.Figure()
            for name, stats in [(n1, t1), (n2, t2)]:
                c = TEAM_COLORS.get(name, {"primary": "#808080", "secondary": "#000000"})
                y_vals = []
                text_vals = []
                for m in metrics:
                    val = stats[m]
                    if per_match and stats['MATCHES'] > 0 and m != 'PPDA':
                        val = val / stats['MATCHES']
                        text_vals.append(f"{val:.2f}")
                    else:
                        text_vals.append(fmt_val(val))
                    y_vals.append(val)
                
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=y_vals, 
                    marker_color=c["primary"], marker_line_color=c["secondary"], 
                    marker_line_width=2, text=text_vals, textposition='auto'
                ))
            
            logo_imgs = []
            for idx in range(len(labels)):
                for s, offset in [(t1, -0.2), (t2, 0.2)]:
                    if pd.notnull(s['IMAGEDATAURL']):
                        logo_imgs.append(dict(
                            source=s['IMAGEDATAURL'], xref="x", yref="paper", 
                            x=idx + offset, y=1.05, sizex=0.08, sizey=0.08, 
                            xanchor="center", yanchor="bottom"
                        ))
            
            fig.update_layout(
                images=logo_imgs, barmode='group', height=450, 
                margin=dict(t=80, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)

        with h2h_sub_tabs[0]: 
            create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_sub_tabs[1]: 
            create_h2h_plot(['GOALS', 'SHOTS', 'XGSHOT'], ['Mål/kamp', 'Skud/kamp', 'xG/kamp'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_sub_tabs[2]: 
            # CONCEDEDGOALS fjernet fra listen herunder
            create_h2h_plot(['XGSHOTAGAINST', 'PPDA'], ['xG imod/kamp', 'PPDA'], t1_stats, t2_stats, team1, team2, per_match=True)
