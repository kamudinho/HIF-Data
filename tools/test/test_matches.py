import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Opta Match Center")

    # --- 1. HOLD-VÆLGER (DROPDOWN) ---
    # Vi henter alle unikke holdnavne fra både ude- og hjemmebane
    alle_hold = sorted(pd.concat([df['CONTESTANTHOME_NAME'], df['CONTESTANTAWAY_NAME']]).unique())
    
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        # Vi sætter Hvidovre som standard, hvis de findes i listen
        default_ix = alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0
        valgt_hold = st.selectbox("🎯 Vælg hold for at se kampe", ["Alle hold"] + alle_hold, index=default_ix + 1 if "Hvidovre" in alle_hold else 0)

    with col_sel2:
        view_type = st.radio("Status", ["Spillede", "Kommende"], horizontal=True)

    # --- 2. FILTRERING ---
    # Først på status (Played vs Fixture)
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = df['MATCH_STATUS'] == status_filter
    
    # Derefter på det valgte hold fra dropdown
    if valgt_hold != "Alle hold":
        mask = mask & ((df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING AF KORT ---
    if display_df.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet for {valgt_hold}.")
        return

    for _, row in display_df.head(15).iterrows():
        with st.container(border=True):
            st.caption(f"📅 {row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} | 🏟️ {row['VENUE_LONGNAME']}")
            
            c1, c2, c3 = st.columns([2, 1, 2])
            
            # Hjemmehold
            h_name = row['CONTESTANTHOME_NAME']
            h_logo = logos.get(h_name, "")
            c1.image(h_logo, width=50) if h_logo else c1.write("⚽")
            # Highlight hvis det er det valgte hold
            h_label = f":red[{h_name}]" if h_name == valgt_hold else h_name
            c1.subheader(h_label)

            # Score / VS
            if row['MATCH_STATUS'] == 'Played':
                score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
                c2.markdown(f"<h2 style='text-align:center; background:#1e1e1e; color:white; border-radius:10px;'>{score}</h2>", unsafe_allow_html=True)
            else:
                c2.markdown("<h2 style='text-align:center; padding-top:10px;'>VS</h2>", unsafe_allow_html=True)

            # Udehold
            a_name = row['CONTESTANTAWAY_NAME']
            a_logo = logos.get(a_name, "")
            c3.image(a_logo, width=50) if a_logo else c3.write("⚽")
            a_label = f":red[{a_name}]" if a_name == valgt_hold else a_name
            c3.subheader(a_label)

            # --- DATA EXPANDER ---
            if row['MATCH_STATUS'] == 'Played':
                with st.expander("📊 Se Opta Kamp-data"):
                    st.write("**Statistik for kampen**")
                    # Her kan vi indsætte xG og Possession bars senere
                    st.progress(0.5, text="Boldbesiddelse (Simuleret 50/50)")
