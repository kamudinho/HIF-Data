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

    # SQL der bruger præcis kobling mellem Type og Qualifier
    sql = f"""
    WITH QUALS AS (
        SELECT 
            EVENT_OPTAUUID,
            LISTAGG(QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUAL_LIST,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as EVENT_ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as EVENT_ENDY,
            MAX(CASE WHEN QUALIFIER_QID = 214 THEN 1 ELSE 0 END) as IS_BIG_CHANCE,
            MAX(CASE WHEN QUALIFIER_QID = 223 THEN 'Inswinger' 
                     WHEN QUALIFIER_QID = 224 THEN 'Outswinger' 
                     WHEN QUALIFIER_QID = 225 THEN 'Straight' ELSE 'Standard' END) as SWING_TYPE
        FROM {DB}.OPTA_QUALIFIERS
        GROUP BY EVENT_OPTAUUID
    )
    SELECT 
        e.EVENT_OPTAUUID, 
        e.EVENT_X, 
        e.EVENT_Y, 
        e.EVENT_TYPEID, 
        e.EVENT_CONTESTANT_OPTAUUID, 
        e.PLAYER_OPTAUUID,
        e.EVENT_OUTCOME,
        q.QUAL_LIST,
        q.EVENT_ENDX,
        q.EVENT_ENDY,
        q.IS_BIG_CHANCE,
        q.SWING_TYPE,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM {DB}.OPTA_EVENTS e
    JOIN QUALS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.MATCH_OPTAUUID IN ({match_sql})
      AND e.EVENT_TYPEID = 1 -- Vi skal kun have pasninger/igangsætninger
      AND (
          ',' || q.QUAL_LIST || ',' LIKE '%,6,%' OR   -- Corner taken
          ',' || q.QUAL_LIST || ',' LIKE '%,5,%' OR   -- Free kick taken
          ',' || q.QUAL_LIST || ',' LIKE '%,107,%'    -- Throw in
      )
    """
    
    df = conn.query(sql)
    if df is None or df.empty:
        return pd.DataFrame()
        
    df.columns = [c.upper() for c in df.columns]

    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Overstyre labels direkte for at undgå fejl i din eksterne mapping-fil
    def assign_label(row):
        q = ',' + str(row['QUAL_LIST']) + ','
        if ',6,' in q: return "Hjørnespark"
        if ',107,' in q: return "Indkast"
        if ',5,' in q: return "Frispark"
        return "Andet"

    df['SET_PIECE_TYPE'] = df.apply(assign_label, axis=1)
    # Fjern "Andet" hvis der skulle være smuttet noget med
    df = df[df['SET_PIECE_TYPE'] != "Andet"]

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

def vis_side():
    st.title("🎯 Standardsituationer")
    
    df_all = load_setpiece_data()
    
    if df_all.empty:
        st.error("Ingen data fundet. Tjek databaseforbindelse.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams_in_data)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filtrering
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Normalisering (Angrebsretning mod top)
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
        st.info(f"Ingen {sp_type} fundet for {t_sel}.")
        return

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) 

        # Tegn kun hvis vi har slutkoordinater
        valid_arrows = df_team.dropna(subset=['ENDX_M', 'ENDY_M'])
        if not valid_arrows.empty:
            pitch.arrows(valid_arrows.X_M, valid_arrows.Y_M, valid_arrows.ENDX_M, valid_arrows.ENDY_M, 
                         width=2, headwidth=4, headlength=4, color=t_color, ax=ax, alpha=0.4)
            pitch.scatter(valid_arrows.ENDX_M, valid_arrows.ENDY_M, s=60, edgecolors='white', c=t_color, ax=ax, zorder=3)
        
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik")
        st.metric("Antal unikke spark", len(df_team))
        
        st.write("**Top udførere:**")
        # Dette vil nu vise de rigtige spillere og ikke keeperen
        st.dataframe(df_team['PLAYER_NAME'].value_counts().head(10), use_container_width=True)
        
        if sp_type == "Hjørnespark":
            st.write("**Type (Skru):**")
            st.write(df_team['SWING_TYPE'].value_counts())

if __name__ == "__main__":
    vis_side()
