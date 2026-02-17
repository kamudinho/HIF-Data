import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. SETUP & STYLING ---
    st.markdown("""
        <style>
        .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; border-bottom: 3px solid #df003b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen kampdata fundet.")
        return

    # 2. VALG AF MODSTANDER
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    
    valgt_id = navne_dict[valgt_navn]
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 3. STATS PANEL ---
    st.markdown(f"### {valgt_navn.upper()} PROFIL")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Gns. xG", round(df_f['XG'].mean(), 2))
    m2.metric("Skud", int(df_f['SHOTS'].mean()) if 'SHOTS' in df_f else "N/A")
    m3.metric("Possession", f"{round(df_f['POSSESSIONPERCENT'].mean(), 1)}%")
    m4.metric("Mål", round(df_f['GOALS'].mean(), 1))
    
    seneste_3_xg = df_f['XG'].head(3).mean()
    m5.metric("Trend (xG)", f"{round(seneste_3_xg, 2)}", delta=round(seneste_3_xg - df_f['XG'].mean(), 2))

    st.markdown("---")

    # --- 4. TO-DELT LAYOUT (BANE & DATA) ---
    left_col, right_col = st.columns([1.3, 1])

    with left_col:
        st.subheader("Taktisk Heatmap")
        
        # Opret MPLSOCCER bane
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='#f8f9fa', 
            line_color='#1a1a1a', 
            linewidth=1.5,
            goal_type='box'
        )
        fig, ax = pitch.draw(figsize=(8, 11))

        # Integrer Heatmap hvis data findes
        if df_events is not None and not df_events.empty:
            df_p = df_events[
                (df_events['TEAM_WYID'] == valgt_id) & 
                (df_events['PRIMARYTYPE'].str.lower().str.contains('pass', na=False))
            ].copy()
            
            if not df_p.empty:
                sns.kdeplot(
                    x=df_p['LOCATIONY'], y=df_p['LOCATIONX'],
                    ax=ax, fill=True, thresh=0.05, levels=15,
                    cmap='Reds', alpha=0.6, zorder=1, clip=((0, 100), (0, 100))
                )
                
                # Tilføj en lille label for dominanszone
                pitch.annotate(f"HØJESTE INTENSITET\n{valgt_navn}", 
                               xy=(10, 50), va='center', ha='center',
                               ax=ax, fontsize=10, fontweight='bold', color='#df003b',
                               bbox=dict(facecolor='white', alpha=0.6, edgecolor='#df003b', boxstyle='round'))

        st.pyplot(fig)

    with right_col:
        st.subheader("Seneste Resultater")
        mini_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        mini_df['DATE'] = mini_df['DATE'].dt.strftime('%d/%m')
        st.table(mini_df.set_index('DATE'))
        
        # Skud-præcision visualisering
        st.write("**Skud-effektivitet**")
        acc = (df_f['GOALS'].sum() / df_f['SHOTS'].sum() * 100) if 'SHOTS' in df_f and df_f['SHOTS'].sum() > 0 else 0
        st.progress(min(acc/30, 1.0), text=f"{round(acc,1)}% conversion rate")

        st.info(f"""
        **Analytikerens Note:**
        Holdet opererer primært i de mørkerøde zoner på heatmappet. 
        Deres gennemsnitlige xG på {round(df_f['XG'].mean(), 2)} indikerer deres offensive trussel.
        """)

    # 5. Rå data expander
    with st.expander("Se komplet kampdata"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
