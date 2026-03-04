import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME

# --- 1. SQL QUERY FUNKTION ---
def get_opta_queries(liga_uuid=None, saeson_navn=None):
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # Bruger værdier fra team_mapping: SEASONNAME = "2025/2026"
    liga = liga_uuid if liga_uuid else COMPETITION_NAME
    saeson = saeson_navn if saeson_navn else TOURNAMENTCALENDAR_NAME
    
    return {
        "opta_shotevents": f"""
            SELECT 
                e.MATCH_OPTAUUID, 
                e.EVENT_OPTAUUID, 
                e.EVENT_CONTESTANT_OPTAUUID,
                e.PLAYER_NAME, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME,
                e.EVENT_TYPEID,
                e.EVENT_PERIODID,
                e.EVENT_TIMEMIN,
                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN q.QUALIFIER_VALUE END) as PASS_END_X,
                MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN q.QUALIFIER_VALUE END) as PASS_END_Y,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TYPEID IN (1, 13, 14, 15, 16)
            AND e.TOURNAMENTCALENDAR_OPTAUUID IN (
                SELECT DISTINCT TOURNAMENTCALENDAR_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_NAME = '{saeson}'
            )
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
        """
    }

# --- 2. STREAMLIT VISUALISERING ---

# HIF Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
HIF_BLUE = '#0056a3'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    # CSS til de bokse du bad om
    st.markdown("""
        <style>
        .stat-container { display: flex; gap: 10px; margin-bottom: 20px; }
        .stat-box { 
            padding: 15px; border-radius: 8px; background: #f0f2f6; 
            border-left: 5px solid #cc0000; flex: 1; text-align: center;
        }
        .stat-label { font-size: 12px; text-transform: uppercase; color: #555; font-weight: bold; }
        .stat-value { font-size: 24px; font-weight: bold; color: #111; }
        </style>
    """, unsafe_allow_html=True)

    # Hent data
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    
    if df_raw.empty:
        st.info("Ingen kampdata fundet for denne sæson.")
        return

    # Data Rens (Sørg for tal-formater)
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)
    
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        # Skudtyper: 13, 14, 15 (Skud), 16 (Mål)
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        # Stat-bokse
        n_skud = len(df_skud)
        n_maal = len(df_skud[df_skud['EVENT_TYPEID'] == 16])
        
        st.markdown(f"""
            <div class="stat-container">
                <div class="stat-box"><div class="stat-label">Afslutninger</div><div class="stat-value">{n_skud}</div></div>
                <div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{n_maal}</div></div>
            </div>
        """, unsafe_allow_html=True)

        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_skud.empty:
            # Tegn mål (16)
            df_goals = df_skud[df_skud['EVENT_TYPEID'] == 16]
            pitch.scatter(df_goals.EVENT_X, df_goals.EVENT_Y, s=200, 
                         c=HIF_RED, edgecolors='black', label='Mål', ax=ax, zorder=3)
            
            # Tegn øvrige skud
            df_miss = df_skud[df_skud['EVENT_TYPEID'] != 16]
            pitch.scatter(df_miss.EVENT_X, df_miss.EVENT_Y, s=150, 
                         c='white', edgecolors=HIF_RED, label='Andet skud', ax=ax, zorder=2)
            
            # Legend
            ax.legend(loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=2, fontsize=10)
        
        st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        # Assists (210) og Key Passes (29)
        df_chance = df_hif[(df_hif['EVENT_TYPEID'] == 1) & (df_hif['QUAL_STR'].str.contains('210|29'))].copy()
        
        n_ast = df_chance['QUAL_STR'].str.contains('210').sum()
        n_key = df_chance['QUAL_STR'].str.contains('29').sum()

        st.markdown(f"""
            <div class="stat-container">
                <div class="stat-box" style="border-left-color: {HIF_GOLD}"><div class="stat-label">Assists</div><div class="stat-value">{n_ast}</div></div>
                <div class="stat-box" style="border-left-color: {HIF_BLUE}"><div class="stat-label">Key Passes</div><div class="stat-value">{n_key}</div></div>
            </div>
        """, unsafe_allow_html=True)

        pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
        
        if not df_chance.empty:
            # Pile for afleveringer
            pitch_a.arrows(df_chance.EVENT_X, df_chance.EVENT_Y, df_chance.PASS_END_X, df_chance.PASS_END_Y, 
                         color='#dddddd', width=2, zorder=1, ax=ax_a)
            
            # Assists (Guld)
            df_ast_pts = df_chance[df_chance['QUAL_STR'].str.contains('210')]
            pitch_a.scatter(df_ast_pts.EVENT_X, df_ast_pts.EVENT_Y, s=150, 
                           c=HIF_GOLD, edgecolors='white', label='Assist', ax=ax_a, zorder=2)
            
            # Key Passes (Blå)
            df_key_pts = df_chance[~df_chance['QUAL_STR'].str.contains('210')]
            pitch_a.scatter(df_key_pts.EVENT_X, df_key_pts.EVENT_Y, s=120, 
                           c=HIF_BLUE, edgecolors='white', label='Key Pass', ax=ax_a, zorder=2)
            
            # Legend
            ax_a.legend(loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=2, fontsize=10)
            
        st.pyplot(fig_a)
