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
        h_logo = logos.get(h_name)
        
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi bygger titlen: "Hjemmehold Score Udehold"
        # Vi bruger 'icon' til hjemmeholdets logo for at få det ind i baren
        expander_label = f"{h_name}  ({score})  {a_name}"
        
        with st.expander(expander_label, icon=h_logo):
            # KUN rå data herinde.
            if status_filter == 'Played':
                # Tre smalle kolonner til ren data-sammenligning
                c1, c2, c3 = st.columns([1, 1, 1])
                
                # Rækker med rå stats
                with c1:
                    st.write(f"**{h_name}**")
                    st.write(f"xG: 1.42")
                    st.write(f"Skud: 12")
                
                with c2:
                    st.write("<p style='text-align:center;'><b>VS</b></p>", unsafe_allow_html=True)
                    st.write(f"<p style='text-align:center; font-size:11px;'>Poss: 55% - 45%</p>", unsafe_allow_html=True)
                
                with c3:
                    st.write(f"<p style='text-align:right;'><b>{a_name}</b></p>", unsafe_allow_html=True)
                    st.write(f"<p style='text-align:right;'>xG: 0.85</p>", unsafe_allow_html=True)
                    st.write(f"<p style='text-align:right;'>Skud: 8</p>", unsafe_allow_html=True)
                
                st.divider()
                st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Tilskuere: {int(row['ATTENDANCE']):,}")
            else:
                st.write(f"🏟️ {row['VENUE_LONGNAME']} | 📅 {row['MATCH_DATE_FULL'].strftime('%d. %b - %H:%M')}")
