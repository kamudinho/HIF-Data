import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt

def vis_side(analysis_package):
    st.title("⚽ Opta Shapes & Formationer")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    
    if df_shapes.empty:
        st.warning("Ingen positionsdata fundet.")
        return

    # 1. Kamp-vælger
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg en kamp (UUID):", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. Hold-vælger (For at rydde op i visningen)
    hold_muligheder = df_match['SHAPE_LABEL'].unique()
    valgt_hold_label = st.selectbox("Vælg specifikt hold/taktik:", hold_muligheder)
    
    df_valgt = df_match[df_match['SHAPE_LABEL'] == valgt_hold_label]

    # 3. Vis Formation Stats
    st.metric("Valgt Formation", df_valgt['SHAPE_FORMATION'].iloc[0])
    st.caption(f"Taktik: {valgt_hold_label}")

    # 4. Parsing af spillere
    all_players = []
    for _, row in df_valgt.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        if not raw_roles: continue
        
        roles_list = json.loads(raw_roles) if isinstance(raw_roles, str) else raw_roles
        for p in roles_list:
            all_players.append(p)

    if all_players:
        df_p = pd.DataFrame(all_players)
        # Konverter koordinater til float
        df_p['X'] = pd.to_numeric(df_p['averageRolePositionX'])
        df_p['Y'] = pd.to_numeric(df_p['averageRolePositionY'])

        # --- VISUEL PITCH ---
        st.subheader("Visuelt Pitch Map")
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Tegn banen (simpel grøn boks)
        ax.set_facecolor('#224422')
        plt.plot([0, 100, 100, 0, 0], [0, 0, 100, 100, 0], color="white") # Ramme
        plt.axvline(50, color="white") # Midterlinje
        
        # Plot spillere
        # Bemærk: Opta koordinater skal ofte vendes/justeres alt efter system
        ax.scatter(df_p['X'], df_p['Y'], s=300, color='#e21a22', edgecolors='white', zorder=3)
        
        # Tilføj numre/navne på prikkerne
        for i, row in df_p.iterrows():
            ax.annotate(row.get('shirtNumber', ''), (row['X'], row['Y']), 
                        color='white', weight='bold', ha='center', va='center', fontsize=9, zorder=4)
            ax.annotate(row.get('roleDescription', ''), (row['X'], row['Y']-3), 
                        color='lightgray', ha='center', fontsize=7)

        plt.xlim(-5, 105)
        plt.ylim(-5, 105)
        plt.axis('off')
        st.pyplot(fig)

        # Vis tabellen under kortet
        st.subheader("Spillerdata")
        st.dataframe(df_p[['shirtNumber', 'roleDescription', 'X', 'Y']], use_container_width=True, hide_index=True)
