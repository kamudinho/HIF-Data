import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(dp):
    st.subheader("KAMPOVERSIGT")
    
    # 1. HENT DATA FRA PAKKEN
    df = dp.get("opta_matches", pd.DataFrame()).copy()
    df_stats = dp.get("opta_stats", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampdata fundet i systemet.")
        return

    try:
        # --- KONFIGURATION OG FILTRERING ---
        df.columns = [c.upper() for c in df.columns]
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        
        col_nav1, col_nav2 = st.columns([2, 2])
        with col_nav1:
            visning = st.radio("Visning:", ["Spillede kampe", "Kommende kampe"], horizontal=True)

        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            nu = datetime.now()
            df = df[df[dato_col] <= nu] if visning == "Spillede kampe" else df[df[dato_col] > nu]
            df = df.sort_values(by=dato_col, ascending=(visning == "Kommende kampe"))

        # --- TABEL VISNING ---
        df['KAMP'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
        df['RESULTAT'] = df.apply(lambda r: f"{int(r['TOTAL_HOME_SCORE'])} - {int(r['TOTAL_AWAY_SCORE'])}" if visning == "Spillede kampe" else "-", axis=1)
        df['DATO'] = df[dato_col].dt.strftime('%d-%m-%Y')

        st.dataframe(df[['DATO', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

        # --- DYNAMISK MATCH REPORT (KUN FOR SPILLEDE KAMPE) ---
        if visning == "Spillede kampe" and not df.empty:
            st.markdown("---")
            valgt_label = st.selectbox("Vælg en kamp for dyb statistik:", df['KAMP'].tolist())
            match_info = df[df['KAMP'] == valgt_label].iloc[0]
            m_uuid = match_info['MATCH_OPTAUUID']
            
            # Find stats for denne kamp
            m_stats = df_stats[df_stats['MATCH_OPTAUUID'] == m_uuid].copy()
            
            if not m_stats.empty:
                h_id = match_info['CONTESTANTHOME_OPTAUUID']
                a_id = match_info['CONTESTANTAWAY_OPTAUUID']
                h_navn = match_info['CONTESTANTHOME_NAME']
                a_navn = match_info['CONTESTANTAWAY_NAME']

                # Hjælpefunktion til at hente stats
                def get_v(stat_type, team_id, col='STAT_TOTAL'):
                    val = m_stats[(m_stats['STAT_TYPE'] == stat_type) & (m_stats['CONTESTANT_OPTAUUID'] == team_id)][col]
                    return val.values[0] if not val.empty else 0

                st.markdown(f"### 📊 Match Report: {h_navn} vs {a_navn}")
                
                # Formationer
                st.info(f"🏟️ **Formationer:** {h_navn}: {get_v('formationUsed', h_id)} | {a_navn}: {get_v('formationUsed', a_id)}")

                # Hoved-stats (Metric række)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Possession", f"{get_v('possessionPercentage', h_id)}%", f"{get_v('possessionPercentage', h_id) - 50}%", delta_color="normal")
                m2.metric("Skud (Target)", f"{get_v('totalScoringAtt', h_id)} ({get_v('ontargetScoringAtt', h_id)})")
                m3.metric("xG (Opta)", f"{get_v('expectedGoals', h_id) if 'expectedGoals' in m_stats['STAT_TYPE'].values else '-'}")
                m4.metric("Hjørnespark", f"{get_v('wonCorners', h_id)}")

                # Sammenligningstabel for detaljer
                stats_to_show = [
                    ('accuratePass', 'Præcise afleveringer'),
                    ('totalPass', 'Total afleveringer'),
                    ('totalTackle', 'Tacklinger'),
                    ('wonTackle', 'Vundne tacklinger'),
                    ('totalClearance', 'Clearinger'),
                    ('totalYellowCard', 'Gule kort'),
                    ('totalOffside', 'Offsides')
                ]
                
                compare_data = []
                for s_type, s_label in stats_to_show:
                    compare_data.append({
                        "Statistik": s_label,
                        h_navn: get_v(s_type, h_id),
                        a_navn: get_v(s_type, a_id)
                    })
                
                st.table(pd.DataFrame(compare_data))

                # Halvlegs-analyse (FH vs SH)
                with st.expander("Se udvikling (1. halvleg vs 2. halvleg)"):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Possession 1. HL:** {get_v('possessionPercentage', h_id, 'STAT_FH')}%")
                    c2.write(f"**Possession 2. HL:** {get_v('possessionPercentage', h_id, 'STAT_SH')}%")

            else:
                st.info("Der er ingen detaljeret statistik (Opta MatchStats) tilgængelig for denne kamp endnu.")

    except Exception as e:
        st.error(f"Fejl i generering af kampoversigt: {e}")
