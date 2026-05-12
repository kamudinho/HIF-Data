import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

# Konfiguration
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"
HVIDOVRE_UUID = "67p88id0unq39f688on9atnsh" # Standard Opta UUID for Hvidovre

@st.cache_data(ttl=3600)
def load_pure_standards():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID,
        e.EVENT_OUTCOME,
        e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
        MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
        MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
        MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    AND q.QUALIFIER_QID IN (6, 107, 5, 26)
    GROUP BY 1, 2, 3, 4
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_full_stats(df):
    stats = []
    # Vi grupperer stadig pr. spiller
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
            'h_a': h_a, 'h_s': h_s, 'i_a': i_a, 'i_s': i_s, 'f_a': f_a, 'f_s': f_s
        })
    return pd.DataFrame(stats).sort_values("Total", ascending=False)

def vis_side():
    st.title("🎯 Standardsituationer")
    
    df_raw = load_pure_standards()
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    # --- SIDEBAR FILTRERING ---
    st.sidebar.header("Filter")
    team_list = sorted(df_raw['TEAM_UUID'].unique())
    
    # Forsøg at sætte Hvidovre som default hvis de findes i listen
    default_index = 0
    if HVIDOVRE_UUID in team_list:
        default_index = team_list.index(HVIDOVRE_UUID)
        
    selected_team = st.sidebar.selectbox("Vælg Hold (Opta ID)", team_list, index=default_index)

    # Filtrér data baseret på valg
    df_filtered = df_raw[df_raw['TEAM_UUID'] == selected_team]
    df_stats = generate_full_stats(df_filtered)

    # --- TABS ---
    tab_hold, tab_total, tab_hjorne, tab_indkast, tab_frispark = st.tabs([
        "🏠 Holdoversigt", "📊 Spillere (Samlet)", "🚩 Hjørnespark", "👐 Indkast", "🎯 Frispark"
    ])

    with tab_hold:
        st.subheader(f"Holdstatistik for {selected_team}")
        t_h_a, t_h_s = df_stats['h_a'].sum(), df_stats['h_s'].sum()
        t_i_a, t_i_s = df_stats['i_a'].sum(), df_stats['i_s'].sum()
        t_f_a, t_f_s = df_stats['f_a'].sum(), df_stats['f_s'].sum()
        
        team_data = [
            {'Kategori': '🚩 Hjørnespark', 'Antal / Succes': f"{t_h_a} / {t_h_s}", 'Succes %': (t_h_s/t_h_a*100) if t_h_a > 0 else 0},
            {'Kategori': '👐 Indkast', 'Antal / Succes': f"{t_i_a} / {t_i_s}", 'Succes %': (t_i_s/t_i_a*100) if t_i_a > 0 else 0},
            {'Kategori': '🎯 Frispark', 'Antal / Succes': f"{t_f_a} / {t_f_s}", 'Succes %': (t_f_s/t_f_a*100) if t_f_a > 0 else 0}
        ]
        st.dataframe(pd.DataFrame(team_data), use_container_width=True, hide_index=True,
                     column_config={"Succes %": st.column_config.NumberColumn(format="%.1f%%")})
        st.metric("Total antal hændelser (valgt hold)", df_stats['Total'].sum())

    with tab_total:
        display_cols = ['Navn', 'Total', 'Hjørne (A/S)', 'Hjørne %', 'Indkast (A/S)', 'Indkast %', 'Frispark (A/S)', 'Frispark %']
        st.dataframe(df_stats[display_cols], use_container_width=True, hide_index=True,
                     column_config={
                         "Hjørne %": st.column_config.NumberColumn(format="%.1f%%"),
                         "Indkast %": st.column_config.NumberColumn(format="%.1f%%"),
                         "Frispark %": st.column_config.NumberColumn(format="%.1f%%")
                     })

    # Specifikke tabs (sorteret efter succes %)
    with tab_hjorne:
        st.dataframe(df_stats[df_stats['h_a'] > 0][['Navn', 'Hjørne (A/S)', 'Hjørne %']].sort_values('Hjørne %', ascending=False), 
                     use_container_width=True, hide_index=True, column_config={"Hjørne %": st.column_config.NumberColumn(format="%.1f%%")})

    with tab_indkast:
        st.dataframe(df_stats[df_stats['i_a'] > 0][['Navn', 'Indkast (A/S)', 'Indkast %']].sort_values('Indkast %', ascending=False), 
                     use_container_width=True, hide_index=True, column_config={"Indkast %": st.column_config.NumberColumn(format="%.1f%%")})

    with tab_frispark:
        st.dataframe(df_stats[df_stats['f_a'] > 0][['Navn', 'Frispark (A/S)', 'Frispark %']].sort_values('Frispark %', ascending=False), 
                     use_container_width=True, hide_index=True, column_config={"Frispark %": st.column_config.NumberColumn(format="%.1f%%")})

if __name__ == "__main__":
    vis_side()
