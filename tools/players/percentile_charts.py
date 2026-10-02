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
    st.markdown("#### Spillerprofiler & Percentiler")
    st.caption("Her kan du se rangeringer, top-spillere og spillerprofiler")

    # Hent data
    try:
        df = fetch_player_percentiles()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df.empty:
        st.warning("Ingen data fundet med de aktuelle filtre.")
        return

    # Omdøb systemkolonner til pænere visning
    rename_dict = {
        'SPILLER_NAVN': 'Navn',
        'HOLD_NAVN': 'Hold',
        'MINUTTER': 'Minutter',
        'KAMPE': 'Kampe'
    }
    df_display = df.rename(columns=rename_dict)

    # Opret tabs til navigation
    tab_overview, tab_profile = st.tabs(["Top 20 Oversigt", "Spillerprofil"])

    with tab_overview:
        st.subheader("Top 20 Spillere per Kategori")
        
        metric_cols = [col for col in df.columns if col not in ['HOLD_NAVN', 'SPILLER_NAVN', 'MINUTTER', 'KAMPE'] and not col.endswith('_PCTILE')]
        selected_metric = st.selectbox("Vælg kategori for Top 20:", metric_cols)

        if selected_metric:
            top_20 = df[['SPILLER_NAVN', 'HOLD_NAVN', selected_metric]].sort_values(by=selected_metric, ascending=True).tail(20)
            
            players = top_20['SPILLER_NAVN'].tolist()
            teams = top_20['HOLD_NAVN'].tolist()
            values = top_20[selected_metric].tolist()
            
            labels = [f"{p} ({t})" for p, t in zip(players, teams)]

            fig, ax = plt.subplots(figsize=(10, len(labels) * 0.4 + 1.5))
            
            y_pos = np.arange(len(labels))
            max_val = max(values) if values else 1
            ax.set_xlim(0, max_val * 1.25 if max_val > 0 else 10)
            ax.set_ylim(-1, len(labels))

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=9, color='#222222')
            ax.xaxis.set_visible(True)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.xaxis.grid(True, linestyle='--', alpha=0.5, color='#cccccc')

            bars = ax.barh(y_pos, values, height=0.6, color='#1b4d3e', alpha=0.9)

            for bar, val in zip(bars, values):
                width = bar.get_width()
                val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
                ax.text(width + (max_val * 0.02), bar.get_y() + bar.get_height()/2, val_str,
                        va='center', ha='left', fontsize=9, fontweight='bold', color='#222222')

            ax.set_title(f"Top 20: {selected_metric}", fontsize=11, fontweight='bold', color='white', backgroundcolor='#1b4d3e', pad=15, loc='left')

            plt.tight_layout()
            st.pyplot(fig)

    with tab_profile:
        st.subheader("Visuel spillerprofil")
        
        teams = sorted(df['HOLD_NAVN'].unique())
        selected_team = st.selectbox("Vælg hold:", teams, key="profile_team")
        
        team_players = sorted(df[df['HOLD_NAVN'] == selected_team]['SPILLER_NAVN'].unique())
        selected_player = st.selectbox("Vælg spiller:", team_players, key="profile_player")

        if selected_player:
            player_row = df[df['SPILLER_NAVN'] == selected_player].iloc[0]

            # Kategoriseret opsætning med farver i stil med billedet
            categories = [
                {
                    "title": "Afslutningsspil",
                    "color": "#2ca02c",  # Grøn
                    "metrics": [
                        ("Non-Penalty Goals", "NP_GOALS_P90", "NP_GOALS_PCTILE"),
                        ("npxG", "NP_XG_P90", "NP_XG_PCTILE"),
                        ("Shots Total", "SHOTS_P90", "SHOTS_PCTILE")
                    ]
                },
                {
                    "title": "Boldbesiddelse",
                    "color": "#d9822b",  # Orange / Gul
                    "metrics": [
                        ("Assists", "ASSISTS_P90", "ASSISTS_PCTILE"),
                        ("xA", "XA_P90", "XA_PCTILE"),
                        ("Key Passes", "KEY_PASSES_P90", "KEY_PASSES_PCTILE"),
                        ("Passes Attempted", "PASSES_ATTEMPTED_P90", "PASSES_ATTEMPTED_PCTILE"),
                        ("Pass Completion %", "PASS_COMPLETION_PCT", "PASS_COMPLETION_PCTILE"),
                        ("Touches (Att Pen)", "TOUCHES_IN_BOX_P90", "TOUCHES_IN_BOX_PCTILE")
                    ]
                },
                {
                    "title": "Forsvarsspil",
                    "color": "#c0392b",  # Rød / Brun
                    "metrics": [
                        ("Tackles Won", "TACKLES_WON_P90", "TACKLES_WON_PCTILE"),
                        ("Interceptions", "INTERCEPTIONS_P90", "INTERCEPTIONS_PCTILE"),
                        ("Clearances", "CLEARANCES_P90", "CLEARANCES_PCTILE"),
                        ("Ball Recoveries", "BALL_RECOVERIES_P90", "BALL_RECOVERIES_PCTILE"),
                        ("Dribbles Succ.", "DRIBBLES_SUCC_P90", "DRIBBLES_SUCC_PCTILE"),
                        ("Aerial Duels Won", "AERIAL_DUELS_WON_P90", "AERIAL_DUELS_WON_PCTILE")
                    ]
                }
            ]

            # Beregn samlet højde baseret på antal rækker og overskrifter
            total_items = sum(len(cat["metrics"]) for cat in categories) + len(categories)
            fig, ax = plt.subplots(figsize=(10, total_items * 0.42 + 2.0))

            ax.set_xlim(-45, 110)
            ax.set_ylim(-1, total_items)
            ax.invert_yaxis()

            ax.set_yticks([])
            ax.xaxis.set_visible(False)
            for spine in ['top', 'right', 'bottom', 'left']:
                ax.spines[spine].set_visible(False)

            current_y = 0

            for cat in categories:
                # Tilføj kategorioverskrift
                ax.text(-45, current_y, cat["title"], fontweight='bold', fontsize=10.5, color='#111111', ha='left')
                ax.axhline(current_y + 0.35, color='#dddddd', linewidth=1)
                current_y += 1

                for label, p90_col, pct_col in cat["metrics"]:
                    if p90_col in player_row and pct_col in player_row:
                        val = player_row[p90_col]
                        pct = player_row[pct_col]

                        # 1. Skyggebar (0 til 100 baggrund)
                        ax.barh(current_y, 100, left=0, height=0.55, color='#e9ecef', alpha=0.6)

                        # 2. Den faktiske percentil-bar med kategoriens farve
                        ax.barh(current_y, pct, left=0, height=0.55, color=cat["color"], alpha=0.9)

                        # 3. Metriknavn i venstre side
                        ax.text(-42, current_y, label, va='center', ha='left', fontsize=9.5, color='#222222')

                        # 4. Placer percentil-tallet (altid inde i baren, eller udenfor hvis baren er for kort)
                        if pct >= 12:
                            pct_x = pct - 2
                            text_align = 'right'
                            text_color = 'white'
                        else:
                            pct_x = pct + 2
                            text_align = 'left'
                            text_color = '#333333'

                        ax.text(pct_x, current_y, f"{int(pct)}", va='center', ha=text_align, fontsize=9, fontweight='bold', color=text_color)

                        ax.axhline(current_y + 0.5, color='#f1f3f5', linewidth=0.5)
                        current_y += 1

            # Titel over det hele
            team_name = selected_team
            ax.set_title(f"{selected_player}: Percentile Ranks among {team_name} (2025/26 Season)", 
                         fontsize=11, fontweight='bold', color='white', backgroundcolor='#1b4d3e', pad=15, loc='left')

            # Fodnote
            minutter = player_row['MINUTTER']
            kampe = player_row['KAMPE']
            fig.text(0.05, 0.01, f"Spiller sammenlignet med hold/ligastandarder. Baseret på {minutter} minutter fordelt på {kampe} kampe.", 
                     fontsize=8.5, fontstyle='italic', color='#555555')

            plt.tight_layout()
            st.pyplot(fig)
