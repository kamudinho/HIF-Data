import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING (Uændret) ---
    st.markdown("""
        <style>
        .stMetric { 
            background-color: #ffffff; 
            padding: 15px; 
            border-radius: 10px; 
            border-bottom: 4px solid #df003b; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata i systemet.")
        return

    # --- 2. VALG AF MODSTANDER (Uændret) ---
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        valgt_navn = st.selectbox("Vælg modstander til analyse:", options=sorted(navne_dict.keys()))
    
    valgt_id = navne_dict[valgt_navn]
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    
    # --- 3. DASHBOARD METRICS (Uændret) ---
    st.markdown(f"### Statistisk overblik: {valgt_navn.upper()}")
    # ... (dine metrics køre her) ...

    st.markdown("---")

    # --- 4. HOVEDLAYOUT ---
    left_col, right_col = st.columns([1.4, 1])

    with left_col:
        # NY DROPDOWN TIL VISNINGSTYPE
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
            # Filtrer data for det valgte hold
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()
            
            if not df_hold.empty:
                # A: HEATMAP (Bruger alle touch/pass events)
                if visningstype in ["Heatmap (Aktivitet)", "Alt (Kombineret)"]:
                    sns.kdeplot(
                        x=df_hold['LOCATIONY'], y=df_hold['LOCATIONX'],
                        ax=ax, fill=True, thresh=0.05, levels=15,
                        cmap='Reds', alpha=0.5, zorder=1, clip=((0, 100), (0, 100))
                    )

                # B: PILE (Bruger ENDLOCATION)
                if visningstype in ["Afleveringer (Pile)", "Alt (Kombineret)"]:
                    df_passes = df_hold[df_hold['PRIMARYTYPE'].str.contains('pass', case=False, na=False)].dropna(subset=['ENDLOCATIONX', 'ENDLOCATIONY'])
                    if not df_passes.empty:
                        # Vi tegner kun de seneste 100 afleveringer for at undgå rod
                        pitch.arrows(
                            df_passes['LOCATIONX'].tail(100), df_passes['LOCATIONY'].tail(100),
                            df_passes['ENDLOCATIONX'].tail(100), df_passes['ENDLOCATIONY'].tail(100),
                            width=2, headwidth=3, headlength=3, color='#1a1a1a', alpha=0.3, ax=ax, zorder=2
                        )

                # C: SKUD (Prikker)
                if visningstype in ["Skud (Prikker)", "Alt (Kombineret)"]:
                    df_shots = df_hold[df_hold['PRIMARYTYPE'].str.contains('shot', case=False, na=False)]
                    if not df_shots.empty:
                        pitch.scatter(
                            df_shots['LOCATIONX'], df_shots['LOCATIONY'],
                            s=100, edgecolors='#1a1a1a', c='#df003b', marker='o', ax=ax, zorder=3, label='Skud'
                        )

                pitch.annotate(f"{visningstype}: {valgt_navn}", xy=(5, 50), va='center', ha='center',
                               ax=ax, fontsize=12, fontweight='bold', color='#df003b',
                               bbox=dict(facecolor='white', alpha=0.8, edgecolor='#df003b', boxstyle='round,pad=0.5'))
            else:
                ax.text(50, 50, "INGEN DATA FUNDET", size=15, ha="center", va="center", color="grey")
        
        st.pyplot(fig)


    with right_col:
        st.subheader("Seneste 5 Kampe")
        res_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        res_df['DATE'] = res_df['DATE'].dt.strftime('%d/%m-%y')
        st.table(res_df.set_index('DATE'))
        
        # Skud-effektivitet Progress Bar
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

    # --- 5. RÅ DATA ---
    with st.expander("Se alle rå kampdata for modstanderen"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
