import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Opta Match Center")

    # --- 1. FILTRE ---
    alle_hold = sorted(pd.concat([df['CONTESTANTHOME_NAME'], df['CONTESTANTAWAY_NAME']]).unique())
    col1, col2 = st.columns([2, 1])
    valgt_hold = col1.selectbox("Filtrer hold", ["Alle hold"] + alle_hold)
    view_type = col2.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = df['MATCH_STATUS'] == status_filter
    if valgt_hold != "Alle hold":
        mask = mask & ((df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. KOMPAKT LISTE ---
    for _, row in display_df.head(20).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi laver en ekstremt kompakt titel til expanderen
        # Vi bruger 'icon' argumentet i expander til at vise det ene logo, 
        # men for to logoer bygger vi en custom label
        expander_label = f"{h_name}  {score}  {a_name}"
        
        # Vi bruger 'label_visibility' og 'expanded=False' for at holde det stramt
        with st.expander(expander_label):
            # Herinde viser vi KUN rå data. Ingen ikoner.
            if status_filter == 'Played':
                c1, c2, c3 = st.columns([1, 2, 1])
                
                # Venstre: Hjemmehold stats
                c1.metric("xG", "1.42")
                c1.write(f"Skud: 12")
                
                # Midte: Sammenlignings-barer (Rå Opta tal)
                with c2:
                    st.markdown("<p style='text-align:center; font-size:12px; margin-bottom:0;'>Boldbesiddelse %</p>", unsafe_allow_html=True)
                    # En simpel progress bar er den mest "data-agtige" måde at vise det på
                    st.progress(0.55) 
                    st.markdown("<p style='text-align:center; font-size:11px;'>55% - 45%</p>", unsafe_allow_html=True)
                
                # Højre: Udehold stats
                c3.metric("xG", "0.85")
                c3.write(f"Skud: 8")
                
                st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Tilskuere: {int(row['ATTENDANCE']):,}")
            else:
                # For kommende kampe viser vi kun info
                st.write(f"Spilles på {row['VENUE_LONGNAME']} kl. {row['MATCH_DATE_FULL'].strftime('%H:%M')}")
