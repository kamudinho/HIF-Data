import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. UI & CSS ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { 
                background-color: #f8f9fa; padding: 8px; border-radius: 6px; 
                border-left: 4px solid #df003b; margin-bottom: 5px; font-size: 0.85rem;
            }
            .pitch-label { text-align: center; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD (Event & Shape data) ---
    if "events_data" not in st.session_state:
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
        
        # Event Query (Eksisterende)
        q_events = """SELECT HOMECONTESTANT_NAME, HOMECONTESTANT_OPTAUUID, EVENT_CONTESTANT_OPTAUUID, 
                      EVENT_TYPEID, EVENT_X, EVENT_Y, PLAYER_NAME 
                      FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS 
                      WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'"""
        st.session_state["events_data"] = conn.query(q_events)

        # Shape Query (Din nye tabel)
        q_shape = """SELECT CONTESTANT_OPTAUUID, SHAPE_FORMATION, SHAPE_LABEL, SHAPEOUTCOME_XG, SHAPEOUTCOME_XT 
                     FROM KLUB_HVIDOVREIF.AXIS.OPTA_SHAPES 
                     WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'"""
        st.session_state["shape_data"] = conn.query(q_shape)

    df_events = st.session_state["events_data"].copy()
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    df_shape_pos = analysis_package.get("shape_positions", pd.DataFrame())
    
    # --- 3. FILTER-RÆKKE ---
    col_h1, col_h2, _ = st.columns([1, 1, 2])
    with col_h1:
        valgt_hold = st.selectbox("Vælg hold:", sorted(df_events['HOMECONTESTANT_NAME'].unique()))
    
    hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()
    df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_h2:
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist()))

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # NY GRUNDSTRUKTUR LOGIK
    with tabs[0]: # GRUNDSTRUKTUR
        st.subheader(f"Taktisk Struktur: {valgt_hold}")
        
        # Filtrér shape-data på det valgte hold
        df_h_shape = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid]
        
        if not df_h_shape.empty:
            meste_brugte = df_h_shape['SHAPE_FORMATION'].value_counts().idxmax()
            avg_xg_shape = df_h_shape['SHAPEOUTCOME_XG'].mean()
            
            c1, c2 = st.columns(2)
            c1.metric("Foretrukken Formation", meste_brugte)
            c2.metric("Gns. xG i denne struktur", f"{avg_xg_shape:.2f}")

            # Vis de seneste 5 formationer i en tabel
            st.write("**Seneste taktik-logs:**")
            st.table(df_h_shape[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5))
        else:
            st.info("Ingen taktisk shape-data fundet for dette hold.")

    # MED BOLD (Som før)
    with tabs[1]:
        c1, c2 = st.columns(2)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        # Opbygning
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            df_p = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['EVENT_X'] < 50)]
            if not df_p.empty: sns.kdeplot(x=df_p['EVENT_Y'], y=df_p['EVENT_X'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(0,50)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        # Gennembrud
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            df_g = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['EVENT_X'] >= 50)]
            if not df_g.empty: sns.kdeplot(x=df_g['EVENT_Y'], y=df_g['EVENT_X'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(50,100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    # MOD BOLD (Kompakt)
    with tabs[2]:
        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            st.markdown('<p class="pitch-label">DEFENSIV INTENSITET</p>', unsafe_allow_html=True)
            pitch_f = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_f.draw(figsize=(4, 6))
            df_d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
            if not df_d.empty: sns.kdeplot(x=df_d['EVENT_Y'], y=df_d['EVENT_X'], fill=True, cmap='Blues', ax=ax, clip=((0,100),(0,100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    # TOP 5 (Som før)
    with tabs[3]:
        cols = st.columns(3)
        for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold[df_hold['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, c in top.items(): st.markdown(f'<div class="stat-box"><b>{c}</b> {n}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
