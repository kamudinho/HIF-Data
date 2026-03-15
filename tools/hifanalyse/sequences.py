import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

# Dansk ordbog til aktioner (mapping af Opta IDs)
OPTA_MAP_DK = {
    1: "Aflevering", 2: "Aflevering", 3: "Dribling", 4: "Tackling", 
    5: "Frispark", 6: "Hjørnespark", 7: "Tackling", 8: "Interception",
    10: "Redning", 12: "Skud", 13: "Skud", 14: "Skud", 15: "Skud", 
    16: "MÅL", 43: "Frispark", 44: "Indkast", 49: "Opsamling", 50: "Opsnapning",
    107: "Restart"
}

def vis_side(dp):
    # CSS Styling til bokse og flow
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
            .play-flow-container {{ background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #eee; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .flow-step {{ font-weight: 700; color: #333; }}
            .flow-action {{ color: #666; font-size: 0.85rem; font-weight: 400; }}
            .flow-arrow {{ color: {HIF_RED}; margin: 0 10px; font-weight: bold; }}
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty:
        st.info("Ingen sekvens-data fundet.")
        return

    # Standardiser kolonnenavne
    df = df_raw.copy()
    df.columns = [c.upper() for c in df.columns]

    # Find rigtige X/Y kolonner
    col_x = 'RAW_X' if 'RAW_X' in df.columns else ('EVENT_X' if 'EVENT_X' in df.columns else None)
    col_y = 'RAW_Y' if 'RAW_Y' in df.columns else ('EVENT_Y' if 'EVENT_Y' in df.columns else None)

    if not col_x:
        st.error("Kunne ikke finde koordinater i data.")
        return

    df['EVENT_CONTESTANT_OPTAUUID'] = df['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower()
    local_hif_uuid = HIF_UUID.lower()
    
    # Isoler mål for drop-down
    goals = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goals.empty: return

    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        sel_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique())
        sel_row = goals[goals['LABEL'] == sel_label].iloc[0]
        
        # Hent HIF-sekvensen for det specifikke mål
        hif_seq = df[(df['SEQUENCEID'] == sel_row['SEQUENCEID']) & (df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid)].copy()
        hif_seq = hif_seq.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

        if not hif_seq.empty:
            scorer = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if pd.notnull(hif_seq.iloc[-1]['PLAYER_NAME']) else "HIF"
            assist = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"
            
            st.markdown(f'<div class="stat-box-side"><span class="dot" style="background-color:{HIF_RED}"></span><b>Målscorer:</b> {scorer}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><span class="dot" style="background-color:{ASSIST_BLUE}"></span><b>Assist:</b> {assist}</div>', unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        flip = True if sel_row[col_x] < 50 else False
        
        prev = None
        for i, r in hif_seq.iterrows():
            cx, cy = (100 - r[col_x] if flip else r[col_x]), (100 - r[col_y] if flip else r[col_y])
            if prev:
                ax.annotate('', xy=(cx, cy), xytext=(prev[0], prev[1]),
                            arrowprops=dict(arrowstyle='->', color='#ccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))
            
            p_name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            color = HIF_RED if r['EVENT_TYPEID'] == 16 else (ASSIST_BLUE if p_name == assist else '#999')
            pitch.scatter(cx, cy, s=180, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 3, p_name, fontsize=8, ha='center', fontweight='bold')
            prev = (cx, cy)
        st.pyplot(fig)

        # --- SEKVENS OVERSIGT (LAYOUT FIX) ---
        st.write("### Angrebssekvens")
        steps = []
        for _, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
            handling = OPTA_MAP_DK.get(int(r['EVENT_TYPEID']), f"Aktion {r['EVENT_TYPEID']}")
            if int(r['EVENT_TYPEID']) == 16: handling = "MÅL"
            
            steps.append(f'<span class="flow-step">{p}</span> <span class="flow-action">({handling})</span>')
        
        flow_html = f'<div class="play-flow-container">{" <span class="flow-arrow">→</span> ".join(steps)}</div>'
        st.markdown(flow_html, unsafe_allow_html=True)

    # --- TABEL: KAMP-INVOLVERINGER ---
    st.write("---")
    st.subheader(f"Mål-involveringer i denne kamp")
    
    # Tæller kun i det nuværende df (som er kampspecifikt)
    all_hif = df[df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid].copy()
    if not all_hif.empty:
        all_hif['Spiller'] = all_hif['PLAYER_NAME'].apply(lambda x: x.split()[-1] if pd.notnull(x) else "HIF")
        top_df = all_hif['Spiller'].value_counts().reset_index()
        top_df.columns = ['Spiller', 'Antal Aktioner']
        st.table(top_df.head(10))
