import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
# Vigtig import til lazy loading
from data.data_load import load_snowflake_query

# --- 0. DYNAMISK KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    TEAM_COLOR = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    TEAM_COLOR = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    st.markdown("<style>.main .block-container { padding-top: 1.5rem; }</style>", unsafe_allow_html=True)

    # --- LAZY LOADING AF SKUDDATA ---
    if "shotevents_data" not in st.session_state:
        with st.spinner(f"Henter skuddata for {SEASONNAME}..."):
            dp = st.session_state["data_package"]
            # Vi henter specifikt 'shotevents'
            st.session_state["shotevents_data"] = load_snowflake_query(
                "shotevents", dp["comp_filter"], dp["season_filter"]
            )
            st.rerun()

    # Brug de hentede data fra session_state
    df_shots = st.session_state["shotevents_data"]

    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet for {SEASONNAME}.")
        return

    # --- 1. DATA-RENS ---
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE', 'TEAM_WYID']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    def to_bool(val):
        return str(val).lower() in ['true', '1', '1.0', 't', 'y']

    df_s['IS_GOAL'] = df_s['SHOTISGOAL'].apply(to_bool) if 'SHOTISGOAL' in df_s.columns else False
    
    # Filtrer på dit holds ID
    df_s = df_s[df_s['TEAM_WYID'] == TEAM_WYID].copy()

    if df_s.empty:
        st.warning(f"Ingen skud registreret for det valgte hold i {SEASONNAME}.")
        return

    # Formater Modstander
    eget_hold_navn = str(hold_map.get(str(int(TEAM_WYID)), "Hvidovre")).upper()
    def clean_label(label):
        if pd.isna(label): return "Ukendt"
        txt = str(label).upper().replace(eget_hold_navn, "").replace("-", "").strip()
        return f"vs. {txt.title()}" if txt else "Kamp"
    df_s['MODSTANDER'] = df_s['MATCHLABEL'].apply(clean_label) if 'MATCHLABEL' in df_s.columns else "Kamp"

    # Spiller mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID_STR'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID_STR'], s_df.get('NAVN', 'Ukendt')))
    df_s['PLAYER_ID_STR'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_STR'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # Beregninger
        SHOTS = len(df_p)
        GOALS = int(df_p['IS_GOAL'].sum())
        XG_TOTAL = df_p['SHOTXG'].sum()
        CONV_RATE = (GOALS / SHOTS * 100) if SHOTS > 0 else 0

        # --- METRICS BOKS ---
        html_content = f"""
        <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px 20px; background-color: #f1f3f6; border-radius: 0 8px 8px 0; margin-top: 10px; font-family: sans-serif;">
            <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase;">Afslutninger / Mål</p>
            <p style="margin:0 0 12px 0; font-size:28px; font-weight:800; color:#111;">{SHOTS} / {GOALS}</p>
            <div style="border-top:1px solid #d1d5db; margin-bottom:12px;"></div>
            <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase;">Konverteringsrate</p>
            <p style="margin:0 0 12px 0; font-size:28px; font-weight:800; color:#111;">{CONV_RATE:.1f}%</p>
            <div style="border-top:1px solid #d1d5db; margin-bottom:12px;"></div>
            <p style="margin:0; color:#555; font-size:11px; font-weight:700; text-transform:uppercase;">Total xG</p>
            <p style="margin:0; font-size:28px; font-weight:800; color:#111;">{XG_TOTAL:.2f}</p>
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)

        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            tabel_df['RES'] = tabel_df['IS_GOAL'].map({True: "⚽ MÅL", False: "Afslutning"})
            b_map = {'right_foot': 'Højre', 'left_foot': 'Venstre', 'head': 'Hoved', 'other': 'Andet'}
            tabel_df['DEL'] = tabel_df['SHOTBODYPART'].str.lower().map(b_map).fillna(tabel_df['SHOTBODYPART'])
            vis_tabel = tabel_df[['NR', 'MODSTANDER', 'MINUTE', 'DEL', 'SHOTXG', 'RES']]
            vis_tabel.columns = ['#', 'Kamp', 'Min', 'Del', 'xG', 'Res']
            st.dataframe(vis_tabel.style.format({'xG': '{:.2f}'}), hide_index=True, use_container_width=True)

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2, goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        ax.set_ylim(48, 102) 

        for _, row in df_p.iterrows():
            is_goal = row['IS_GOAL']
            p_size = 220 if is_goal else 110 
            
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], s=p_size,
                       color='gold' if is_goal else TEAM_COLOR, 
                       edgecolors='white', linewidth=1.2, alpha=1.0, zorder=3)
            
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                    color='black' if is_goal else 'white', ha='center', va='center', 
                    fontsize=7 if not is_goal else 8, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)
