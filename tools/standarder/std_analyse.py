import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()

    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # Vi fjerner EVENT_TYPEID = 1 restriktionen for en sikkerheds skyld
    # Men beholder den præcise Qualifier-søgning
    sql = f"""
    WITH EVENT_BASE AS (
        SELECT 
            e.EVENT_OPTAUUID, 
            e.EVENT_X, 
            e.EVENT_Y, 
            e.EVENT_TYPEID, 
            e.EVENT_CONTESTANT_OPTAUUID, 
            e.PLAYER_OPTAUUID,
            e.MATCH_OPTAUUID,
            e.EVENT_OUTCOME,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUAL_LIST,
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDX,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDY,
            MAX(CASE WHEN q.QUALIFIER_QID = 214 THEN 1 ELSE 0 END) as IS_BIG_CHANCE,
            MAX(CASE WHEN q.QUALIFIER_QID = 223 THEN 'Inswinger' 
                     WHEN q.QUALIFIER_QID = 224 THEN 'Outswinger' 
                     WHEN q.QUALIFIER_QID = 225 THEN 'Straight' ELSE 'Standard' END) as SWING_TYPE
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.MATCH_OPTAUUID IN ({match_sql})
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    )
    SELECT 
        b.*,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM EVENT_BASE b
    LEFT JOIN {DB}.OPTA_PLAYERS p ON b.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE (
        ',' || QUAL_LIST || ',' LIKE '%,6,%' OR 
        ',' || QUAL_LIST || ',' LIKE '%,107,%' OR 
        ',' || QUAL_LIST || ',' LIKE '%,5,%'
    )
    """
    
    df = conn.query(sql)
    if df is None or df.empty:
        return pd.DataFrame()
        
    df.columns = [c.upper() for c in df.columns]

    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['qual_list'] = df['QUAL_LIST']
    df['SET_PIECE_TYPE'] = df.apply(get_action_label, axis=1)

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

def vis_side():
    st.title("🎯 Standardsituationer")
    
    df_all = load_setpiece_data()
    
    if df_all.empty:
        st.error("Kunne ikke hente data. Tjek om LIGA_UUID er korrekt.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    
    if not teams_in_data:
        st.warning("Ingen hold fundet i data. Viser rådata til fejlfinding:")
        st.write(df_all[['EVENT_OPTAUUID', 'EVENT_CONTESTANT_OPTAUUID']].head())
        return

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams_in_data, index=0)
    with col_f2:
        # Sikrer os at vi bruger de navne som din get_action_label returnerer
        available_types = df_all['SET_PIECE_TYPE'].unique()
        sp_type = st.selectbox("Type", available_types)
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Normalisering
    mask_flip = df_team['EVENT_X'] < 50
    for col_x, col_y in [('EVENT_X', 'EVENT_Y'), ('EVENT_ENDX', 'EVENT_ENDY')]:
        df_team.loc[mask_flip, col_x] = 100 - df_team.loc[mask_flip, col_x]
        df_team.loc[mask_flip, col_y] = 100 - df_team.loc[mask_flip, col_y]

    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    if side_sel == "Venstre":
        df_team = df_team[df_team['Y_M'] < 34]
    elif side_sel == "Højre":
        df_team = df_team[df_team['Y_M'] >= 34]

    if df_team.empty:
        st.info(f"Ingen {sp_type} fundet for {t_sel} med de valgte filtre.")
        return

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) 

        pitch.arrows(df_team.X_M, df_team.Y_M, df_team.ENDX_M, df_team.ENDY_M, 
                     width=2, headwidth=4, headlength=4, color=t_color, ax=ax, alpha=0.6)
        pitch.scatter(df_team.ENDX_M, df_team.ENDY_M, s=80, edgecolors='white', c=t_color, ax=ax, zorder=3)
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik")
        st.metric("Antal unikke spark", len(df_team))
        st.write("**Top udførere:**")
        st.dataframe(df_team['PLAYER_NAME'].value_counts(), use_container_width=True)

if __name__ == "__main__":
    vis_side()
