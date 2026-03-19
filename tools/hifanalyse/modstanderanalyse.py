import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. UI & CSS STYLING ---
    st.markdown("""
        <style>
            .stTabs { margin-top: -15px; }
            .stat-box { 
                background-color: #f8f9fa; 
                padding: 8px; 
                border-radius: 6px; 
                border-left: 4px solid #df003b; 
                margin-bottom: 5px;
                font-size: 0.85rem;
            }
            .pitch-label {
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 2px;
            }
            /* Gør dropdowns mindre */
            div[data-testid="stSelectbox"] > div {
                min-height: 30px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. FORBEDRET DATA-LOAD (Sørger for at der altid er data) ---
    if "events_data" not in st.session_state:
        try:
            from data.data_load import _get_snowflake_conn
            conn = _get_snowflake_conn()
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
            st.session_state["events_data"] = conn.query(query)
        except Exception as e:
            st.error(f"Kunne ikke forbinde til data: {e}")
            return

    df_events = st.session_state["events_data"].copy()

    # --- 3. TOPBAR ---
    menu_col1, menu_col2, menu_col3 = st.columns([2, 1, 1])
    
    with menu_col1:
        tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with menu_col2:
        hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
        valgt_hold = st.selectbox("Hold:", hold_liste, key="opp_team_sel", label_visibility="collapsed")
    
    with menu_col3:
        hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
        df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Spiller:", spiller_liste, label_visibility="collapsed")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # Type mapping
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. FANER ---
    with tabs[0]:
        st.write(f"Analyse af {valgt_hold}")

    with tabs[1]:
        # Vi bruger et 5-kolonne layout for at få bedre kontrol over midterpladsen
        # [side-buffer, bane1, center-gap, bane2, side-buffer]
        _, b1, gap, b2, _ = st.columns([0.1, 1.5, 0.1, 1.5, 0.1])
        
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        with b1:
            st.markdown('<p class="pitch-label">OPBYGNING</p>', unsafe_allow_html=True)
            # Vi øger figsize for at gøre billedet fysisk større
            fig, ax = pitch.draw(figsize=(6, 8)) 
            ax.set_ylim(0, 50) 
            df_opbyg = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)]
            if not df_opbyg.empty:
                sns.kdeplot(x=df_opbyg['EVENT_Y'], y=df_opbyg['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (0, 50)))
            # use_container_width=True sørger for at billedet udfylder kolonnen helt
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with b2:
            st.markdown('<p class="pitch-label">GENNEMBRUD</p>', unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(6, 8))
            ax.set_ylim(50, 100)
            df_gen = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)]
            if not df_gen.empty:
                sns.kdeplot(x=df_gen['EVENT_Y'], y=df_gen['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    with tabs[2]:
        # Centreret og mindre fuld-bane
        _, mid_col, _ = st.columns([1, 2, 1])
        with mid_col:
            st.markdown('<p class="pitch-label">DEFENSIV INTENSITET</p>', unsafe_allow_html=True)
            pitch_full = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_full.draw(figsize=(5, 7)) # Skaleret ned her
            df_def = df_hold[df_hold['type'].isin(['duel', 'erobring'])]
            if not df_def.empty:
                sns.kdeplot(x=df_def['EVENT_Y'], y=df_def['EVENT_X'], fill=True, cmap='Blues', 
                            alpha=0.6, levels=15, thresh=0.05, ax=ax, clip=((0, 100), (0, 100)))
            st.pyplot(fig)
            plt.close(fig)

    with tabs[3]:
        c1, c2, c3 = st.columns(3)
        for k_id, k_navn, col in [('pass', 'Afleveringer', c1), ('duel', 'Dueller', c2), ('erobring', 'Erobringer', c3)]:
            with col:
                st.markdown(f"**Top {k_navn}**")
                top = df_hold[df_hold['type'] == k_id]['PLAYER_NAME'].value_counts().head(5)
                for navn, count in top.items():
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {navn}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
