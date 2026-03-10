import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # --- 1. DATA-LOAD SIKRING ---
    # Hvis data ikke findes i session_state, henter vi det nu
    if "events_data" not in st.session_state:
        with st.spinner("Henter Opta-events fra Snowflake..."):
            try:
                from data.data_load import _get_snowflake_conn
                conn = _get_snowflake_conn()
                
                # Din specifikke query med de UUID'er du sendte
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
                st.error(f"Kunne ikke hente data: {e}")
                return

    df_events = st.session_state["events_data"]

    # --- 2. UI & STYLING ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"

    # --- 3. FILTRERING ---
    # Vi finder alle unikke hold i ligaen fra din query
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    
    col_sel, col_halv = st.columns([2, 1])
    with col_sel:
        valgt_hold = st.selectbox("Vælg hold til analyse:", hold_liste)
    with col_halv:
        halvdel = st.radio("Fokus:", ["Offensiv", "Defensiv"], horizontal=True)

    # Find UUID for det valgte hold for at filtrere events korrekt
    hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    # Mapping
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. SPEJLINGS-LOGIK ---
    if halvdel == "Offensiv":
        df_plot = df_hold[df_hold['EVENT_X'] >= 50].copy()
    else:
        # Defensiv: Vi tager egen halvdel (<50) og spejler X-aksen
        df_plot = df_hold[df_hold['EVENT_X'] < 50].copy()
        df_plot['EVENT_X'] = 100 - df_plot['EVENT_X']
        # Vi rører ikke EVENT_Y, så siderne passer!

    # --- 5. VISUALISERING ---
    pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
    
    cols = st.columns(3)
    kategorier = [
        ('pass', 'Afleveringer', 'Reds'),
        ('duel', 'Dueller', 'Blues'),
        ('erobring', 'Erobringer', 'Greens')
    ]

    for i, (kat_id, kat_navn, kat_cmap) in enumerate(kategorier):
        with cols[i]:
            st.write(f"**{kat_navn}**")
            fig, ax = pitch.draw(figsize=(4, 5))
            df_subset = df_plot[df_plot['type'] == kat_id]

            if not df_subset.empty:
                sns.kdeplot(
                    x=df_subset['EVENT_Y'], 
                    y=df_subset['EVENT_X'], 
                    fill=True, cmap=kat_cmap, alpha=0.7, 
                    levels=10, thresh=0.05, ax=ax,
                    clip=((0, 100), (50, 100)) # Holder det på halvbanen
                )
            else:
                ax.text(50, 75, "Ingen hændelser", ha='center', color='gray')
            
            st.pyplot(fig)
            plt.close(fig)

    # --- 6. TOP SPILLERE ---
    st.write("---")
    
    # Hurtig beregning af top 3 per kategori
    stat_cols = st.columns(3)
    for i, (kat_id, kat_navn, _) in enumerate(kategorier):
        with stat_cols[i]:
        top_spillere = df_plot[df_plot['type'] == kat_id]['PLAYER_NAME'].value_counts().head(5)
        if not top_spillere.empty:
                for navn, count in top_spillere.items():
                    st.write(f"**{count}** {navn}")
            else:
                st.write("Ingen data")
