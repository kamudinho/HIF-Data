import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

# 0. Konfiguration af Farver (Med de rettede kombinationer)
TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},    # Rød med blå border
    "B.93": {"primary": "#0000ff", "secondary": "#ffffff"},        # Blå med hvid border
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},    # Orange med sort border
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},     # Blå med hvid border
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},      # Kongeblå med hvid border
    "Horsens": {"primary": "#ffff00", "secondary": "#000000"},     # Gul med sort border
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},  # Lys blå med hvid border
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},         # Rød med hvid border
    "Kolding IF": {"primary": "#ffffff", "secondary": "#0000ff"},  # Hvid med blå border
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},       # Gul med blå border
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},     # Sort med blå border
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"} # Sort med gul border
}

def vis_side():
    # 1. CSS Styling & Header
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            .custom-header {
                display: flex; align-items: center; justify-content: center; height: 60px;
                background-color: #cc0000; color: white; border-radius: 8px;
                margin-bottom: 20px; font-weight: bold; font-size: 24px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-header">NORDICBET LIGA: ANALYSE & H2H</div>', unsafe_allow_html=True)

    # 2. Data Loading
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    df_raw = load_snowflake_query("team_stats_full", "(328)", dp.get("season_filter", "='2025/2026'"))

    if df_raw is None or df_raw.empty:
        st.error("❌ Ingen data fundet i Snowflake. Prøv at rydde cachen (tast 'C').")
        return

    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)

    try:
        saesoner = sorted(df['SEASONNAME'].unique().tolist())
        nyeste_saeson = saesoner[-1]
        df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()
    except Exception as e:
        st.error(f"Fejl ved behandling af sæson-data: {e}")
        return

    # 3. HOVED TABS
    tab_liga_hoved, tab_h2h_hoved = st.tabs(["Ligaoversigt", "Head-to-Head"])

    # --- SEKTION 1: LIGAOVERSIGT ---
    with tab_liga_hoved:
        l_gen, l_off, l_def = st.tabs(["Stilling", "Offensivt", "Defensivt"])
        
        with l_gen:
            cols = ['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS', 'GOALS', 'CONCEDEDGOALS']
            st.dataframe(
                df_liga[cols].sort_values('TOTALPOINTS', ascending=False),
                use_container_width=True, hide_index=True, height=500,
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"), 
                    "TEAMNAME": "HOLD", "MATCHES": "KAMPE", "TOTALPOINTS": "POINT",
                    "TOTALWINS": "SEJR", "TOTALLOSSES": "NEDERLAG", "TOTALDRAWS": "UAFGJORT",
                    "GOALS": "MÅL FOR", "CONCEDEDGOALS": "MÅL MOD"
                }
            )
        
        with l_off:
            df_off = df_liga.copy()
            df_off['XG (DIFF)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)
            st.dataframe(
                df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'XG (DIFF)', 'TOUCHINBOX']].sort_values('GOALS', ascending=False), 
                use_container_width=True, hide_index=True, 
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"), 
                    "TEAMNAME": "HOLD", "GOALS": "MÅL", "XG (DIFF)": "xG (DIFF)", "TOUCHINBOX": "BERØRINGER I FELT"
                }
            )
            
        with l_def:
            df_def = df_liga.copy()
            df_def['XG MOD (DIFF)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['CONCEDEDGOALS']-r['XGSHOTAGAINST']):+.2f})", axis=1)
            st.dataframe(
                df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'XG MOD (DIFF)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True), 
                use_container_width=True, hide_index=True, 
                column_config={
                    "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                    "TEAMNAME": "HOLD", "CONCEDEDGOALS": "MÅL MOD", "XG MOD (DIFF)": "xG MOD (DIFF)", "PPDA": "PPDA"
                }
            )

    # --- SEKTION 2: HEAD-TO-HEAD ---
    with tab_h2h_hoved:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        _, c_t1, c_t2 = st.columns([0.1, 1, 1])
        
        with c_t1: 
            team1 = st.selectbox("Hold 1", hold_navne, index=hold_navne.index("Hvidovre") if "Hvidovre" in hold_navne else 0)
        with c_t2: 
            team2 = st.selectbox("Hold 2", [h for h in hold_navne if h != team1], index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        h2h_tabs = st.tabs(["Overblik", "Offensiv", "Defensiv"])

        def create_h2h_plot(metrics, labels, t1, t2, n1, n2):
            fig = go.Figure()
            for name, stats in [(n1, t1), (n2, t2)]:
                c = TEAM_COLORS.get(name, {"primary": "#808080", "secondary": "#000000"})
                fig.add_trace(go.Bar(
                    name=name, x=labels, y=[stats[m] for m in metrics], 
                    marker_color=c["primary"],
                    marker_line_color=c["secondary"],
                    marker_line_width=2,
                    text=[fmt_val(stats[m]) for m in metrics], 
                    textposition='auto', showlegend=False
                ))
            
            logo_imgs = []
            # Vi justerer offset en lille smule (fra 0.17 til 0.18) 
            # for at de passer over de nu smallere søjler
            for idx in range(len(labels)):
                for s, offset in [(t1, -0.18), (t2, 0.18)]:
                    if pd.notnull(s['IMAGEDATAURL']):
                        logo_imgs.append(dict(
                            source=s['IMAGEDATAURL'], xref="x", yref="paper", 
                            x=idx + offset, y=1.02, sizex=0.07, sizey=0.07, 
                            xanchor="center", yanchor="bottom"
                        ))
            
            fig.update_layout(
                images=logo_imgs, 
                barmode='group', 
                bargap=0.4,       # Mellemrum mellem de forskellige metrikker (f.eks. Mål vs xG)
                bargroupgap=0.1,  # Mellemrum mellem Hold 1 og Hold 2 søjlen
                height=400, 
                margin=dict(t=70, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False), 
                yaxis=dict(showgrid=False, showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)

        with h2h_tabs[0]: create_h2h_plot(['TOTALPOINTS', 'TOTALWINS', 'MATCHES'], ['Point', 'Sejre', 'Kampe'], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[1]: create_h2h_plot(['GOALS', 'SHOTS', 'XGSHOT'], ['Mål', 'Skud' 'xG''], t1_stats, t2_stats, team1, team2)
        with h2h_tabs[2]: create_h2h_plot(['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA'], ['Mål Imod', 'xG Imod', 'PPDA'], t1_stats, t2_stats, team1, team2)
