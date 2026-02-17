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
    # Vi henter unikke ID'er og mapper dem til navne
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        valgt_navn = st.selectbox("Vælg modstander til analyse:", options=sorted(navne_dict.keys()))
    
    valgt_id = navne_dict[valgt_navn]
    
    # Filtrer kamp-statistik (xG, Possession etc.)
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 3. DASHBOARD METRICS ---
    st.markdown(f"### Statistisk overblik: {valgt_navn.upper()}")
    m1, m2, m3, m4, m5 = st.columns(5)
    
    avg_xg = df_f['XG'].mean()
    avg_poss = df_f['POSSESSIONPERCENT'].mean()
    avg_shots = df_f['SHOTS'].mean() if 'SHOTS' in df_f else 0
    avg_goals = df_f['GOALS'].mean()
    
    # Trend-beregning (Sidste 3 kampe vs gennemsnit)
    seneste_3_xg = df_f['XG'].head(3).mean()
    xg_delta = round(seneste_3_xg - avg_xg, 2)

    m1.metric("Gns. xG", round(avg_xg, 2))
    m2.metric("Skud pr. kamp", round(avg_shots, 1))
    m3.metric("Possession", f"{round(avg_poss, 1)}%")
    m4.metric("Mål pr. kamp", round(avg_goals, 1))
    m5.metric("Trend (xG)", round(seneste_3_xg, 2), delta=xg_delta)

    st.markdown("---")

    # --- 4. HOVEDLAYOUT (BANE & RESULTATER) ---
    left_col, right_col = st.columns([1.4, 1])

    with left_col:
        st.subheader("Positionelt Heatmap")
        
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='#f8f9fa', 
            line_color='#1a1a1a', 
            linewidth=2,
            goal_type='box'
        )
        fig, ax = pitch.draw(figsize=(8, 11))

        if df_events is not None and not df_events.empty:
            # RETTELSE HER: Vi inkluderer alle de typer vi har hentet i SQL
            relevante_typer = ['pass', 'touch', 'throw_in', 'shot', 'interception']
            
            mask = (
                (df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))) & 
                (df_events['PRIMARYTYPE'].fillna('').str.lower().isin(relevante_typer))
            )
            df_p = df_events[mask].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
            
            # DEBUG (Fjern denne når det virker):
            # st.write(f"Antal datapunkter til heatmap: {len(df_p)}")

            if not df_p.empty:
                # Vi bruger de nye kolonnenavne fra din SQL: LOCATIONX og LOCATIONY
                sns.kdeplot(
                    x=df_p['LOCATIONY'], y=df_p['LOCATIONX'],
                    ax=ax, fill=True, thresh=0.05, levels=15,
                    cmap='Reds', alpha=0.6, zorder=1, clip=((0, 100), (0, 100))
                )
                
                pitch.annotate(f"Aktivitetszoner: {valgt_navn}", 
                               xy=(5, 50), va='center', ha='center',
                               ax=ax, fontsize=12, fontweight='bold', color='#df003b',
                               bbox=dict(facecolor='white', alpha=0.8, edgecolor='#df003b', boxstyle='round,pad=0.5'))
            else:
                ax.text(50, 50, "INGEN POSITIONS-DATA\nFOR DETTE HOLD", 
                        size=15, ha="center", va="center", color="grey", alpha=0.5)
        
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
