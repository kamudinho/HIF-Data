import streamlit as st
import pandas as pd
import seaborn as sns
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # --- 1. DATA LOAD ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    
    # Hent events fra session_state (eller load hvis de mangler)
    if "events_data" not in st.session_state:
        from data.data_load import _get_snowflake_conn
        from data.sql.opta_queries import get_opta_queries
        
        conn = _get_snowflake_conn()
        liga = analysis_package.get("config", {}).get("liga_navn", "")
        saeson = analysis_package.get("config", {}).get("season", "")
        
        q = get_opta_queries(liga, saeson)
        # Vi sikrer os at vi får en ren DataFrame
        res = conn.query(q["opta_events"])
        st.session_state["events_data"] = pd.DataFrame(res)

    df_events = st.session_state["events_data"]

    # --- 2. BRANDING ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"
    
    # --- 3. FILTRERING ---
    try:
        # Samler unikke hold fra matchlisten (Opta navne-standard)
        hold_df = pd.concat([
            df_matches[['CONTESTANTHOME_NAME', 'CONTESTANTHOME_OPTAUUID']].rename(
                columns={'CONTESTANTHOME_NAME': 'NAVN', 'CONTESTANTHOME_OPTAUUID': 'UUID'}
            ),
            df_matches[['CONTESTANTAWAY_NAME', 'CONTESTANTAWAY_OPTAUUID']].rename(
                columns={'CONTESTANTAWAY_NAME': 'NAVN', 'CONTESTANTAWAY_OPTAUUID': 'UUID'}
            )
        ]).drop_duplicates().sort_values('NAVN')

        col_sel, col_halv = st.columns([2, 1])
        with col_sel:
            valgt_hold_navn = st.selectbox("Vælg Modstander:", hold_df['NAVN'].unique())
            valgt_uuid = hold_df[hold_df['NAVN'] == valgt_hold_navn]['UUID'].iloc[0]
        
        with col_halv:
            halvdel = st.radio("Fokus på banehalvdel:", ["Offensiv", "Defensiv"], horizontal=True)

    except KeyError as e:
        st.error(f"Kolonne-fejl: {e}. Tjek din df_matches struktur.")
        st.stop()

    # --- 4. PLOTTING LOGIK ---
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid].copy()

    if not df_hold_ev.empty:
        # Vi bruger 'opta' pitch_type (0-100 koordinater)
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#fdfdfd', line_color='#333')
        c1, c2, c3 = st.columns(3)
        
        # --- Rigtig Spejlings-logik ---
        if halvdel == "Offensiv":
            # Vis aktioner på modstanderens halvdel (X > 50)
            df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
        else:
            # Vis aktioner på egen halvdel (X < 50)
            df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
            # Spejl KUN X-aksen så deres eget felt kommer i toppen af billedet.
            # Vi rører IKKE Y, så venstre side forbliver venstre side.
            df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']

        config = [
            (c1, "Afleveringer", "pass", "Reds"),
            (c2, "Dueller", "duel", "Blues"),
            (c3, "Erobringer", "interception", "Greens")
        ]

        for col, title, p_type, cmap in config:
            with col:
                st.write(f"**{title}**")
                fig, ax = pitch.draw(figsize=(4, 5))
                df_f = df_plot[df_plot['PRIMARYTYPE'] == p_type]
                
                if not df_f.empty:
                    # Clip og Thresh sikrer at farverne holder sig inden for kridtstregerne
                    sns.kdeplot(
                        x=df_f['LOCATIONY'], 
                        y=df_f['LOCATIONX'], 
                        ax=ax, 
                        fill=True, 
                        cmap=cmap, 
                        alpha=0.7, 
                        levels=10, 
                        thresh=0.05, 
                        clip=((0, 100), (50, 100))
                    )
                    # Tvinger akserne til halvbanen så plottet ikke "skrider"
                    ax.set_xlim(0, 100)
                    ax.set_ylim(50, 100)
                else:
                    ax.text(50, 75, "Ingen data", ha='center', color='gray')
                    
                st.pyplot(fig)
    else:
        st.warning(f"Ingen Opta-events fundet for {valgt_hold_navn} i de indlæste data.")

    # --- 5. STATS SECTION (Valgfrit) ---
    st.divider()
    # Her kan du tilføje dine metrics (m1, m2, m3, m4) som før
