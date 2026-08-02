import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from data.utils.team_mapping import TEAMS, TEAM_COLORS

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    """Henter holdets logo baseret på Opta UUID."""
    if not opta_uuid: 
        return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: 
        return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: 
        return None

def get_team_color(team_name, color_type="primary", default="#df003b"):
    """Finder holdets farve fra TEAM_COLORS mappingen."""
    found_colors = None
    for key, colors in TEAM_COLORS.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            found_colors = colors
            break
            
    if not found_colors:
        return default
        
    primary = found_colors.get("primary", default)
    secondary = found_colors.get("secondary", "#000000")
    
    if color_type == "primary" and primary.lower() in ["#ffffff", "white", "#fff"]:
        return secondary
        
    return found_colors.get(color_type, default)

def get_ordinal(n):
    """Konverterer et tal til ordinal-form (1st, 2nd, 3rd osv.)."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def oversæt_qualifiers(qualifier_list_str):
    """Oversætter Opta qualifier-IDs til læsevenlige tekster."""
    if not qualifier_list_str or not isinstance(qualifier_list_str, str):
        return ""
    
    # Eksempel på mapping - tilpas eller udvid denne efter behov i din app
    mapping = {
        "56": "Lang bold",
        "140": "Hovedstød",
        "9": "Fod",
        "210": "Indeni feltet",
        "212": "Langskud"
        # Tilføj flere Opta qualifier ID'er her hvis nødvendigt
    }
    
    q_ids = qualifier_list_str.split(",")
    oversatte = [mapping.get(q.strip(), f"Q:{q.strip()}") for q in q_ids if q.strip()]
    return ", ".join(oversatte)

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    """Tegner en spillerinfobox på et matplotlib/mplsoccer plot."""
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')
