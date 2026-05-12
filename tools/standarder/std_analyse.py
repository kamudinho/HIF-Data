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
# Opdateret til din aktuelle sæson UUID
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # SQL der samler Qualifiers i en sub-query for at undgå at mangedoble hændelser
    sql = f"""
    WITH AGG_QUALS AS (
        SELECT 
            EVENT_OPTAUUID,
            LISTAGG(QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUAL_LIST,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDY,
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
        e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID, 
        e.PLAYER_OPTAUUID as PLAYER_UUID,
        q.QUAL_LIST,
        q.ENDX as EVENT_ENDX,
        q.ENDY as EVENT_ENDY,
        q.SWING_TYPE,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN AGG_QUALS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.MATCH_OPTAUUID IN (
        SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    )
    AND e.EVENT_TYPEID = 1 
    AND (
        ',' || q.QUAL_LIST || ',' LIKE '%,6,%' OR 
        ',' || q.QUAL_LIST || ',' LIKE '%,107,%' OR 
        ',' || q.QUAL_LIST || ',' LIKE '%,5,%'
    )
    """
    
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    def assign_label(row):
        ql = ',' + str(row['QUAL_LIST']) + ','
        if ',6,' in ql: return "Hjørnespark"
        if ',107,' in ql: return "Indkast"
        if ',5,' in ql: return "Frispark"
        return "Andet"
    
    df['SET_PIECE_TYPE'] = df.apply(assign_label, axis=1)
    return df[df['SET_PIECE_TYPE'] != "Andet"]

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.title("🎯 Standardsituationer")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.error("Kunne ikke hente data fra databasen.")
        return

    # Team mapping og metadata
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Filtre i toppen
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams_in_data, index=teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filtrering og dublet-tjek (vigtigt!)
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()
    df_team = df_team.drop_duplicates(subset=['EVENT_OPTAUUID'])

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

    # Tabs til de forskellige visninger
    tab_bane, tab_data = st.tabs(["🏟️ Banevisning", "📊 Rådata & Statistik"])

    with tab_bane:
        col_p, col_s = st.columns([2, 1])
        
        with col_p:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(10, 12))
            ax.set_ylim(50, 105) 
            
            t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
            valid = df_team.dropna(subset=['ENDX_M', 'ENDY_M'])
            
            if not valid.empty:
                pitch.arrows(valid.X_M, valid.Y_M, valid.ENDX_M, valid.ENDY_M, color=t_color, ax=ax, alpha=0.4, width=2)
                pitch.scatter(valid.ENDX_M, valid.ENDY_M, s=60, edgecolors='white', c=t_color, ax=ax, zorder=3)
            else:
                st.info("Ingen slutpositioner at vise.")
            st.pyplot(fig)

        with col_s:
            st.subheader("Overblik")
            st.metric(f"Total {sp_type}", len(df_team))
            st.write("**Top skytter:**")
            st.write(df_team['PLAYER_NAME'].value_counts().head(5))
            
            if sp_type == "Hjørnespark":
                st.write("**Skru:**")
                st.write(df_team['SWING_TYPE'].value_counts())

    with tab_data:
        st.subheader(f"Alle registrerede {sp_type}")
        # Vi viser de vigtigste kolonner for at gøre det overskueligt
        vis_df = df_team[['PLAYER_NAME', 'SWING_TYPE', 'EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']].copy()
        st.dataframe(vis_df, use_container_width=True)
        
        st.download_button(
            label="Download data som CSV",
            data=vis_df.to_csv(index=False).encode('utf-8'),
            file_name=f"{t_sel}_{sp_type}.csv",
            mime='text/csv',
        )

if __name__ == "__main__":
    vis_side()
