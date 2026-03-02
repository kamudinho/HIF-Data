import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Opta Match Center")

    # --- 1. FILTRE (Kompakte) ---
    alle_hold = sorted(pd.concat([df['CONTESTANTHOME_NAME'], df['CONTESTANTAWAY_NAME']]).unique())
    
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        valgt_hold = st.selectbox("🎯 Filtrer på hold", ["Alle hold"] + alle_hold)
    with col_sel2:
        view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = df['MATCH_STATUS'] == status_filter
    if valgt_hold != "Alle hold":
        mask = mask & ((df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. KOMPAKT LISTE-VISNING ---
    for _, row in display_df.head(20).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        h_logo = logos.get(h_name, "")
        a_logo = logos.get(a_name, "")
        
        # Vi bygger overskriften på expanderen (Den "lukkede" bar)
        score_display = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        dato = row['MATCH_DATE_FULL'].strftime('%d/%m')
        
        # Selve expander-titlen skal være kort og præcis
        label = f"{dato} | {h_name} {score_display} {a_name}"
        
        with st.expander(label):
            # --- DETTE VISES NÅR DEN ÅBNES ---
            st.caption(f"🏟️ {row['VENUE_LONGNAME']} | 📅 {row['MATCH_DATE_FULL'].strftime('%H:%M - %d. %B %Y')}")
            
            c1, c2, c3 = st.columns([2, 1, 2])
            
            # Hjemmehold
            with c1:
                if h_logo: st.image(h_logo, width=40)
                st.subheader(h_name)
            
            # Score/Info i midten
            with c2:
                st.markdown(f"<h1 style='text-align:center;'>{score_display}</h1>", unsafe_allow_html=True)
                if row['ATTENDANCE'] > 0:
                    st.write(f"<p style='text-align:center; font-size:12px;'>👥 {int(row['ATTENDANCE']):,}</p>", unsafe_allow_html=True)

            # Udehold
            with c3:
                if a_logo: st.image(a_logo, width=40)
                st.subheader(a_name)

            # --- OPTA STATS BARER ---
            if status_filter == 'Played':
                st.divider()
                st.markdown("#### 📊 Kampstatistik (Opta)")
                
                # Eksempel: Boldbesiddelse
                st.write("**Boldbesiddelse %**")
                # Her indsætter vi rigtige Opta-stats senere
                st.progress(0.55, text=f"{h_name} 55% - 45% {a_name}")
                
                # Eksempel: xG Metrics
                col_xg1, col_xg2 = st.columns(2)
                col_xg1.metric("xG (Expected Goals)", "1.84", delta="Hjemme")
                col_xg2.metric("xG (Expected Goals)", "0.92", delta="Ude", delta_color="inverse")
