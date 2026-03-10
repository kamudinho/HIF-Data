import streamlit as st
import pandas as pd
import seaborn as sns
from mplsoccer import VerticalPitch

def vis_side(analysis_package):
    # --- 1. Hent data fra pakken ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    
    # Hent events fra session_state (eller load dem hvis de mangler)
    if "events_data" not in st.session_state:
        from data.data_load import _get_snowflake_conn
        from data.sql.opta_queries import get_opta_queries
        
        conn = _get_snowflake_conn()
        # Sørg for at config-nøglerne matcher din analyse_load.py
        liga = analysis_package.get("config", {}).get("liga_navn", "")
        saeson = analysis_package.get("config", {}).get("season", "")
        
        q = get_opta_queries(liga, saeson)
        st.session_state["events_data"] = pd.DataFrame(conn.query(q["opta_events"]))

    df_events = st.session_state["events_data"]

    # --- 2. Branding & Layout ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"

    st.markdown(f"""
        <div style="background-color:{HIF_ROD}; padding:10px; border-radius:5px; border-left:8px solid {HIF_GOLD}; margin-bottom:20px;">
            <h3 style="color:white; margin:0; text-transform:uppercase;">Modstanderanalyse: Opta Engine</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. Filtrering af Modstander ---
    try:
        # Vi samler unikke hold fra df_matches
        hold_df = pd.concat([
            df_matches[['HOMECONTESTANT_NAME', 'HOMECONTESTANT_OPTAUUID']].rename(
                columns={'HOMECONTESTANT_NAME': 'NAVN', 'HOMECONTESTANT_OPTAUUID': 'UUID'}
            ),
            df_matches[['AWAYCONTESTANT_NAME', 'AWAYCONTESTANT_OPTAUUID']].rename(
                columns={'AWAYCONTESTANT_NAME': 'NAVN', 'AWAYCONTESTANT_OPTAUUID': 'UUID'}
            )
        ]).drop_duplicates().sort_values('NAVN')

        col_sel, col_halv = st.columns([2, 1])
        with col_sel:
            valgt_hold_navn = st.selectbox("Vælg Modstander:", hold_df['NAVN'].unique())
            valgt_uuid = hold_df[hold_df['NAVN'] == valgt_hold_navn]['UUID'].iloc[0]
        with col_halv:
            halvdel = st.radio("Fokus:", ["Offensiv", "Defensiv"], horizontal=True)

    except KeyError as e:
        st.error(f"Kolonne-fejl: {e}. Tjek om df_matches indeholder de korrekte Opta-kolonner.")
        st.write("Fundne kolonner i df_matches:", df_matches.columns.tolist())
        return # Stop funktionen her hvis der er fejl

    # --- 4. Plotting ---
    # Vi filtrerer hændelser baseret på den valgte UUID
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid].copy()

    if not df_hold_ev.empty:
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#fdfdfd', line_color='#333')
        c1, c2, c3 = st.columns(3)
        
        # Logik for banehalvdel
        if halvdel == "Offensiv":
            df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50]
        else:
            df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
            # Ved defensivt fokus vender vi banen for at se deres forsvarsaktioner øverst
            df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
            df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

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
                    sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, 
                                fill=True, cmap=cmap, alpha=0.7, levels=8, thresh=0.1)
                else:
                    ax.text(50, 75, "Ingen data", ha='center', color='gray')
                st.pyplot(fig)
    else:
        st.warning(f"Ingen Opta-events fundet for {valgt_hold_navn} i de indlæste data.")
