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
LIGA_UUID = "dyjr458hcmrc_LIGA_UUID" # Erstat med din korrekte UUID

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()

    # Sub-query til kampe
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # SQL der grupperer pr. unik hændelse og samler alle Qualifiers (Tags)
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
            -- Saml alle tags til ét felt for at undgå dubletter i tællingen
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUAL_LIST,
            -- Slutkoordinater (QID 140/141)
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDX,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as EVENT_ENDY,
            -- Taktiske tags fra din liste
            MAX(CASE WHEN q.QUALIFIER_QID = 214 THEN 1 ELSE 0 END) as IS_BIG_CHANCE,
            MAX(CASE WHEN q.QUALIFIER_QID = 223 THEN 'Inswinger' 
                     WHEN q.QUALIFIER_QID = 224 THEN 'Outswinger' 
                     WHEN q.QUALIFIER_QID = 225 THEN 'Straight' ELSE 'Standard' END) as SWING_TYPE
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.MATCH_OPTAUUID IN ({match_sql})
        GROUP BY 1, 2, 3, 4, 5, 6, 7
    )
    SELECT 
        b.*,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM EVENT_BASE b
    LEFT JOIN {DB}.OPTA_PLAYERS p ON b.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    -- Filtrér så vi kun får de rækker der er identificeret som standardsituationer
    WHERE (QUAL_LIST LIKE '%6%' OR QUAL_LIST LIKE '%107%' OR QUAL_LIST LIKE '%5%')
    """
    
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]

    # Konverter koordinater
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Brug din mapping logik
    df['qual_list'] = df['QUAL_LIST']
    df['SET_PIECE_TYPE'] = df.apply(get_action_label, axis=1)

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

def vis_side():
    st.markdown("<style>header {visibility: hidden;} .main .block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Filtre
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams_in_data, index=teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filtrering
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # --- NORMALISERING AF KOORDINATER ---
    # Tving alle aktioner til at vende "opad" mod modstanderens mål
    mask_flip = df_team['EVENT_X'] < 50
    for col_x, col_y in [('EVENT_X', 'EVENT_Y'), ('EVENT_ENDX', 'EVENT_ENDY')]:
        df_team.loc[mask_flip, col_x] = 100 - df_team.loc[mask_flip, col_x]
        df_team.loc[mask_flip, col_y] = 100 - df_team.loc[mask_flip, col_y]

    # Skalering til meter (105x68)
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    # Filtrér side efter normalisering
    if side_sel == "Venstre":
        df_team = df_team[df_team['Y_M'] < 34]
    elif side_sel == "Højre":
        df_team = df_team[df_team['Y_M'] >= 34]

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)

    # Layout
    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) 

        if not df_team.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            # Tegn pile
            pitch.arrows(df_team.X_M, df_team.Y_M, df_team.ENDX_M, df_team.ENDY_M, 
                         width=2, headwidth=4, headlength=4, color=t_color, ax=ax, alpha=0.6)
            # Markér landing spots
            pitch.scatter(df_team.ENDX_M, df_team.ENDY_M, s=80, edgecolors='white', c=t_color, linewidth=1, alpha=0.8, ax=ax, zorder=3)
        else:
            st.info("Ingen slut-koordinater fundet.")
        
        st.pyplot(fig)

    with col_s:
        st.subheader("Teknisk Statistik")
        total = len(df_team)
        st.metric("Antal unikke hændelser", total)
        
        if total > 0:
            # Big Chance logik (fra din QID 214)
            bc_count = int(df_team['IS_BIG_CHANCE'].sum())
            st.metric("Store chancer skabt", bc_count)

            # Swing type (fra din QID 223/224)
            if sp_type
