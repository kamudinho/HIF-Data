import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # --- 1. HENT DATA ---
    # Vi antager at data er hentet via din Snowflake query med de UUID'er du sendte
    if "events_data" not in st.session_state:
        st.error("Ingen event-data fundet. Sørg for at data-load kører først.")
        return

    df_events = st.session_state["events_data"]
    df_matches = analysis_package.get("matches", pd.DataFrame())

    # --- 2. STYLING & UI ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"

    st.markdown(f"""
        <div style="background-color:{HIF_ROD}; padding:10px; border-radius:5px; border-left:8px solid {HIF_GOLD}; margin-bottom:20px;">
            <h3 style="color:white; margin:0; text-transform:uppercase;">Opta Positionsanalyse</h3>
        </div>
    """, unsafe_allow_html=True)

    # Vælg hold baseret på de unikke navne i dit data-dump
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    valgt_hold = st.selectbox("Vælg hold til analyse:", hold_liste)
    
    halvdel = st.radio("Vælg fokus:", ["Offensiv", "Defensiv"], horizontal=True, 
                       help="Offensiv: Modstanderens halvdel | Defensiv: Egen halvdel (vises øverst)")

    # --- 3. DATABEHANDLING ---
    # Filtrer på det valgte hold (bruger EVENT_CONTESTANT_OPTAUUID for præcision)
    hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    # Mapping af event typer baseret på din SQL logik
    # 1=Pass, 4/5=Duel, 8=Interception, 49=Recovery
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'

    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. SPEJLINGS-LOGIK (Her fikser vi fejlen) ---
    if halvdel == "Offensiv":
        # Opta: 100 er modstanderens mål. Vi kigger på 50-100.
        df_plot = df_hold[df_hold['EVENT_X'] >= 50].copy()
    else:
        # Opta: 0 er eget mål. Vi tager 0-50.
        df_plot = df_hold[df_hold['EVENT_X'] < 50].copy()
        # Vi spejler KUN X (længden), så eget felt kommer op i toppen.
        # Vi rører IKKE Y, så venstre side bliver i venstre side.
        df_plot['EVENT_X'] = 100 - df_plot['EVENT_X']

    # --- 5. VISUALISERING ---
    pitch = VerticalPitch(pitch_type='opta', half=True, goal_type='box', 
                          pitch_color='#ffffff', line_color='#cccccc')
    
    cols = st.columns(3)
    typer = [('pass', 'Afleveringer', 'Reds'), 
             ('duel', 'Dueller', 'Blues'), 
             ('erobring', 'Erobringer', 'Greens')]

    for i, (t_slug, t_navn, t_cmap) in enumerate(typer):
        with cols[i]:
            st.caption(f"**{t_navn}**")
            fig, ax = pitch.draw(figsize=(4, 6))
            df_type = df_plot[df_plot['type'] == t_slug]

            if not df_type.empty:
                sns.kdeplot(
                    x=df_type['EVENT_Y'], 
                    y=df_type['EVENT_X'], 
                    fill=True, cmap=t_cmap, alpha=0.6, 
                    levels=8, thresh=0.1, ax=ax
                )
            else:
                ax.text(50, 75, "Ingen data", ha='center', alpha=0.5)
            
            st.pyplot(fig)
            plt.close(fig)
