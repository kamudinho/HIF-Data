import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Denne SQL er ombygget til at aggregere Qualifiers INDEN de rammer Events
    # Det forhindrer de eksplosive tal (som 10.000+ aktioner)
    sql = f"""
        WITH QUAL_SUMMARY AS (
            SELECT 
                EVENT_OPTAUUID,
                MAX(CASE WHEN QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
                MAX(CASE WHEN QUALIFIER_QID IN (2, 6) THEN 1 ELSE 0 END) as IS_CORNER,
                MAX(CASE WHEN QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
                MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as ENDX,
                MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as ENDY,
                MAX(CASE WHEN QUALIFIER_QID IN (210, 154) THEN 1 ELSE 0 END) as IS_CHANCE
            FROM {DB}.OPTA_QUALIFIERS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_X,
            e.EVENT_Y,
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.PLAYER_OPTAUUID,
            e.MATCH_OPTAUUID,
            q.IS_THROW_IN,
            q.IS_CORNER,
            q.IS_FREEKICK,
            q.ENDX,
            q.ENDY,
            q.IS_CHANCE,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN QUAL_SUMMARY q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_TYPEID IN (1, 15, 16) -- Kun afleveringer og dødbolde
        AND (q.IS_THROW_IN = 1 OR q.IS_CORNER = 1 OR q.IS_FREEKICK = 1)
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Definer typerne én gang for alle
    def get_type(row):
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        if row['IS_THROW_IN'] == 1: return "Indkast"
        return "Frispark"
    
    df['SET_PIECE_TYPE'] = df.apply(get_type, axis=1)
    return df

def vis_side():
    st.title("Standardsituationer - Korrigeret Statistik")
    df_all = load_setpiece_data()
    
    if df_all.empty:
        st.error("Ingen data fundet.")
        return

    # Holdmapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    hold_navne = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    t_sel = st.selectbox("Vælg Hold", hold_navne, index=hold_navne.index("Hvidovre") if "Hvidovre" in hold_navne else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    # --- Statistik Beregning ---
    # Vi grupperer på spillernavn og tæller de UNIKKE hændelser
    stats_data = []
    for player, p_df in df_team.groupby('PLAYER_NAME'):
        total_actions = len(p_df)
        
        # Succeslogik
        # Hjørne/Frispark: Succes hvis IS_CHANCE == 1
        # Indkast: Succes hvis EVENT_OUTCOME == 1
        corners = p_df[p_df['SET_PIECE_TYPE'] == "Hjørnespark"]
        throws = p_df[p_df['SET_PIECE_TYPE'] == "Indkast"]
        frees = p_df[p_df['SET_PIECE_TYPE'] == "Frispark"]
        
        c_succes = corners['IS_CHANCE'].sum()
        t_succes = throws[throws['EVENT_OUTCOME'] == 1].shape[0]
        f_succes = frees['IS_CHANCE'].sum()
        
        total_succes = c_succes + t_succes + f_succes
        
        stats_data.append({
            'Navn': player,
            'Total Aktioner': total_actions,
            'Total Succes %': (total_succes / total_actions * 100) if total_actions > 0 else 0,
            'Hjørnespark (Antal)': len(corners),
            'Hjørnespark (%)': (c_succes / len(corners) * 100) if len(corners) > 0 else 0,
            'Indkast (Antal)': len(throws),
            'Indkast (%)': (t_succes / len(throws) * 100) if len(throws) > 0 else 0,
            'Frispark (Antal)': len(frees),
            'Frispark (%)': (f_succes / len(frees) * 100) if len(frees) > 0 else 0
        })

    df_final = pd.DataFrame(stats_data).sort_values("Total Aktioner", ascending=False)
    
    # Visning
    st.subheader(f"Overblik: {t_sel}")
    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Total Succes %": st.column_config.NumberColumn(format="%.1f%%"),
            "Hjørnespark (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Indkast (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Frispark (%)": st.column_config.NumberColumn(format="%.1f%%")
        }
    )

    # Plot (hvis man vil se de specifikke pile)
    st.divider()
    type_choice = st.radio("Se placeringer for:", ["Hjørnespark", "Indkast", "Frispark"], horizontal=True)
    df_plot = df_team[df_team['SET_PIECE_TYPE'] == type_choice]
    
    pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
    fig, ax = pitch.draw(figsize=(8, 10))
    if not df_plot.empty:
        pitch.arrows(df_plot.EVENT_X * 1.05, df_plot.EVENT_Y * 0.68, 
                     df_plot.ENDX * 1.05, df_plot.ENDY * 0.68, 
                     color="#cc0000", ax=ax, width=2, alpha=0.3)
    st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
