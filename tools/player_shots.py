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
        st.warning(f"Ingen skuddata fundet for {SEASONNAME}.")
        return

    # --- 1. SIKKER DATA-RENS ---
    df_s = df_shots.copy()
    df_s.columns = [str(c).upper() for c in df_s.columns]
    
    # Konverter alle vigtige kolonner til numeriske typer for at undgå fejl
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE', 'TEAM_WYID']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    # Hjælpefunktion til booleans (Snowflake sender ofte 1/0 eller True/False)
    def to_bool(val):
        return str(val).lower() in ['true', '1', '1.0', 't', 'y']

    df_s['IS_GOAL'] = df_s['SHOTISGOAL'].apply(to_bool) if 'SHOTISGOAL' in df_s.columns else False

    # Filtrer til eget hold
    df_s = df_s[df_s['TEAM_WYID'] == TEAM_WYID].copy()

    # Formater Modstander-navn
    eget_hold_navn = str(hold_map.get(str(int(TEAM_WYID)), "Hvidovre")).upper()
    
    def clean_label(label):
        if pd.isna(label): return "Ukendt"
        # Fjerner eget holdnavn og overflødige bindestreger
        txt = str(label).upper().replace(eget_hold_navn, "").replace("-", "").strip()
        return f"vs. {txt}" if txt else "Kamp"

    df_s['MODSTANDER'] = df_s['MATCHLABEL'].apply(clean_label) if 'MATCHLABEL' in df_s.columns else "Kamp"

    # Spiller mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df.get('NAVN', 'Ukendt')))
    
    df_s['PLAYER_ID_STR'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s['SPILLER_NAVN'] = df_s['PLAYER_ID_STR'].map(navne_dict).fillna("Ukendt Spiller")

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
        GOALS = int(df_p['IS_GOAL'].sum())
        XG_TOTAL = df_p['SHOTXG'].sum() if 'SHOTXG' in df_p.columns else 0
        CONV_RATE = (GOALS / SHOTS * 100) if SHOTS > 0 else 0

        # Metrics blok (HTML/CSS)
        st.markdown(f"""
            <div style="border-left: 5px solid {TEAM_COLOR}; padding: 15px; background: #f0f2f6; border-radius: 5px;">
                <p style="margin:0; font-size:13px; color:#555;">AFSLUTNINGER / MÅL</p>
                <p style="margin:0; font-size:26px; font-weight:bold;">{SHOTS} / {GOALS}</p>
                <div style="margin:10px 0; border-top:1px solid #ccc;"></div>
                <p style="margin:0; font-size:13px; color:#555;">KONVERTERINGSRATE</p>
                <p style="margin:0; font-size:26px; font-weight:bold;">{CONV_RATE:.1f}%</p>
                <div style="margin:10px 0; border-top:1px solid #ccc;"></div>
                <p style="margin:0; font-size:13px; color:#555;">TOTAL xG</p>
                <p style="margin:0; font-size:26px; font-weight:bold;">{XG_TOTAL:.2f}</p>
            </div>
        """, unsafe_allow_html=True)

        with st.popover("Se alle afslutninger", use_container_width=True):
            tabel_df = df_p.copy()
            tabel_df['RES'] = tabel_df['IS_GOAL'].map({True: "⚽ MÅL", False: "Skud"})
            
            # Bodypart mapping
            b_map = {'right_foot': 'Højre', 'left_foot': 'Venstre', 'head': 'Hoved', 'other': 'Andet'}
            tabel_df['DEL'] = tabel_df['SHOTBODYPART'].str.lower().map(b_map).fillna(tabel_df['SHOTBODYPART'])
            
            vis_tabel = tabel_df[['NR', 'MODSTANDER', 'MINUTE', 'DEL', 'RES']]
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

    with col_map:
        # Pitch setup - Vi reducerer figsize lidt for at få bedre proportioner
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
        fig, ax = pitch.draw(figsize=(5, 4)) # Lidt mindre figur giver bedre kontrol over punktstørrelsen
        ax.set_ylim(45, 102) 

        for _, row in df_p.iterrows():
            is_goal = row['IS_GOAL']
            
            # Vi skalerer størrelsen markant ned:
            # Mål: 120 (før 220)
            # Skud: 70 (før 140)
            point_size = 120 if is_goal else 70
            
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=point_size,
                       color='gold' if is_goal else TEAM_COLOR, 
                       edgecolors='white', 
                       linewidth=0.8, # Finere kant
                       alpha=0.9, 
                       zorder=3)
            
            # Nummeret skal også være mindre for at passe i de mindre cirkler
            ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['NR'])), 
                    color='black' if is_goal else 'white', 
                    ha='center', va='center', 
                    fontsize=5, # Mindre font
                    fontweight='bold', 
                    zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
