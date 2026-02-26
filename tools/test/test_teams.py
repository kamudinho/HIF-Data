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
    # 1. HENT DATA HVIS DET MANGLER
    if df_raw is None or df_raw.empty:
        if "data_package" not in st.session_state:
            from data.data_load import get_data_package
            st.session_state["data_package"] = get_data_package()
        
        dp = st.session_state["data_package"]
        # Her sikrer vi os, at vi bruger de præcise filtre fra pakken
        df_raw = load_snowflake_query("team_stats_full", dp["comp_filter"], dp["season_filter"])

    # 2. TJEK IGEN - Hvis den stadig er tom, er der ingen data i Snowflake
    if df_raw is None or df_raw.empty:
        st.warning("⚠️ Ingen data fundet for den valgte sæson og liga.")
        # Tilføj en knap til at rydde cachen direkte
        if st.button("Genindlæs data (Ryd Cache)"):
            st.cache_data.clear()
            st.rerun()
        return
        
    # 1. CSS til centrering af st.table (HTML)
    st.markdown("""
        <style>
            .stTable { width: 100%; }
            th, td { text-align: center !important; vertical-align: middle !important; }
            td:nth-child(2), th:nth-child(2) { text-align: left !important; } /* Holdnavn venstrestillet */
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .custom-header {
                display: flex; align-items: center; justify-content: center; height: 60px;
                background-color: #cc0000; color: white; border-radius: 8px;
                margin-bottom: 20px; font-weight: bold; font-size: 24px;
            }
        </style>
    """, unsafe_allow_html=True)

    # 1.2. BRANDING BOKS
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">BETINIA LIGAEN: ANALYSE & H2H</h3>
    </div>""", unsafe_allow_html=True)
    
    # 2. Data Loading
    if df_raw is None:
        if "data_package" not in st.session_state:
            st.session_state["data_package"] = get_data_package()
        dp = st.session_state["data_package"]
        df_raw = load_snowflake_query("team_stats_full", dp["comp_filter"], dp["season_filter"])
    
    # Slet den linje der hedder df_raw = load_snowflake_query("team_stats_full", "(328)", ...) 
    # da den overskriver den data, vi lige har fået!

    if df_raw is None or df_raw.empty:
        st.error("❌ Ingen data fundet i team_stats_full queryen.")
        return

    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)
    
    try:
        saesoner = sorted(df['SEASONNAME'].unique().tolist())
        nyeste_saeson = saesoner[-1]
        df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()
    except Exception as e:
        st.error(f"Fejl: {e}")
        return

    # 3. HOVED TABS (Defineres her før de bruges!)
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        
        def render_html_table(dataframe, columns, rename_dict):
            temp_df = dataframe[columns].copy()
            # Lav logoer til HTML
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
            df_def['XG_MOD_DIFF'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['CONCEDEDGOALS']-r['XGSHOTAGAINST']):+.2f})", axis=1)
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XG_MOD_DIFF', 'PPDA']
            renames = {'IMAGEDATAURL': '', 'TEAMNAME': 'HOLD', 'CONCEDEDGOALS': 'MÅL MOD', 'XG_MOD_DIFF': 'xG MOD (DIFF)', 'PPDA': 'PPDA'}
            render_html_table(df_def.sort_values('CONCEDEDGOALS', ascending=True), cols, renames)

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        _, c_t1, c_t2 = st.columns([0.1, 1, 1])
        with c_t1: team1 = st.selectbox("Hold 1", hold_navne, index=0)
        with c_t2: team2 = st.selectbox("Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]
        h2h_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2, per_match=False):
            fig = go.Figure()
            for name, stats in [(n1, t1), (n2, t2)]:
                c = TEAM_COLORS.get(name, {"primary": "#808080", "secondary": "#000000"})
                y_vals = []
                text_vals = []
                for m in metrics:
                    if per_match and stats['MATCHES'] > 0 and m != 'PPDA':
                        val = stats[m] / stats['MATCHES']
                        y_vals.append(val); text_vals.append(f"{val:.2f}")
                    else:
                        val = stats[m]
                        y_vals.append(val); text_vals.append(fmt_val(val))
                fig.add_trace(go.Bar(name=name, x=labels, y=y_vals, marker_color=c["primary"], marker_line_color=c["secondary"], marker_line_width=2, text=text_vals, textposition='auto', showlegend=False))
            
            logo_imgs = []
            for idx in range(len(labels)):
                for s, offset in [(t1, -0.18), (t2, 0.18)]:
                    if pd.notnull(s['IMAGEDATAURL']):
                        logo_imgs.append(dict(source=s['IMAGEDATAURL'], xref="x", yref="paper", x=idx + offset, y=1.02, sizex=0.07, sizey=0.07, xanchor="center", yanchor="bottom"))
            
            fig.update_layout(images=logo_imgs, barmode='group', bargap=0.4, bargroupgap=0.1, height=400, margin=dict(t=70, b=20, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, showticklabels=False))
            st.plotly_chart(fig, use_container_width=True, key=f"h2h_{'_'.join(metrics)}_{n1}_{n2}")

        with h2h_tabs[0]: create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2, per_match=False)
        with h2h_tabs[1]: create_h2h_plot(['GOALS', 'SHOTS', 'XGSHOT'], ['Mål/kamp', 'Skud/kamp', 'xG/kamp'], t1_stats, t2_stats, team1, team2, per_match=True)
        with h2h_tabs[2]: create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål imod/kamp', 'xG imod/kamp', 'PPDA'], t1_stats, t2_stats, team1, team2, per_match=True)
