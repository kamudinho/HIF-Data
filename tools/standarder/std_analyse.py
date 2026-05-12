import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # SQL optimeret til at undgå dubletter via GROUP BY på hændelses-niveau
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID, 
        MAX(e.EVENT_X) as EVENT_X, 
        MAX(e.EVENT_Y) as EVENT_Y, 
        MAX(e.EVENT_CONTESTANT_OPTAUUID) as TEAM_UUID, 
        MAX(e.PLAYER_OPTAUUID) as PLAYER_UUID,
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
      AND e.EVENT_TYPEID = 1
    GROUP BY e.EVENT_OPTAUUID
    HAVING (
        ',' || QUAL_LIST || ',' LIKE '%,6,%' OR 
        ',' || QUAL_LIST || ',' LIKE '%,107,%' OR 
        ',' || QUAL_LIST || ',' LIKE '%,5,%'
    )
    """
    
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    # Hent spillernavne separat for at undgå JOIN-dubletter
    player_sql = f"SELECT PLAYER_OPTAUUID, TRIM(FIRST_NAME) || ' ' || TRIM(LAST_NAME) as PLAYER_NAME FROM {DB}.OPTA_PLAYERS"
    pdf = conn.query(player_sql)
    pdf.columns = [c.upper() for c in pdf.columns]
    
    df = df.merge(pdf, left_on='PLAYER_UUID', right_on='PLAYER_OPTAUUID', how='left')

    # Type-labeling
    def assign_label(row):
        q = ',' + str(row['QUAL_LIST']) + ','
        if ',6,' in q: return "Hjørnespark"
        if ',107,' in q: return "Indkast"
        if ',5,' in q: return "Frispark"
        return "Andet"
    
    df['SET_PIECE_TYPE'] = df.apply(assign_label, axis=1)
    return df[df['SET_PIECE_TYPE'] != "Andet"]

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.title("🎯 Standardsituationer (Renset)")
    df_all = load_setpiece_data()
    if df_all.empty:
        st.error("Ingen data fundet.")
        return

    # Map team UUIDs til Navne
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        t_sel = st.selectbox("Vælg hold (Eget eller modstander)", teams_in_data)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])

    # KRITISK FILTRERING: Her skiller vi Hvidovre fra modstanderen
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Normalisering og beregning
    mask_flip = df_team['EVENT_X'] < 50
    for col_x, col_y in [('EVENT_X', 'EVENT_Y'), ('EVENT_ENDX', 'EVENT_ENDY')]:
        df_team.loc[mask_flip, col_x] = 100 - df_team.loc[mask_flip, col_x]
        df_team.loc[mask_flip, col_y] = 100 - df_team.loc[mask_flip, col_y]

    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) 
        
        valid = df_team.dropna(subset=['ENDX_M', 'ENDY_M'])
        pitch.arrows(valid.X_M, valid.Y_M, valid.ENDX_M, valid.ENDY_M, color=TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED), ax=ax, alpha=0.4)
        pitch.scatter(valid.ENDX_M, valid.ENDY_M, s=60, edgecolors='white', c=TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED), ax=ax)
        st.pyplot(fig)

    with col_s:
        st.subheader(f"Statistik for {t_sel}")
        st.metric("Antal unikke aktioner", len(df_team))
        st.write("**Top udførere:**")
        st.dataframe(df_team['PLAYER_NAME'].value_counts().head(10))

if __name__ == "__main__":
    vis_side()
