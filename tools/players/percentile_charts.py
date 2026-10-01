# tools/players/percentile_charts.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data.sql.percentile_players import fetch_player_percentiles

def vis_side():
    """
    Hovedfunktion der kaldes af appen uden argumenter.
    Henter data via fetch_player_percentiles().
    """
    st.title("Spillerprofiler & Percentiler")
    st.markdown("Her kan du se rangeringer, top 10-spillere og generere visuelle spillerprofiler i Opta/FBref-stil.")

    # Hent data
    try:
        df = fetch_player_percentiles()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df.empty:
        st.warning("Inden data fundet med de aktuelle filtre.")
        return

    # Opret tabs til navigation
    tab_overview, tab_profile = st.tabs(["🏆 Oversigt & Top 10", "📊 Generér Spillerprofil"])

    with tab_overview:
        st.subheader("Top 10 Spillere per Kategori")
        
        metric_cols = [col for col in df.columns if col not in ['HOLD_NAVN', 'SPILLER_NAVN', 'MINUTTER', 'KAMPE']]
        selected_metric = st.selectbox("Vælg metrik / kategori for Top 10:", metric_cols)

        if selected_metric:
            top_10 = df[['SPILLER_NAVN', 'HOLD_NAVN', 'MINUTTER', selected_metric]].sort_values(by=selected_metric, ascending=False).head(10)
            st.dataframe(top_10.reset_index(drop=True), use_container_width=True)

        st.markdown("---")
        st.subheader("Komplet Datatabel")
        st.dataframe(df, use_container_width=True)

    with tab_profile:
        st.subheader("Visuel Spillerprofil Generator (Opta-stil)")
        
        teams = sorted(df['HOLD_NAVN'].unique())
        selected_team = st.selectbox("Vælg hold:", teams, key="profile_team")
        
        team_players = sorted(df[df['HOLD_NAVN'] == selected_team]['SPILLER_NAVN'].unique())
        selected_player = st.selectbox("Vælg spiller:", team_players, key="profile_player")

        if selected_player:
            player_row = df[df['SPILLER_NAVN'] == selected_player].iloc[0]

            metrics_config = [
                ("Non-Penalty Goals", "NP_GOALS_P90", "NP_GOALS_PCTILE"),
                ("npxG", "NP_XG_P90", "NP_XG_PCTILE"),
                ("Shots Total", "SHOTS_P90", "SHOTS_PCTILE"),
                ("Assists", "ASSISTS_P90", "ASSISTS_PCTILE"),
                ("xA", "XA_P90", "XA_PCTILE"),
                ("Key Passes", "KEY_PASSES_P90", "KEY_PASSES_PCTILE"),
                ("Passes Attempted", "PASSES_ATTEMPTED_P90", "PASSES_ATTEMPTED_PCTILE"),
                ("Pass Completion %", "PASS_COMPLETION_PCT", "PASS_COMPLETION_PCTILE"),
                ("Touches (Att Pen)", "TOUCHES_IN_BOX_P90", "TOUCHES_IN_BOX_PCTILE"),
                ("Tackles Won", "TACKLES_WON_P90", "TACKLES_WON_PCTILE"),
                ("Interceptions", "INTERCEPTIONS_P90", "INTERCEPTIONS_PCTILE"),
                ("Clearances", "CLEARANCES_P90", "CLEARANCES_PCTILE"),
                ("Ball Recoveries", "BALL_RECOVERIES_P90", "BALL_RECOVERIES_PCTILE"),
                ("Dribbles Succ.", "DRIBBLES_SUCC_P90", "DRIBBLES_SUCC_PCTILE"),
                ("Aerial Duels Won", "AERIAL_DUELS_WON_P90", "AERIAL_DUELS_WON_PCTILE")
            ]

            labels = []
            values_p90 = []
            percentiles = []

            for label, p90_col, pct_col in metrics_config:
                if p90_col in player_row and pct_col in player_row:
                    labels.append(label)
                    values_p90.append(player_row[p90_col])
                    percentiles.append(player_row[pct_col])

            # Byg matplotlib-figur
            fig, ax = plt.subplots(figsize=(10, len(labels) * 0.45 + 1.8))
            
            y_pos = np.arange(len(labels))

            ax.set_xlim(-45, 110)
            ax.set_ylim(-1, len(labels))
            ax.invert_yaxis()

            ax.set_yticks([])
            ax.xaxis.set_visible(False)
            for spine in ['top', 'right', 'bottom', 'left']:
                ax.spines[spine].set_visible(False)

            # Kolonne-overskrifter
            ax.text(-42, -0.8, "Statistic", fontweight='bold', fontsize=9.5, ha='left', color='#222222')
            ax.text(-8, -0.8, "Per 90", fontweight='bold', fontsize=9.5, ha='right', color='#222222')
            ax.text(50, -0.8, "Percentile", fontweight='bold', fontsize=9.5, ha='center', color='#222222')
            ax.axhline(-0.4, color='#333333', linewidth=1)

            for i, (label, val, pct) in enumerate(zip(labels, values_p90, percentiles)):
                # 1. Skyggebar (0 til 100)
                ax.barh(i, 100, left=0, height=0.6, color='#e9ecef', alpha=0.6)

                # 2. Vælg farve til den faktiske percentil-bar
                if pct >= 75:
                    bar_color = '#55a868'  # Grøn
                elif pct >= 40:
                    bar_color = '#999999'  # Grå
                else:
                    bar_color = '#c44e52'  # Rødbrun

                # 3. Den faktiske percentil-bar
                ax.barh(i, pct, left=0, height=0.6, color=bar_color, alpha=0.9)

                # Indsæt statistikkens navn og Per 90 værdi i venstre side
                ax.text(-42, i, label, va='center', ha='left', fontsize=9.5, color='#222222')
                
                val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
                if "%" in label and isinstance(val, float):
                    val_str = f"{val:.1f}%"
                ax.text(-8, i, val_str, va='center', ha='right', fontsize=9.5, fontweight='semibold', color='#222222')

                # 4. Placer percentil-tallet: Hvis baren er bred nok (> 12), sættes den inde i baren (højrejusteret). 
                # Hvis baren er for kort, placeres den lige uden for baren, så den altid kan ses.
                if pct >= 12:
                    pct_x = pct - 2
                    text_align = 'right'
                    text_color = 'white'
                else:
                    pct_x = pct + 2
                    text_align = 'left'
                    text_color = '#333333'

                ax.text(pct_x, i, f"{int(pct)}", va='center', ha=text_align, fontsize=9, fontweight='bold', color=text_color)

                ax.axhline(i + 0.5, color='#f1f3f5', linewidth=0.5)

            # Top boks over det hele
            ax.set_title("vs. Ligaen / Spillere", fontsize=11, fontweight='bold', color='white', backgroundcolor='#1b4d3e', pad=15, loc='left')

            # Fodnote
            minutter = player_row['MINUTTER']
            kampe = player_row['KAMPE']
            fig.text(0.05, 0.02, f"Spiller sammenlignet med ligastandarder. Baseret på {minutter} minutter fordelt på {kampe} kampe.", fontsize=8.5, fontstyle='italic', color='#555555')

            plt.tight_layout()
            st.pyplot(fig)
