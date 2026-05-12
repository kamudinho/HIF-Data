import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # SQL der samler alle tags (Qualifiers) til én række pr. hændelse
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID, 
        e.EVENT_X, 
        e.EVENT_Y, 
        e.EVENT_TYPEID, 
        e.EVENT_CONTESTANT_OPTAUUID, 
        e.PLAYER_OPTAUUID,
        -- Her samler vi alle qualifiers i en liste så vi ikke får dubletter
        LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUAL_LIST,
        -- Her trækker vi slutkoordinaterne ud specifikt
        MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDX,
        MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDY,
        MAX(CASE WHEN q.QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST,
        MAX(CASE WHEN q.QUALIFIER_QID = 321 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE 0 END) as XG,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM {DB}.OPTA_EVENTS e
    JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.MATCH_OPTAUUID IN ({match_sql})
    GROUP BY 1, 2, 3, 4, 5, 6, 12 -- Gruppering pr. unik hændelse
    HAVING (QUAL_LIST LIKE '%6%' OR QUAL_LIST LIKE '%107%' OR QUAL_LIST LIKE '%5%')
    """
    
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]

    # Konverter koordinater
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Brug din mapping logik (som nu får en ren liste af unikke events)
    df['qual_list'] = df['QUAL_LIST']
    df['SET_PIECE_TYPE'] = df.apply(get_action_label, axis=1)

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

def vis_side():
    st.title("🎯 Standardsituationer - Unikke Aktioner")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filter og Normalisering (Fixer pilene fra din screenshot)
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Normaliser angrebsretning (Flip alt til angreb mod top-mål)
    mask_flip = df_team['EVENT_X'] < 50
    for col_x, col_y in [('EVENT_X', 'EVENT_Y'), ('EVENT_ENDX', 'EVENT_ENDY')]:
        df_team.loc[mask_flip, col_x] = 100 - df_team.loc[mask_flip, col_x]
        df_team.loc[mask_flip, col_y] = 100 - df_team.loc[mask_flip, col_y]

    # Skalering
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    if side_sel == "Venstre":
        df_team = df_team[df_team['Y_M'] < 34]
    elif side_sel == "Højre":
        df_team = df_team[df_team['Y_M'] >= 34]

    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) 

        if not df_team.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            pitch.arrows(df_team.X_M, df_team.Y_M, df_team.ENDX_M, df_team.ENDY_M, 
                         width=2, headwidth=4, headlength=4, color=TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000'), ax=ax, alpha=0.6)
            pitch.scatter(df_team.ENDX_M, df_team.ENDY_M, s=80, edgecolors='white', c='red', ax=ax, zorder=3)
        
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik (Unikke)")
        st.metric("Antal hjørnespark", len(df_team))
        st.write("**Top udførere:**")
        st.dataframe(df_team['PLAYER_NAME'].value_counts(), use_container_width=True)

if __name__ == "__main__":
    vis_side()
