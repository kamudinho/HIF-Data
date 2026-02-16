import streamlit as st
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side(df_live, hold_map):
    st.header("Taktisk Modstanderanalyse")
    
    if df_live is None or df_live.empty:
        st.info("Ingen data fundet i Snowflake for denne sæson.")
        return

    # Forbered data (rensning af typer og navne)
    df_live['PRIMARYTYPE'] = df_live['PRIMARYTYPE'].str.lower()
    df_live['HOLD_NAVN'] = df_live['TEAM_WYID'].astype(str).map(hold_map).fillna(df_live['TEAM_WYID'].astype(str))
    
    # Valg af modstander i sidebar
    alle_hold = sorted(df_live['HOLD_NAVN'].unique())
    valgt_hold = st.sidebar.selectbox("Vælg modstander", alle_hold)
    hold_data = df_live[df_live['HOLD_NAVN'] == valgt_hold]

    # --- 1. OVERORDNEDE METRICS (UDEN IKONER) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("AKTIONER I ALT", len(hold_data))
    with c2:
        st.metric("EGNE SKUD", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot']))
    with c3:
        st.metric("SKUD IMOD", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot_against']))
    with c4:
        avg_xg = hold_data[hold_data['PRIMARYTYPE'] == 'shot']['SHOTXG'].mean() if 'SHOTXG' in hold_data.columns else 0
        st.metric("AVG. xG/SKUD", f"{avg_xg:.2f}" if avg_xg > 0 else "-")

    st.divider()

    # --- 2. TAKTISKE BANER ---
    pitch = VerticalPitch(
        pitch_type='wyscout', 
        pitch_color='white', 
        line_color='#888888', 
        linewidth=0.5,
        pad_top=0, pad_bottom=0
    )
    
    cols = st.columns(3)
    # Mapping af typer til titler og farver
    configs = [
        ('pass', 'PASNINGER (FINAL 3RD)', 'Reds'), 
        ('shot', 'AFSLUTNINGSMØNSTER', 'YlOrBr'), 
        ('shot_against', 'SKUD MODTAGET', 'Purples')
    ]

    for i, (p_type, title, cmap) in enumerate(configs):
        with cols[i]:
            st.markdown(f"<p style='text-align:center; font-size:13px; font-weight:bold;'>{title.upper()}</p>", unsafe_allow_html=True)
            
            fig, ax = pitch.draw(figsize=(3, 4.5))
            d = hold_data[hold_data['PRIMARYTYPE'] == p_type]
            
            if not d.empty:
                # Heatmap / KDE Plot
                try:
                    sns.kdeplot(
                        x=d['LOCATIONY'], y=d['LOCATIONX'], 
                        fill=True, alpha=.6, cmap=cmap, ax=ax,
                        levels=8, thresh=.05, bw_adjust=0.8
                    )
                except:
                    # Fallback hvis der er for få datapunkter til et heatmap
                    pitch.scatter(d['LOCATIONX'], d['LOCATIONY'], alpha=0.5, color='grey', ax=ax)
                
                # Hvis det er skud, så tegn de præcise punkter ovenpå
                if 'shot' in p_type:
                    pitch.scatter(d['LOCATIONX'], d['LOCATIONY'], s=15, edgecolors='#333333', linewidth=0.5, c='white', alpha=0.8, ax=ax)
            
            st.pyplot(fig)
            
    # --- 3. KAMP-LISTE ---
    with st.expander("SE ENKELTE KAMPE FOR DETTE HOLD"):
        kampe = hold_data['MATCHLABEL'].unique()
        for k in kampe:
            st.write(f"- {k}")
