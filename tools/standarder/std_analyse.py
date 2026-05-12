import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

# Konfiguration
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_pure_standards():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID,
        e.EVENT_OUTCOME,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
        MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
        MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
        MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    AND q.QUALIFIER_QID IN (6, 107, 5, 26)
    GROUP BY 1, 2, 3
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_full_stats(df):
    stats = []
    for player, p_df in df.groupby('PLAYER_NAME'):
        def get_m(sub_df):
            a = len(sub_df)
            s = int(sub_df['EVENT_OUTCOME'].sum()) if a > 0 else 0
            pct = (s / a * 100) if a > 0 else 0
            return a, s, pct

        h_a, h_s, h_p = get_m(p_df[p_df['IS_CORNER'] == 1])
        i_a, i_s, i_p = get_m(p_df[p_df['IS_THROW_IN'] == 1])
        f_a, f_s, f_p = get_m(p_df[p_df['IS_FREEKICK'] == 1])
        
        stats.append({
            'Navn': player,
            'Total': len(p_df),
            'Hjørne (A/S)': f"{h_a} / {h_s}", 'Hjørne %': h_p,
            'Indkast (A/S)': f"{i_a} / {i_s}", 'Indkast %': i_p,
            'Frispark (A/S)': f"{f_a} / {f_s}", 'Frispark %': f_p,
            # Rå tal til holdberegning
            'h_a': h_a, 'h_s': h_s, 'i_a': i_a, 'i_s': i_s, 'f_a': f_a, 'f_s': f_s
        })
    return pd.DataFrame(stats).sort_values("Total", ascending=False)

def vis_side():
    st.title("🎯 Standardsituationer - Hvidovre IF")
    
    df_raw = load_pure_standards()
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_stats = generate_full_stats(df_raw)

    # Tabs inklusiv ny Holdoversigt
    tab_hold, tab_total, tab_hjorne, tab_indkast, tab_frispark = st.tabs([
        "🏠 Holdoversigt", "📊 Spillere (Samlet)", "🚩 Hjørnespark", "👐 Indkast", "🎯 Frispark"
    ])

    with tab_hold:
        st.subheader("Samlet holdstatistik")
        # Beregn totaler for hele holdet
        t_h_a = df_stats['h_a'].sum()
        t_h_s = df_stats['h_s'].sum()
        t_i_a = df_stats['i_a'].sum()
        t_i_s = df_stats['i_s'].sum()
        t_f_a = df_stats['f_a'].sum()
        t_f_s = df_stats['f_s'].sum()
        
        team_data = [{
            'Kategori': '🚩 Hjørnespark',
            'Antal / Succes': f"{t_h_a} / {t_h_s}",
            'Succes %': (t_h_s / t_h_a * 100) if t_h_a > 0 else 0
        }, {
            'Kategori': '👐 Indkast',
            'Antal / Succes': f"{t_i_a} / {t_i_s}",
            'Succes %': (t_i_s / t_i_a * 100) if t_i_a > 0 else 0
        }, {
            'Kategori': '🎯 Frispark',
            'Antal / Succes': f"{t_f_a} / {t_f_s}",
            'Succes %': (t_f_s / t_f_a * 100) if t_f_a > 0 else 0
        }]
        
        st.dataframe(pd.DataFrame(team_data), use_container_width=True, hide_index=True,
                     column_config={"Succes %": st.column_config.NumberColumn(format="%.1f%%")})
        
        st.metric("Total antal standardsituationer", df_stats['Total'].sum())

    with tab_total:
        # Viser kun de relevante kolonner til brugeren
        display_cols = ['Navn', 'Total', 'Hjørne (A/S)', 'Hjørne %', 'Indkast (A/S)', 'Indkast %', 'Frispark (A/S)', 'Frispark %']
        st.dataframe(df_stats[display_cols], use_container_width=True, hide_index=True,
                     column_config={
                         "Hjørne %": st.column_config.NumberColumn(format="%.1f%%"),
                         "Indkast %": st.column_config.NumberColumn(format="%.1f%%"),
                         "Frispark %": st.column_config.NumberColumn(format="%.1f%%")
                     })

    # (Resten af tabs som før...)
    with tab_hjorne:
        st.subheader("Specialister: Hjørnespark")
        h_df = df_stats[df_stats['h_a'] > 0][['Navn', 'Hjørne (A/S)', 'Hjørne %']].sort_values('Hjørne %', ascending=False)
        st.dataframe(h_df, use_container_width=True, hide_index=True, column_config={"Hjørne %": st.column_config.NumberColumn(format="%.1f%%")})

    with tab_indkast:
        st.subheader("Specialister: Indkast")
        i_df = df_stats[df_stats['i_a'] > 0][['Navn', 'Indkast (A/S)', 'Indkast %']].sort_values('Indkast %', ascending=False)
        st.dataframe(i_df, use_container_width=True, hide_index=True, column_config={"Indkast %": st.column_config.NumberColumn(format="%.1f%%")})

    with tab_frispark:
        st.subheader("Specialister: Frispark")
        f_df = df_stats[df_stats['f_a'] > 0][['Navn', 'Frispark (A/S)', 'Frispark %']].sort_values('Frispark %', ascending=False)
        st.dataframe(f_df, use_container_width=True, hide_index=True, column_config={"Frispark %": st.column_config.NumberColumn(format="%.1f%%")})

if __name__ == "__main__":
    vis_side()
