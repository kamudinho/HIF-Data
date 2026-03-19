import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    if analysis_package is None:
        st.error("Ingen datapakke fundet. Sørg for at get_analysis_package() kører.")
        return

    # --- 1. DATA-LOAD FRA PAKKEN ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_shapes = analysis_package.get("shapes", pd.DataFrame())
    df_shots = analysis_package.get("playerstats", pd.DataFrame()) # Bruges til event-plots

    # --- 2. UI & CSS ---
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

    # --- 3. FILTRERING ---
    col_h1, col_h2, _ = st.columns([1, 1, 2])
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_navne)
    
    # Hent UUID fra matches i stedet for rå events
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0]
    
    # Filtrering af hold-specifik data
    df_hold_events = df_shots[df_shots['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid]
    df_shape_hold = df_shapes[df_shapes['CONTESTANT_OPTAUUID'] == hold_uuid]

    with col_h2:
        spillere = ["Alle spillere"] + sorted(df_hold_events['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spillere)

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # TAB 0: GRUNDSTRUKTUR (Integration af Shape)
    with tabs[0]:
        st.markdown(f"#### Taktisk udgangspunkt: {valgt_hold}")
        if not df_shape_hold.empty:
            meste_brugte = df_shape_hold['SHAPE_FORMATION'].value_counts().idxmax()
            avg_xg = df_shape_hold['SHAPEOUTCOME_XG'].mean()
            
            c1, c2 = st.columns(2)
            c1.metric("Foretrukken formation", meste_brugte)
            c2.metric("Gns. xG pr. kamp", f"{avg_xg:.2f}")
            
            st.write("Seneste benyttede formationer (Shape Data):")
            st.dataframe(df_shape_hold[['SHAPE_LABEL', 'SHAPE_FORMATION', 'SHAPEOUTCOME_XG']].tail(5), use_container_width=True)
        else:
            st.info("Ingen taktisk shape-data fundet for dette hold i Snowflake.")

    # TAB 1: MED BOLD (Bruger df_shots til heatmaps)
    with tabs[1]:
        c1, c2 = st.columns(2)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            df_p = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['EVENT_X'] < 50)]
            if not df_p.empty: sns.kdeplot(x=df_p['EVENT_Y'], y=df_p['EVENT_X'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(0,50)))
            st.pyplot(fig); plt.close(fig)

        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            df_g = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['EVENT_X'] >= 50)]
            if not df_g.empty: sns.kdeplot(x=df_g['EVENT_Y'], y=df_g['EVENT_X'], fill=True, cmap='Reds', ax=ax, clip=((0,100),(50,100)))
            st.pyplot(fig); plt.close(fig)

    # TAB 2: MOD BOLD
    with tabs[2]:
        st.write("Her kan du visualisere defensive aktioner fra df_hold_events...")

    # TAB 3: TOP 5
    with tabs[3]:
        st.markdown(f"**Nøglespillere: {valgt_hold}**")
        top_scorers = df_hold_events['PLAYER_NAME'].value_counts().head(5)
        for name, count in top_scorers.items():
            st.markdown(f'<div class="stat-box"><b>{count}</b> {name}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
