import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- 0. DYNAMISK KONFIGURATION ---
try:
    from data.season_show import TEAM_WYID, SEASONNAME
    TEAM_COLOR = '#d31313' 
except ImportError:
    TEAM_WYID = 38331
    SEASONNAME = "2025/2026"
    TEAM_COLOR = '#d31313'

def vis_side(df_shots, df_spillere, hold_map):
    st.markdown("<style>.main .block-container { padding-top: 2rem; }</style>", unsafe_allow_html=True)

    if df_shots is None or df_shots.empty:
        st.warning(f"Ingen skuddata fundet i Snowflake for {SEASONNAME}.")
        return

    # --- 1. DATA RENS & FORMATERING ---
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Mapping af kropsdele fra Wyscout koder/navne
    body_map = {
        'right_foot': 'Højre', 'left_foot': 'Venstre', 'head': 'Hoved',
        'other': 'Andet', 'head/body': 'Hoved'
    }

    # Rens Player IDs
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Filtrer til eget hold
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == TEAM_WYID].copy()

    # Formater Matchlabel: "HIF - Modstander 2-1" -> "vs. Modstander 2-1"
    # Vi fjerner "Hvidovre" eller hvad dit hold hedder i hold_map
    eget_hold_navn = hold_map.get(str(TEAM_WYID), "Hvidovre")
    
    def format_match(label):
        if pd.isna(label): return "Ukendt"
        return label.replace(eget_hold_navn, "").replace(" - ", "").replace("  ", " ").strip()

    df_s['MODSTANDER'] = df_s['MATCHLABEL'].apply(lambda x: f"vs. {format_match(x)}")

    # Spiller mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df.get('NAVN', 'Ukendt')))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
        
        df_p = df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()
        df_p = df_p.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # Beregninger
        SHOTS = len(df_p)
        GOALS = int(df_p['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        XG_TOTAL = df_p['SHOTXG'].sum()
        CONV_RATE = (GOALS / SHOTS * 100) if SHOTS > 0 else 0

        # Metrics blok
        st.markdown(f"""
            <div style="margin-top:10px; border-left: 4px solid {TEAM_COLOR}; padding-left: 15px; background-color: #f9f9f9; padding: 15px; border-radius: 0 10px 10px 0;">
                <small style="color:gray;">AFSLUTNINGER / MÅL</small>
                <div style="font-size:24px; font-weight:bold;">{SHOTS} / {GOALS}</div>
                <hr style="margin:10px 0;">
                <small style="color:gray;">KONVERTERINGSRATE</small>
                <div style="font-size:24px; font-weight:bold;">{CONV_RATE:.1f}%</div>
                <hr style="margin:10px 0;">
                <small style="color:gray;">TOTAL xG</small>
                <div style="font-size:24px; font-weight:bold;">{XG_TOTAL:.2f}</div>
            </div>
        """, unsafe_allow_html=True)

        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            tabel_df['RESULTAT'] = tabel_df['SHOTISGOAL'].apply(lambda x: "⚽ MÅL" if str(x).lower() in ['true', '1', '1.0', 't'] else "Skud")
            tabel_df['DEL'] = tabel_df['SHOTBODYPART'].map(body_map).fillna(tabel_df['SHOTBODYPART'])
            
            vis_tabel = tabel_df[['NR', 'MODSTANDER', 'MINUTE', 'DEL', 'RESULTAT']]
            vis_tabel.columns = ['#', 'Kamp', 'Min', 'Del', 'Res']
            st.dataframe(vis_tabel, hide_index=True)

    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
        fig, ax = pitch.draw(figsize=(6, 5))
        
        for _, row in df_p.iterrows():
            goal = str(row['SHOTISGOAL']).lower() in ['true', '1', '1.0', 't']
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=200 if goal else 130,
                       color='gold' if goal else TEAM_COLOR, 
                       edgecolors='white', linewidth=1, alpha=0.9, zorder=3)
            
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                    color='black' if goal else 'white', ha='center', va='center', 
                    fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
