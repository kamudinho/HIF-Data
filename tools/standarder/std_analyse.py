import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

# Konfiguration
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"
HVIDOVRE_UUID = "67p88id0unq39f688on9atnsh" 

@st.cache_data(ttl=3600)
def load_standards_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = f"""
    SELECT 
        e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
        e.EVENT_OPTAUUID,
        e.EVENT_OUTCOME,
        e.PLAYER_NAME,
        MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
        MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
        MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
        MAX(CASE WHEN q.QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST,
        -- Sikrer at xG bliver læst korrekt som et tal
        MAX(CASE WHEN q.QUALIFIER_QID = 142 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE 0 END) as XG
    FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS e
    INNER JOIN KLUB_HVIDOVREIF.AXIS.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
      AND q.QUALIFIER_QID IN (6, 107, 5, 26)
    GROUP BY 1, 2, 3, 4
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_stats(df):
    stats_list = []
    for player, p_df in df.groupby('PLAYER_NAME'):
        def get_metrics(sub):
            a = len(sub)
            s = int(sub['EVENT_OUTCOME'].sum()) if a > 0 else 0
            ast = int(sub['IS_ASSIST'].sum()) if a > 0 else 0
            xg_val = sub['XG'].sum() if a > 0 else 0
            pct = (s / a * 100) if a > 0 else 0
            return f"{a} / {s}", pct, ast, xg_val, a, s

        c_as, c_pct, c_ast, c_xg, c_a, c_s = get_metrics(p_df[p_df['IS_CORNER'] == 1])
        i_as, i_pct, i_ast, i_xg, i_a, i_s = get_metrics(p_df[p_df['IS_THROW_IN'] == 1])
        f_as, f_pct, f_ast, f_xg, f_a, f_s = get_metrics(p_df[p_df['IS_FREEKICK'] == 1])
        
        total_xg = p_df['XG'].sum()
        total_assists = p_df['IS_ASSIST'].sum()
        
        stats_list.append({
            'Navn': player,
            'Total': len(p_df),
            'Total xG': total_xg,
            'Total Assists': total_assists,
            'Hjørne (A/S)': c_as, 'Hjørne %': c_pct, 'Hjørne Ast': c_ast, 'Hjørne xG': c_xg,
            'Indkast (A/S)': i_as, 'Indkast %': i_pct, 'Indkast Ast': i_ast, 'Indkast xG': i_xg,
            'Frispark (A/S)': f_as, 'Frispark %': f_pct, 'Frispark Ast': f_ast, 'Frispark xG': f_xg,
            'h_a': c_a, 'h_s': c_s, 'h_ast': c_ast, 'h_xg': c_xg,
            'i_a': i_a, 'i_s': i_s, 'i_ast': i_ast, 'i_xg': i_xg,
            'f_a': f_a, 'f_s': f_s, 'f_ast': f_ast, 'f_xg': f_xg
        })
    return pd.DataFrame(stats_list).sort_values("Total", ascending=False)

def vis_side():
    st.set_page_config(layout="wide")
    st.title("🎯 Standardsituationer - Inkl. Assists & xG")
    
    df_raw = load_standards_data()
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    team_list = sorted(df_raw['TEAM_UUID'].unique())
    selected_team = st.sidebar.selectbox("Vælg Hold", team_list, 
                                         index=team_list.index(HVIDOVRE_UUID) if HVIDOVRE_UUID in team_list else 0)

    df_filtered = df_raw[df_raw['TEAM_UUID'] == selected_team]
    df_stats = generate_stats(df_filtered)

    tab_hold, tab_total, tab_hjorne, tab_indkast, tab_frispark = st.tabs([
        "🏠 Holdoversigt", "📊 Alle Spillere", "🚩 Hjørnespark", "👐 Indkast", "🎯 Frispark"
    ])

    with tab_hold:
        st.subheader("Samlet holdstatistik")
        team_summary = pd.DataFrame([
            {
                'Type': '🚩 Hjørne', 
                'Antal / Succes': f"{df_stats['h_a'].sum()} / {df_stats['h_s'].sum()}", 
                'Assists': int(df_stats['h_ast'].sum()), 
                'xG Skabt': df_stats['h_xg'].sum(),
                'Succes %': (df_stats['h_s'].sum()/df_stats['h_a'].sum()*100) if df_stats['h_a'].sum() > 0 else 0
            },
            {
                'Type': '👐 Indkast', 
                'Antal / Succes': f"{df_stats['i_a'].sum()} / {df_stats['i_s'].sum()}", 
                'Assists': int(df_stats['i_ast'].sum()), 
                'xG Skabt': df_stats['i_xg'].sum(),
                'Succes %': (df_stats['i_s'].sum()/df_stats['i_a'].sum()*100) if df_stats['i_a'].sum() > 0 else 0
            },
            {
                'Type': '🎯 Frispark', 
                'Antal / Succes': f"{df_stats['f_a'].sum()} / {df_stats['f_s'].sum()}", 
                'Assists': int(df_stats['f_ast'].sum()), 
                'xG Skabt': df_stats['f_xg'].sum(),
                'Succes %': (df_stats['f_s'].sum()/df_stats['f_a'].sum()*100) if df_stats['f_a'].sum() > 0 else 0
            }
        ])
        st.dataframe(team_summary, use_container_width=True, hide_index=True,
                     column_config={
                         "Succes %": st.column_config.NumberColumn(format="%.1f%%"),
                         "xG Skabt": st.column_config.NumberColumn(format="%.3f")
                     })

    with tab_total:
        # Her har jeg tilføjet de nye kolonner til oversigten
        display_cols = ['Navn', 'Total', 'Total Assists', 'Total xG', 'Hjørne Ast', 'Indkast Ast', 'Frispark Ast']
        st.dataframe(df_stats[display_cols], use_container_width=True, hide_index=True,
                     column_config={
                         "Total xG": st.column_config.NumberColumn(format="%.3f")
                     })

    with tab_hjorne:
        st.dataframe(df_stats[df_stats['h_a'] > 0][['Navn', 'Hjørne (A/S)', 'Hjørne %', 'Hjørne Ast', 'Hjørne xG']].sort_values('Hjørne Ast', ascending=False), 
                     use_container_width=True, hide_index=True, 
                     column_config={"Hjørne %": st.column_config.NumberColumn(format="%.1f%%"), "Hjørne xG": st.column_config.NumberColumn(format="%.3f")})

    with tab_indkast:
        st.dataframe(df_stats[df_stats['i_a'] > 0][['Navn', 'Indkast (A/S)', 'Indkast %', 'Indkast Ast', 'Indkast xG']].sort_values('Indkast Ast', ascending=False), 
                     use_container_width=True, hide_index=True,
                     column_config={"Indkast %": st.column_config.NumberColumn(format="%.1f%%"), "Indkast xG": st.column_config.NumberColumn(format="%.3f")})

    with tab_frispark:
        st.dataframe(df_stats[df_stats['f_a'] > 0][['Navn', 'Frispark (A/S)', 'Frispark %', 'Frispark Ast', 'Frispark xG']].sort_values('Frispark Ast', ascending=False), 
                     use_container_width=True, hide_index=True,
                     column_config={"Frispark %": st.column_config.NumberColumn(format="%.1f%%"), "Frispark xG": st.column_config.NumberColumn(format="%.3f")})

if __name__ == "__main__":
    vis_side()
