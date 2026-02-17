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
        [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; }
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
    
    # Forbered data
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 3. BEREGNING AF METRICS (DEM DER MANGLEDE) ---
    avg_xg = df_f['XG'].mean() if 'XG' in df_f else 0
    avg_poss = df_f['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_f else 0
    avg_shots = df_f['SHOTS'].mean() if 'SHOTS' in df_f else 0
    avg_goals = df_f['GOALS'].mean() if 'GOALS' in df_f else 0
    
    # Trend (Sidste 3 kampe)
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

    # --- 4. HOVEDLAYOUT (BANE & TABEL) ---
    left_col, right_col = st.columns([1.4, 1])

    with left_col:
        visningstype = st.selectbox(
            "Vælg visning på banen:", 
            ["Heatmap (Aktivitet)", "Afleveringer (Pile)", "Skud (Prikker)", "Alt (Kombineret)"]
        )
        
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='#f8f9fa', 
            line_color='#1a1a1a', 
            linewidth=2,
            goal_type='box'
        )
        fig, ax = pitch.draw(figsize=(8, 11))

        if df_events is not None and not df_events.empty:
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()
            
            if not df_hold.empty:
                # A: HEATMAP
                if visningstype in ["Heatmap (Aktivitet)", "Alt (Kombineret)"]:
                    sns.kdeplot(
                        x=df_hold['LOCATIONY'], y=df_hold['LOCATIONX'],
                        ax=ax, fill=True, thresh=0.05, levels=15,
                        cmap='Reds', alpha=0.5, zorder=1, clip=((0, 100), (0, 100))
                    )

                # B: PILE (Afleveringer) - SIKKER VERSION
                if visningstype in ["Afleveringer (Pile)", "Alt (Kombineret)"]:
                    mask_pass = df_hold['PRIMARYTYPE'].fillna('').str.contains('pass', case=False)
                    
                    # Vi finder ud af, hvad slut-kolonnerne faktisk hedder i din data
                    cols = df_hold.columns.tolist()
                    end_x = next((c for c in cols if 'ENDLOCATIONX' in c.upper()), None)
                    end_y = next((c for c in cols if 'ENDLOCATIONY' in c.upper()), None)

                    if end_x and end_y:
                        df_passes = df_hold[mask_pass].dropna(subset=[end_x, end_y])
                        if not df_passes.empty:
                            pitch.arrows(
                                df_passes['LOCATIONX'].tail(50), df_passes['LOCATIONY'].tail(50),
                                df_passes[end_x].tail(50), df_passes[end_y].tail(50),
                                width=2, headwidth=3, headlength=3, color='#1a1a1a', alpha=0.3, ax=ax, zorder=2
                            )
                    else:
                        st.warning(f"Slut-koordinater ikke fundet. Tilgængelige kolonner: {cols}")

                # C: SKUD (Prikker)
                if visningstype in ["Skud (Prikker)", "Alt (Kombineret)"]:
                    mask_shot = df_hold['PRIMARYTYPE'].fillna('').str.contains('shot', case=False)
                    df_shots = df_hold[mask_shot]
                    if not df_shots.empty:
                        pitch.scatter(
                            df_shots['LOCATIONX'], df_shots['LOCATIONY'],
                            s=100, edgecolors='#1a1a1a', c='#df003b', marker='o', ax=ax, zorder=3
                        )

                pitch.annotate(f"Analyse: {valgt_navn}", xy=(5, 50), va='center', ha='center',
                               ax=ax, fontsize=12, fontweight='bold', color='#df003b',
                               bbox=dict(facecolor='white', alpha=0.8, edgecolor='#df003b', boxstyle='round,pad=0.5'))
            else:
                ax.text(50, 50, "INGEN POSITIONS-DATA FUNDET", size=15, ha="center", va="center", color="grey")
        
        st.pyplot(fig)

    with right_col:
        st.subheader("Seneste 5 Kampe")
        res_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        res_df['DATE'] = res_df['DATE'].dt.strftime('%d/%m-%y')
        st.table(res_df.set_index('DATE'))
        
        st.write("**Konverteringsrate (Mål/Skud)**")
        total_shots = df_f['SHOTS'].sum()
        total_goals = df_f['GOALS'].sum()
        
        if total_shots > 0:
            acc = (total_goals / total_shots) * 100
            st.progress(min(acc/30, 1.0), text=f"{round(acc, 1)}%")
        else:
            st.write("Ingen skud registreret")

        st.info(f"""
        **Scout Note:**
        Holdet har en gennemsnitlig xG på {round(avg_xg, 2)}. 
        Heatmappet til venstre viser hvor deres opspil er mest koncentreret. 
        Vær opmærksom på deres trend-score, som viser om de er i form.
        """)

    with st.expander("Se alle rå kampdata for modstanderen"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
