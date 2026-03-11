import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import os
import requests
from PIL import Image
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# --- 1. OPSÆTNING ---
# (Behold dine METRIC_PAIRS og stier fra dit eget script)

def create_pizza_total(df_orig, team_id):
    df = df_orig.copy()

    # Data normalisering (Håndtering af komma og division med kampe)
    all_metrics = [col for group in METRIC_PAIRS.values() for pair in group for col in pair]
    for col in list(set(all_metrics)):
        clean_col = col.replace(' ', '')
        if clean_col in df.columns:
            # Konverter til float og divider med kampe (undtagen PPDA)
            df[clean_col] = pd.to_numeric(df[clean_col].astype(str).str.replace(',', '.'), errors='coerce')
            if clean_col != 'PPDA':
                df[clean_col] = df[clean_col] / df['MATCHES']

    target_team = df[df['TEAM_WYID'] == team_id]
    if target_team.empty: 
        print(f"Hold ID {team_id} ikke fundet."); return

    # --- DATA FORBEREDELSE ---
    plot_labels, values, display_values, plot_colors = [], [], [], []
    color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING': '#f1c40f', 'DEFENSIV': '#e74c3c'}

    for group_name, pairs in METRIC_PAIRS.items():
        for total_col, _ in pairs:
            col_to_use = total_col.replace(' ', '')
            if col_to_use not in df.columns: continue

            # Beregn percentil
            p_val = stats.percentileofscore(df[col_to_use].dropna(), target_team[col_to_use].values[0])
            
            # Inverter stats hvor lavt er godt (Mål imod og PPDA)
            if col_to_use in ['CONCEDEDGOALS', 'PPDA']: 
                p_val = 100 - p_val

            plot_labels.append(total_col)
            values.append(p_val)
            display_values.append(f"{target_team[col_to_use].values[0]:.1f}")
            plot_colors.append(color_map[group_name])

    # --- PLOTTING ---
    num_vars = len(plot_labels)
    # Beregn vinkler (0 til 2*pi)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
    width = (2 * np.pi) / num_vars # Bredden på hver "skive"

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))

    # GENNEMSIGTIGHED
    fig.patch.set_alpha(0) # Gør figurens baggrund gennemsigtig
    ax.set_facecolor('none') # Gør selve plottets baggrund gennemsigtig
    
    # Skjul grid og akser
    ax.grid(False)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.spines['polar'].set_visible(False)

    # Tegn de yderste hjælpelinjer (cirkler)
    for r in [20, 40, 60, 80, 100]:
        ax.plot(np.linspace(0, 2*np.pi, 100), [r]*100, color="white", linewidth=0.8, alpha=0.2, zorder=2)

    # Tegn "pizzaskiverne" (baggrundslinjer)
    ax.bar(angles, [100]*num_vars, width=width, color='none', edgecolor='white', 
           linewidth=1, alpha=0.1, zorder=1, align='edge')

    # Tegn data-barerne
    # Vi sætter 'bottom' til f.eks. 20 for at give plads til logoet i midten
    INNER_BLANK = 25 
    ax.bar(angles, values, width=width, bottom=INNER_BLANK, color=plot_colors, 
           edgecolor='white', linewidth=1.5, alpha=0.85, zorder=3, align='edge')

    # Tilføj logo i midten
    logo_img = get_logo(LOGO_URL)
    if logo_img:
        imagebox = OffsetImage(logo_img, zoom=0.8)
        ab = AnnotationBbox(imagebox, (0, 0), frameon=False, zorder=10)
        ax.add_artist(ab)

    # Akse-indstillinger
    ax.set_theta_offset(np.pi / 2) # Start i toppen
    ax.set_theta_direction(-1)     # Gå med uret
    ax.set_ylim(0, 130)            # Ekstra plads til tekst i kanten

    # --- TEKST OG LABELS ---
    for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
        # Find position for label (lidt uden for cirklen)
        # Vi lægger halvdelen af 'width' til vinklen for at centrere teksten over skiven
        text_angle = angle + (width / 2)
        
        # Labels (Hvid tekst)
        ax.text(text_angle, 115, label.replace(' ', '\n'), ha='center', va='center', 
                color='white', fontsize=10, fontweight='bold')
        
        # Værdi-bokse
        ax.text(text_angle, 105, disp, ha='center', va='center', color='white',
                fontsize=9, fontweight='bold', 
                bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.3', alpha=1))

    # Gem som transparent PNG
    if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)
    save_path = f"{OUTPUT_FOLDER}MIDDELFART_PIZZA_FINAL.png"
    plt.savefig(save_path, dpi=300, transparent=True, bbox_inches='tight')
    
    print(f"Success! Chart gemt her: {save_path}")
    plt.show()

# Kør funktionen
create_pizza_total(df_raw, MIDDELFART_TEAM_ID)
