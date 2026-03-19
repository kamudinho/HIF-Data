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
            /* Gør dropdowns mere kompakte */
            div[data-testid="stSelectbox"] label { display: none; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA SIKKERHED ---
    if not analysis_package:
        st.error("Ingen datapakke modtaget.")
        return

    # Vi henter data fra pakken i stedet for at lave nye queries midt i visningen
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    
    # Opta events ligger ofte i en sub-dict i din struktur
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame())

    if df_events.empty:
        st.warning("Ingen event-data fundet i pakken.")
        return

    # Sørg for at kolonnenavne er konsistente (Upper case)
    df_events.columns = [c.upper() for c in df_events.columns]

    # --- 3. FILTER-RÆKKE (Layout rettelse) ---
    col_h1, col_h2 = st.columns([1, 1])
    
    with col_h1:
        # Vi bruger CONTESTANTHOME_NAME fra matches i stedet for at gætte fra events
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique()) if not df_matches.empty else sorted(df_events['PLAYER_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_navne, key="target_team_select")
    
    # Hent UUID
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0] if not df_matches.empty else ""
    
    # Filtrér data
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy() if hold_uuid else df_events.copy()

    with col_h2:
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist()), key="player_select")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR
        st.write(f"**Taktisk analyse: {valgt_hold}**")
        df_h_shape = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid] if not df_shapes.empty else pd.DataFrame()
        
        if not df_h_shape.empty:
            c1, c2 = st.columns(2)
            meste_brugte = df_h_shape['SHAPE_FORMATION'].value_counts().idxmax()
            avg_xg_shape = df_h_shape['SHAPEOUTCOME_XG'].mean()
            
            c1.metric("Foretrukken Formation", meste_brugte)
            c2.metric("Gns. xG i denne struktur", f"{avg_xg_shape:.2f}")

            st.write("**Seneste taktik-logs:**")
            st.dataframe(df_h_shape[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5), use_container_width=True)
        else:
            st.info("Ingen taktisk shape-data fundet for dette hold.")

    with tabs[1]: # MED BOLD
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        c1, c2 = st.columns(2)
        # Opbygning
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            df_p = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not df_p.empty: sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        # Gennembrud
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            df_g = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not df_g.empty: sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', ax=ax)
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[2]: # MOD BOLD
        st.markdown('<p class="pitch-label">DEFENSIV INTENSITET</p>', unsafe_allow_html=True)
        pitch_f = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
        fig, ax = pitch_f.draw(figsize=(2, 3))
        # 4=Tackle, 5=Duel, 8=Interception, 49=Recovery
        df_d = df_hold[df_hold['EVENT_TYPEID'].isin([4, 5, 8, 49])]
        if not df_d.empty: sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap='Blues', ax=ax)
        st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[3]: # TOP 5
        cols = st.columns(3)
        for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold[df_hold['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, count in top.items(): 
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)

# Sørg for at denne her IKKE er indrykket under vis_side funktionen!
if __name__ == "__main__":
    # Dette er kun til lokal test. I appen kaldes den fra main.py
    vis_side()
