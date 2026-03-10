import streamlit as st
import pandas as pd
import seaborn as sns
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # 1. Udpak data fra din pakke
    df_matches = analysis_package.get("matches", pd.DataFrame())
    # Her henter vi de nye events vi lige har lavet query på
    if "events_data" not in st.session_state:
        from data.data_load import _get_snowflake_conn
        from data.sql.opta_queries import get_opta_queries
        conn = _get_snowflake_conn()
        queries = get_opta_queries(analysis_package["config"]["liga_navn"], analysis_package["config"]["season"])
        st.session_state["events_data"] = pd.DataFrame(conn.query(queries["opta_events"]))
    
    df_events = st.session_state["events_data"]
    
    # --- UI SETUP ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"

    st.markdown(f'<div style="background-color:{HIF_ROD}; padding:10px; border-radius:5px; border-left:5px solid {HIF_GOLD};"><h3 style="color:white; margin:0;">MODSTANDERANALYSE (OPTA DATA)</h3></div>', unsafe_allow_html=True)

    # --- DROPDOWNS ---
    # Vi bruger Contestant navne fra matchinfo
    hold_options = pd.concat([
        df_matches[['HOME_CONTESTANT_NAME', 'HOME_CONTESTANT_OPTAUUID']].rename(columns={'HOME_CONTESTANT_NAME': 'NAVN', 'HOME_CONTESTANT_OPTAUUID': 'UUID'}),
        df_matches[['AWAY_CONTESTANT_NAME', 'AWAY_CONTESTANT_OPTAUUID']].rename(columns={'AWAY_CONTESTANT_NAME': 'NAVN', 'AWAY_CONTESTANT_OPTAUUID': 'UUID'})
    ]).drop_duplicates().sort_values('NAVN')

    col1, col2 = st.columns(2)
    with col1:
        valgt_navn = st.selectbox("Vælg Modstander:", hold_options['NAVN'].unique())
        valgt_uuid = hold_options[hold_options['NAVN'] == valgt_navn]['UUID'].iloc[0]
    with col2:
        halvdel = st.radio("Fokus:", ["Offensiv", "Defensiv"], horizontal=True)

    # --- HEATMAPS ---
    st.subheader(f"Positionel Analyse: {valgt_navn}")
    
    # Filtrer events for det valgte hold (Opta bruger UUID)
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid].copy()

    if not df_hold_ev.empty:
        # Opta bane er 0-100. VerticalPitch med 'opta' type.
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#f8f9fa', line_color='#333')
        main_col, side_col = st.columns([3, 1])
        
        with main_col:
            c1, c2, c3 = st.columns(3)
            
            # Logik for spejling (Opta x går mod 100 som angrebsretning)
            if halvdel == "Offensiv":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50]
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                # Spejl defensiv aktion til toppen af banen
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            plots = [ (c1, "Passes", "pass", "Reds"), (c2, "Duels", "duel", "Blues"), (c3, "Recov.", "interception", "Greens") ]

            for col, title, p_type, cmap in plots:
                with col:
                    st.caption(f"**{title}**")
                    fig, ax = pitch.draw()
                    df_f = df_plot[df_plot['PRIMARYTYPE'] == p_type]
                    if not df_f.empty:
                        sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, fill=True, cmap=cmap, alpha=0.7, levels=10, thresh=0.1)
                    st.pyplot(fig)
    else:
        st.warning(f"Ingen hændelsesdata fundet i de seneste 6000 events for {valgt_navn}")
