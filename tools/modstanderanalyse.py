import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
        .stMetric { 
            background-color: #ffffff; 
            padding: 15px; 
            border-radius: 10px; 
            border-bottom: 4px solid #df003b; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        }
        [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata i systemet.")
        return

    # --- 2. VALG AF MODSTANDER ---
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        valgt_navn = st.selectbox("Vælg modstander til analyse:", options=sorted(navne_dict.keys()))
    
    valgt_id = navne_dict[valgt_navn]
    
    # Forbered kamp-statistik
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 3. DASHBOARD METRICS ---
    avg_xg = df_f['XG'].mean() if 'XG' in df_f else 0
    avg_poss = df_f['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_f else 0
    avg_shots = df_f['SHOTS'].mean() if 'SHOTS' in df_f else 0
    avg_goals = df_f['GOALS'].mean() if 'GOALS' in df_f else 0
    
    seneste_3_xg = df_f['XG'].head(3).mean() if len(df_f) >= 3 else avg_xg
    xg_delta = round(seneste_3_xg - avg_xg, 2)

    st.markdown(f"### Statistisk overblik: {valgt_navn.upper()}")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Gns. xG", round(avg_xg, 2))
    m2.metric("Skud pr. kamp", round(avg_shots, 1))
    m3.metric("Possession", f"{round(avg_poss, 1)}%")
    m4.metric("Mål pr. kamp", round(avg_goals, 1))
    m5.metric("Trend (xG)", round(seneste_3_xg, 2), delta=xg_delta)

    st.markdown("---")

    # --- 4. DE 4 SMÅ BANER (QUAD-VIEW) ---
    st.subheader("Taktisk Positionering & Mønstre")
    c1, c2, c3, c4 = st.columns(4)
    
    pitch = VerticalPitch(
        pitch_type='wyscout', pitch_color='#f8f9fa', 
        line_color='#1a1a1a', linewidth=1, goal_type='box'
    )

    if df_events is not None and not df_events.empty:
        # Alt data for det valgte hold
        df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()
        
        # Find modstanderens modstandere i de samme kampe (til Skud Mod)
        if 'MATCH_WYID' in df_events.columns:
            match_ids = df_hold['MATCH_WYID'].unique()
            df_opponents = df_events[
                (df_events['MATCH_WYID'].isin(match_ids)) & 
                (df_events['TEAM_WYID'].astype(str) != str(int(valgt_id)))
            ].copy()
        else:
            df_opponents = pd.DataFrame()

        # BANE 1: AFLEVERINGER (PILE)
        with c1:
            st.caption("Afleveringer (Seneste 50)")
            fig, ax = pitch.draw(figsize=(4, 6))
            df_p = df_hold[df_hold['PRIMARYTYPE'].fillna('').str.contains('pass', case=False)]
            # Sikker tjek for EndLocation
            cols = df_p.columns.tolist()
            ex = next((c for c in cols if 'ENDLOCATIONX' in c.upper()), None)
            ey = next((c for c in cols if 'ENDLOCATIONY' in c.upper()), None)
            
            if ex and ey:
                df_p = df_p.dropna(subset=[ex, ey]).tail(50)
                pitch.arrows(df_p['LOCATIONX'], df_p['LOCATIONY'], 
                             df_p[ex], df_p[ey], width=1, color='#df003b', alpha=0.6, ax=ax)
            st.pyplot(fig)

        # BANE 2: SKUD (FOR)
        with c2:
            st.caption("Egen Afslutninger")
            fig, ax = pitch.draw(figsize=(4, 6))
            df_s = df_hold[df_hold['PRIMARYTYPE'].fillna('').str.contains('shot', case=False)]
            if not df_s.empty:
                pitch.scatter(df_s['LOCATIONX'], df_s['LOCATIONY'], s=50, c='#df003b', edgecolors='black', ax=ax)
            st.pyplot(fig)

        # BANE 3: SKUD (IMOD)
        with c3:
            st.caption("Skud mod holdet")
            fig, ax = pitch.draw(figsize=(4, 6))
            if not df_opponents.empty:
                df_si = df_opponents[df_opponents['PRIMARYTYPE'].fillna('').str.contains('shot', case=False)]
                if not df_si.empty:
                    pitch.scatter(df_si['LOCATIONX'], df_si['LOCATIONY'], s=50, c='blue', edgecolors='black', ax=ax)
            st.pyplot(fig)

        # BANE 4: DUELLER / AKTIVITET
        with c4:
            st.caption("Duel & Pressionszoner")
            fig, ax = pitch.draw(figsize=(4, 6))
            if not df_hold.empty:
                sns.kdeplot(x=df_hold['LOCATIONY'], y=df_hold['LOCATIONX'], ax=ax, 
                            fill=True, thresh=0.1, levels=10, cmap='Reds', alpha=0.5, zorder=0, clip=((0, 100), (0, 100)))
            st.pyplot(fig)

    st.markdown("---")

    # --- 5. RESULTATTABEL & NOTER ---
    low_left, low_right = st.columns([1, 1])
    
    with low_left:
        st.subheader("Seneste 5 Kampe")
        res_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        res_df['DATE'] = res_df['DATE'].dt.strftime('%d/%m-%y')
        st.table(res_df.set_index('DATE'))

    with low_right:
        st.subheader("Form & Effektivitet")
        total_shots = df_f['SHOTS'].sum()
        total_goals = df_f['GOALS'].sum()
        if total_shots > 0:
            acc = (total_goals / total_shots) * 100
            st.write(f"**Konverteringsrate:** {round(acc, 1)}%")
            st.progress(min(acc/30, 1.0))
        
        st.info(f"""
        **Scout Note:**
        {valgt_navn} opererer med en xG på {round(avg_xg, 2)}. 
        Tjek 'Skud mod holdet' for at se om de tillader mange afslutninger i boksen. 
        Heatmappet til højre afslører deres foretrukne opbygningsside.
        """)

    with st.expander("Se rå data for alle kampe"):
        st.dataframe(df_f, use_container_width=True)
