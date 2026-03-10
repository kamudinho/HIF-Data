import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # --- 1. DATA-LOAD SIKRING ---
    # Vi tjekker om data allerede ligger i "kassen" (session_state)
    if "events_data" not in st.session_state:
        with st.spinner("Henter Opta-events fra Snowflake..."):
            try:
                from data.data_load import _get_snowflake_conn
                conn = _get_snowflake_conn()
                
                # Query baseret på dine specifikke liga-UUID'er
                query = """
                SELECT 
                    HOMECONTESTANT_NAME, HOMECONTESTANT_OPTAUUID,
                    EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, 
                    EVENT_X, EVENT_Y, PLAYER_NAME
                FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
                WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
                AND TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
                AND EVENT_TYPEID IN (1, 4, 5, 8, 49)
                """
                df_res = conn.query(query)
                st.session_state["events_data"] = pd.DataFrame(df_res)
            except Exception as e:
                st.error(f"Kunne ikke hente data fra Snowflake: {e}")
                return

    df_events = st.session_state["events_data"]

    # --- 2. UI & STYLING ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"

    st.markdown(f"""
        <div style="background-color:{HIF_ROD}; padding:15px; border-radius:5px; border-left:10px solid {HIF_GOLD}; margin-bottom:25px;">
            <h2 style="color:white; margin:0; text-transform:uppercase; font-size:20px;">
                Hvidovre IF Scout: NordicBet Liga 2025/2026
            </h2>
            <p style="color:white; margin:0; opacity:0.8;">Opta Event Analyse & Heatmaps</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. FILTRERING ---
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    
    col_sel, col_halv = st.columns([2, 1])
    with col_sel:
        valgt_hold = st.selectbox("Vælg modstander:", hold_liste)
    with col_halv:
        halvdel = st.radio("Fokusområde:", ["Offensiv", "Defensiv"], horizontal=True)

    # Find UUID for det valgte hold for at filtrere korrekt på deres egne aktioner
    hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    # Mapping af event-typer
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. SPEJLINGS-LOGIK & POSITIONERING ---
    if halvdel == "Offensiv":
        # Aktioner på modstanderens forreste halvdel (X > 50)
        df_plot = df_hold[df_hold['EVENT_X'] >= 50].copy()
    else:
        # Defensiv: Aktioner på egen halvdel (X < 50), spejlet så det vises øverst
        df_plot = df_hold[df_hold['EVENT_X'] < 50].copy()
        df_plot['EVENT_X'] = 100 - df_plot['EVENT_X']

    # --- 5. VISUALISERING (HEATMAPS) ---
    pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
    
    cols = st.columns(3)
    kategorier = [
        ('pass', 'Afleveringer', 'Reds'),
        ('duel', 'Dueller', 'Blues'),
        ('erobring', 'Erobringer', 'Greens')
    ]

    for i, (kat_id, kat_navn, kat_cmap) in enumerate(kategorier):
        with cols[i]:
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>{kat_navn}</p>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(4, 5))
            df_subset = df_plot[df_plot['type'] == kat_id]

            if not df_subset.empty:
                sns.kdeplot(
                    x=df_subset['EVENT_Y'], 
                    y=df_subset['EVENT_X'], 
                    fill=True, cmap=kat_cmap, alpha=0.7, 
                    levels=10, thresh=0.05, ax=ax,
                    clip=((0, 100), (50, 100))
                )
            else:
                ax.text(50, 75, "Ingen data", ha='center', color='gray')
            
            st.pyplot(fig)
            plt.close(fig)

    # --- 6. TOP SPILLERE (NU MED KORREKT INDRYKNING) ---
    st.write("---")
    st.subheader(f"Mest aktive spillere: {valgt_hold} ({halvdel})")
    
    stat_cols = st.columns(3)
    for i, (kat_id, kat_navn, _) in enumerate(kategorier):
        with stat_cols[i]:
            # Her er indrykningen vigtig! Alt under 'with' hører til kolonnen.
            st.markdown(f"**Top 5: {kat_navn}**")
            
            # Tæl unikke spillernavne for den valgte kategori
            top_spillere = df_plot[df_plot['type'] == kat_id]['PLAYER_NAME'].value_counts().head(5)
            
            if not top_spillere.empty:
                for navn, count in top_spillere.items():
                    if pd.notna(navn) and navn != "":
                        st.write(f"**{count}** {navn}")
            else:
                st.write("Ingen hændelser")

# Denne del sørger for at kalde funktionen hvis du tester filen direkte
if __name__ == "__main__":
    vis_side(None)
