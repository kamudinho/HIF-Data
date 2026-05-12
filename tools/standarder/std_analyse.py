import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Denne SQL bruger en CTE (QUAL_VASK) til at sikre, at hver hændelse kun optræder ÉN gang.
    # Vi bruger MAX() for at finde ud af, om en qualifier findes, uden at skabe nye rækker.
    sql = f"""
        WITH QUAL_VASK AS (
            SELECT 
                EVENT_OPTAUUID,
                MAX(CASE WHEN QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
                MAX(CASE WHEN QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
                MAX(CASE WHEN QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
                MAX(CASE WHEN QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST,
                MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as EX,
                MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as EY
            FROM {DB}.OPTA_QUALIFIERS
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_X, e.EVENT_Y,
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
            q.IS_THROW_IN, q.IS_CORNER, q.IS_FREEKICK, q.IS_ASSIST, q.EX, q.EY
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN QUAL_VASK q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_TYPEID IN (1, 15, 16)
        AND (q.IS_THROW_IN = 1 OR q.IS_CORNER = 1 OR q.IS_FREEKICK = 1)
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Definer type
    conditions = [ (df['IS_CORNER'] == 1), (df['IS_THROW_IN'] == 1) ]
    choices = ['Hjørnespark', 'Indkast']
    df['TYPE'] = np.select(conditions, choices, default='Frispark')
    
    return df

def vis_side():
    st.title("Standardsituationer - Valideret")
    df = load_setpiece_data()
    
    if df.empty:
        st.warning("Ingen data fundet.")
        return

    # Hold-valg
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df['HOLD'] = df['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    hold_navn = st.selectbox("Hold", sorted(df['HOLD'].unique().tolist()), index=0)
    
    df_team = df[df['HOLD'] == hold_navn].copy()

    # --- BEREGNING AF STATISTIK (TABEL) ---
    stats = []
    for player, p_df in df_team.groupby('PLAYER_NAME'):
        # Succeslogik: 
        # For indkast bruger vi Outcome=1. 
        # For hjørne/frispark bruger vi Assist (skabt chance) for at være realistiske.
        c_df = p_df[p_df['TYPE'] == 'Hjørnespark']
        t_df = p_df[p_df['TYPE'] == 'Indkast']
        f_df = p_df[p_df['TYPE'] == 'Frispark']
        
        row = {
            'Navn': player,
            'Total': len(p_df),
            'Hjørne (Antal)': len(c_df),
            'Hjørne (Succes %)': (c_df['IS_ASSIST'].sum() / len(c_df) * 100) if len(c_df) > 0 else 0,
            'Indkast (Antal)': len(t_df),
            'Indkast (Succes %)': (t_df[t_df['EVENT_OUTCOME'] == 1].shape[0] / len(t_df) * 100) if len(t_df) > 0 else 0,
            'Frispark (Antal)': len(f_df),
            'Frispark (Succes %)': (f_df['IS_ASSIST'].sum() / len(f_df) * 100) if len(f_df) > 0 else 0
        }
        stats.append(row)

    df_stats = pd.DataFrame(stats).sort_values("Total", ascending=False)
    
    st.dataframe(df_stats, use_container_width=True, hide_index=True, 
                 column_config={f"{t} (Succes %)": st.column_config.NumberColumn(format="%.1f%%") for t in ["Hjørne", "Indkast", "Frispark"]})

    # --- PLOT (BANEN) ---
    st.divider()
    type_sel = st.radio("Se placeringer for:", ["Hjørnespark", "Indkast", "Frispark"], horizontal=True)
    df_plot = df_team[df_team['TYPE'] == type_sel]
    
    pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
    fig, ax = pitch.draw(figsize=(8, 10))
    
    if not df_plot.empty:
        # Tegn pile fra start til slut (skaleret til meter)
        pitch.arrows(df_plot.EVENT_X * 1.05, df_plot.EVENT_Y * 0.68, 
                     df_plot.EX.fillna(df_plot.EVENT_X) * 1.05, df_plot.EY.fillna(df_plot.EVENT_Y) * 0.68, 
                     color="#cc0000", ax=ax, width=2, alpha=0.3)
    
    st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
