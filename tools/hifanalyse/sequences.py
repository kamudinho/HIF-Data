import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

# Direkte oversættelse af Opta IDs (hvis get_event_name driller)
OPTA_MAP_DK = {
    1: "Aflevering", 2: "Aflevering", 3: "Dribling", 4: "Tackling", 
    5: "Frispark", 6: "Hjørnespark", 7: "Tackling", 8: "Interception",
    10: "Redning", 12: "Skud", 13: "Skud", 14: "Skud", 15: "Skud", 
    16: "MÅL", 43: "Frispark", 44: "Indkast", 49: "Opsamling", 50: "Opsnapning"
}

def vis_side(dp):
    # 1. CSS (Enkel version for at undgå syntax fejl)
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid {HIF_RED}; margin-bottom: 5px; }}
            .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }}
            .play-flow {{ background: white; padding: 15px; border: 1px solid #ddd; border-radius: 5px; line-height: 1.5; }}
        </style>
    """, unsafe_allow_html=True)

    # Hent data
    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty:
        st.info("Venter på data...")
        return

    df = df_raw.copy()
    # Tving kolonnenavne til upper for at matche din SQL
    df.columns = [c.upper() for c in df.columns]
    
    # Rens UUID og find mål
    df['EVENT_CONTESTANT_OPTAUUID'] = df['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower()
    local_hif_uuid = HIF_UUID.lower()
    
    goals = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goals.empty:
        return

    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        sel_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique())
        sel_row = goals[goals['LABEL'] == sel_label].iloc[0]
        
        # Isoler hændelser for dette mål (HIF kun)
        target_seq_id = sel_row['SEQUENCEID']
        hif_seq = df[(df['SEQUENCEID'] == target_seq_id) & (df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid)].copy()
        hif_seq = hif_seq.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

        if not hif_seq.empty:
            scorer = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if pd.notnull(hif_seq.iloc[-1]['PLAYER_NAME']) else "HIF"
            assist = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"
            
            st.markdown(f'<div class="stat-box-side"><span class="dot" style="background-color:{HIF_RED}"></span><b>Målscorer:</b> {scorer}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><span class="dot" style="background-color:{ASSIST_BLUE}"></span><b>Assist:</b> {assist}</div>', unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Flip logik (HIF angriber altid mod højre i visningen)
        flip = True if sel_row['EVENT_X'] < 50 else False
        
        prev = None
        for i, r in hif_seq.iterrows():
            # Brug EVENT_X/Y da de ofte er mere stabile end RAW_X/Y
            x, y = r['EVENT_X'], r['EVENT_Y']
            cx = 100 - x if flip else x
            cy = 100 - y if flip else y
            
            if prev is not None:
                ax.annotate('', xy=(cx, cy), xytext=(prev[0], prev[1]),
                            arrowprops=dict(arrowstyle='->', color='#ccc', lw=1, alpha=0.5))
            
            p_name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            dot_col = HIF_RED if r['EVENT_TYPEID'] == 16 else (ASSIST_BLUE if p_name == assist else '#999')
            
            pitch.scatter(cx, cy, s=150, color=dot_col, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 3, p_name, fontsize=8, ha='center')
            prev = (cx, cy)
        
        st.pyplot(fig)

        # --- SEKVENS OVERSIGT ---
        st.write("### Angrebssekvens")
        flow_list = []
        for i, r in hif_seq.iterrows():
            name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
            # Her henter vi oversættelsen fra vores ordbog
            type_id = int(r['EVENT_TYPEID'])
            handling = OPTA_MAP_DK.get(type_id, f"Aktion {type_id}")
            flow_list.append(f"**{name}** ({handling})")
        
        st.markdown(f'<div class="play-flow">{" → ".join(flow_list)}</div>', unsafe_allow_html=True)

    # --- TOP INVOLVERINGER TABEL ---
    st.write("---")
    st.subheader("Involveringer i målsekvenser")
    
    # Vi tæller alle HIF-hændelser i hele det hentede datasæt
    all_hif = df[df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid].copy()
    if not all_hif.empty:
        all_hif['Spiller'] = all_hif['PLAYER_NAME'].str.split().str[-1]
        top_table = all_hif['Spiller'].value_counts().reset_index()
        top_table.columns = ['Spiller', 'Involveringer']
        st.dataframe(top_table.head(10), use_container_width=True, hide_index=True)
