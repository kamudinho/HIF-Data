import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(data_package):
    st.subheader("KAMPOVERSIGT")
    
    # Hent de nødvendige data fra pakken
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    try:
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]

        # --- 1. TOGGLE: SPILLEDE VS KOMMENDE ---
        col_nav1, col_nav2 = st.columns([2, 2])
        with col_nav1:
            visning = st.radio("Vis:", ["Spillede kampe", "Kommende kampe"], horizontal=True)

        # --- 2. DATO FILTRERING ---
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            nu = datetime.now()
            if visning == "Spillede kampe":
                df = df[df[dato_col] <= nu].sort_values(by=dato_col, ascending=False)
            else:
                df = df[df[dato_col] > nu].sort_values(by=dato_col, ascending=True)

        # --- 3. HOLD-VÆLGER ---
        liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        with col_nav2:
            hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)
            valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index)

        if valgt_hold != "Alle hold":
            df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()

        # --- 4. KLARGØR TABEL-VISNING ---
        df['KAMP'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
        
        def get_score(row):
            if visning == "Kommende kampe": return "-"
            h = row.get('TOTAL_HOME_SCORE', 0)
            a = row.get('TOTAL_AWAY_SCORE', 0)
            return f"{int(h)} - {int(a)}"

        df['MÅL'] = df.apply(get_score, axis=1)
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y')

        final_table = df[['DATO_STR', 'KAMP', 'MÅL']].copy()
        final_table.columns = ['Dato', 'Kamp', 'Mål']

        st.dataframe(final_table, use_container_width=True, hide_index=True, height=400)

        # --- 5. DYB STATISTIK (DYNAMISK) ---
        if visning == "Spillede kampe" and not df.empty and df_stats is not None:
            st.markdown("---")
            st.write("### 📊 Kampstatistik (Opta Data)")
            
            # Vælg kamp fra den filtrerede liste
            valgt_label = st.selectbox("Vælg kamp for detaljer:", df['KAMP'].tolist())
            valgt_row = df[df['KAMP'] == valgt_label].iloc[0]
            m_uuid = valgt_row['MATCH_OPTAUUID']
            
            # Filtrér stats for denne specifikke kamp
            m_stats = df_stats[df_stats['MATCH_OPTAUUID'] == m_uuid].copy()
            
            if not m_stats.empty:
                home_uuid = valgt_row['CONTESTANTHOME_OPTAUUID']
                away_uuid = valgt_row['CONTESTANTAWAY_OPTAUUID']
                
                # Hjælpefunktion til at hente stat dynamisk
                def get_s(s_type, team_id):
                    res = m_stats[(m_stats['STAT_TYPE'] == s_type) & (m_stats['CONTESTANT_OPTAUUID'] == team_id)]
                    return res['STAT_TOTAL'].values[0] if not res.empty else 0

                # Vis udvalgte stats i kolonner
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.write(f"**Possession**")
                    st.write(f"{get_s('possessionPercentage', home_uuid)}% - {get_s('possessionPercentage', away_uuid)}%")
                with s2:
                    st.write(f"**Skud (Target)**")
                    st.write(f"{get_s('totalScoringAtt', home_uuid)}({get_s('ontargetScoringAtt', home_uuid)}) - {get_s('totalScoringAtt', away_uuid)}({get_s('ontargetScoringAtt', away_uuid)})")
                with s3:
                    st.write(f"**Hjørnespark**")
                    st.write(f"{get_s('wonCorners', home_uuid)} - {get_s('wonCorners', away_uuid)}")
            else:
                st.info("Ingen detaljeret statistik tilgængelig for denne kamp.")

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
