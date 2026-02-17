import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    st.markdown(f"<h2 style='text-align: center; color: #df003b;'>MODSTANDERANALYSE</h2>", unsafe_allow_html=True)
    
    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen data fundet.")
        return

    # 1. VALG AF MODSTANDER
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    valgt_id = navne_dict[valgt_navn]

    # Filtrering af data
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 2. STATS BOKS (Layoutmæssig info) ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Gns. xG", round(df_f['XG'].mean(), 2))
    with c2: st.metric("Gns. Skud", int(df_f['SHOTS'].mean()) if 'SHOTS' in df_f else "N/A")
    with c3: st.metric("Possession", f"{round(df_f['POSSESSIONPERCENT'].mean(), 1)}%")
    with c4: st.metric("Mål pr. kamp", round(df_f['GOALS'].mean(), 1))

    # --- 3. TAKTISK BANE (MPLSOCCER) ---
    st.markdown("### Taktisk Oversigt & Heatmap")
    
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        # Opsætning af banen
        pitch = VerticalPitch(
            pitch_type='wyscout',
            pitch_color='#f8f9fa',
            line_color='#1a1a1a',
            goal_type='box',
            linewidth=1.2
        )
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Integration af data på banen
        # Da vi ikke har alle event-koordinater her, viser vi holdets offensive profil
        avg_xg = df_f['XG'].mean()
        
        # Tilføj tekst-info direkte på banen (f.eks. i modstanderens felt)
        pitch.annotate(f"Offensiv Styrke\nxG: {round(avg_xg, 2)}", 
                       xy=(85, 50), va='center', ha='center',
                       ax=ax, fontsize=12, fontweight='bold',
                       bbox=dict(facecolor='#df003b', alpha=0.1, edgecolor='#df003b', boxstyle='round,pad=0.5'))

        # Hvis vi har event-data (df_events), kan vi plotte heatmappet ovenpå
        if df_events is not None and not df_events.empty:
            df_p = df_events[
                (df_events['TEAM_WYID'] == valgt_id) & 
                (df_events['PRIMARYTYPE'].str.lower().str.contains('pass', na=False))
            ].copy()
            
            if not df_p.empty:
                import seaborn as sns
                sns.kdeplot(
                    x=df_p['LOCATIONY'], y=df_p['LOCATIONX'],
                    ax=ax, fill=True, thresh=0.1, levels=10,
                    cmap='Reds', alpha=0.5, zorder=1, clip=((0, 100), (0, 100))
                )

        st.pyplot(fig)

    with col_right:
        st.subheader("Seneste 5 Resultater")
        res_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        res_df['DATE'] = res_df['DATE'].dt.strftime('%d/%m')
        st.table(res_df.set_index('DATE'))

        # Infoboks til noter
        st.info(f"""
        **Analyse af {valgt_navn}:**
        - Holdet har et gennemsnitligt opspil centreret i de markerede zoner.
        - Seneste kamp resulterede i {df_f['GOALS'].iloc[0]} mål med en xG på {round(df_f['XG'].iloc[0], 2)}.
        """)

    # 4. Rå data i bunden
    with st.expander("Se fuld kamphistorik"):
        st.dataframe(df_f, use_container_width=True)
