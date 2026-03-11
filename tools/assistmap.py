import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

hif_id = TEAMS["Hvidovre"]["opta_uuid"]

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #b8860b; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-item { font-size: 0.8rem; color: #444; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data - nu med de nye SQL-felter
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.caption("Ingen data fundet for denne periode.")
        return

    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])
    DOT_SIZE = 90 
    player_col = 'ASSIST_PLAYER'

    # --- TAB 1: SPILLEROVERSIGT ---
    with tab1:
        st.caption("Sæsonstatistik for Hvidovre IF (Opta Data)")
        
        # Brug den nye SQL logik til at tælle assists (Type 16)
        df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
        df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
        
        df_table = df_assists.groupby(player_col).agg(
            Assists=('is_assist', 'sum'),
            Key_Passes=('is_key_pass', 'sum'),
            Hjørne_Assists=('IS_CORNER', 'sum'),
            Indlæg_Assists=('IS_CROSS', 'sum'),
            Fremadrettede=('IS_PROGRESSIVE', 'sum')
        ).reset_index()

        df_table = df_table.rename(columns={player_col: "Spiller"})
        df_table = df_table.sort_values(["Assists", "Key_Passes"], ascending=False)
        
        st.dataframe(
            df_table,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller"),
                "Assists": st.column_config.NumberColumn("🅰️"),
                "Key_Passes": st.column_config.NumberColumn("🔑"),
                "Hjørne_Assists": st.column_config.NumberColumn("🚩"),
                "Indlæg_Assists": st.column_config.NumberColumn("⚽ Cross"),
                "Fremadrettede": st.column_config.NumberColumn("↗️ Progressive")
            },
            hide_index=True,
            use_container_width=True
        )

    # --- TAB 2: ASSIST-MAP ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([1.8, 1])
        
        with col_ctrl_a:
            st.caption("Filtrér hændelser")
            spiller_liste_a = sorted(df_table["Spiller"].tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
            
            # Nye filtre baseret på dine Qualifiers
            show_corners = st.checkbox("Vis Hjørnespark (🚩)", value=True)
            show_crosses = st.checkbox("Vis Indlæg (⚽)", value=True)
            
            # Filtrering
            df_filtered = df_assists.copy()
            if v_a != "Hvidovre IF":
                df_filtered = df_filtered[df_filtered[player_col] == v_a]
            
            if not show_corners:
                df_filtered = df_filtered[df_filtered['IS_CORNER'] == 0]
            if not show_crosses:
                df_filtered = df_filtered[df_filtered['IS_CROSS'] == 0]
            
            # Stats bokse
            goals_count = df_filtered['is_assist'].sum()
            kp_count = df_filtered['is_key_pass'].sum()
            
            st.markdown(f"""
                <div class="stat-box" style="border-left-color: {HIF_GOLD}">
                    <div class="stat-label">Goal Assists (16)</div>
                    <div class="stat-value">{goals_count}</div>
                </div>
                <div class="stat-box" style="border-color: #888888">
                    <div class="stat-label">Key Passes (13-15)</div>
                    <div class="stat-value">{kp_count}</div>
                </div>
            """, unsafe_allow_html=True)

            # Modtager-info (Top 3 modtagere for den valgte spiller/hold)
            if not df_filtered.empty and 'GOAL_SCORER' in df_filtered.columns:
                st.write("---")
                st.caption("Top Modtagere (Assists/Key Passes)")
                top_targets = df_filtered['GOAL_SCORER'].value_counts().head(3)
                for name, count in top_targets.items():
                    st.markdown(f"<div class='legend-item'>👤 {name}: <b>{count}</b></div>", unsafe_allow_html=True)

        with col_viz_a:
            from mplsoccer import Pitch
            pitch_a = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 6))
            
            if not df_filtered.empty:
                # 1. Tegn Key Passes
                df_kp = df_filtered[df_filtered['is_key_pass'] == 1]
                pitch_a.arrows(df_kp['PASS_START_X'], df_kp['PASS_START_Y'], 
                               df_kp['SHOT_X'], df_kp['SHOT_Y'], 
                               color='#888888', alpha=0.2, width=1, ax=ax_a)
                
                # 2. Tegn Assists (Mål)
                df_gs = df_filtered[df_filtered['is_assist'] == 1]
                # Vi bruger forskellige markører: Stjerne for hjørne, cirkel for åbent spil
                for _, row in df_gs.iterrows():
                    color = HIF_GOLD
                    marker = '*' if row['IS_CORNER'] == 1 else 'o'
                    size = DOT_SIZE + 50 if row['IS_CORNER'] == 1 else DOT_SIZE
                    
                    pitch_a.arrows(row['PASS_START_X'], row['PASS_START_Y'], 
                                   row['SHOT_X'], row['SHOT_Y'], 
                                   color=color, alpha=0.9, width=3, headwidth=5, ax=ax_a)
                    
                    pitch_a.scatter(row['PASS_START_X'], row['PASS_START_Y'], 
                                    marker=marker, s=size, color=color, 
                                    edgecolors='black', linewidth=1, ax=ax_a, zorder=3)

            st.pyplot(fig_a, use_container_width=True)
            st.caption("⭐ = Hjørnespark | ● = Åbent spil / Indlæg")
