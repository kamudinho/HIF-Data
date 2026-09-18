import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# IMPORTS
import data.hif_load as hif_load
from data.users import get_users

# --- 1. KONFIGURATION & BRANDING ---
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
HIF_ROD = "#df003b"

st.set_page_config(
    page_title="HIF Data Hub",
    layout="wide",
    page_icon=HIF_LOGO_URL,
    initial_sidebar_state="auto"
)

# Centraliseret CSS
st.markdown(f"""
    <style>
        #MainMenu {{visibility: hidden;}}
        <footer> {{visibility: hidden;}}
        header {{visibility: visible !important; background: transparent !important;}}
        [data-testid="stHeader"] {{background-color: transparent !important;}}
        [data-testid="stDecoration"] {{display: none;}}
        .block-container {{ padding-top: 1.5rem !important; }}
    </style>
""", unsafe_allow_html=True)

def render_hif_header(titel):
    st.markdown(f'''
        <div style="background-color: {HIF_ROD} !important; background: {HIF_ROD} !important; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 4px; margin-bottom: 15px; width: 100%;">
            <p style="color: white !important; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; margin: 0;">{titel}</p>
        </div>
    ''', unsafe_allow_html=True)


# --- 1.5. OPGAVE DIALOG VED LOGIN ---
@st.dialog("Ny opgave kræver handling")
def vis_opgave_popup(opgave_id, opgave_titel, opgave_beskrivelse):
    st.write("Du er blevet tildelt følgende aktive opgave:")
    st.info(f"**{opgave_titel}**\n\n{opgave_beskrivelse}")
    
    st.write("Du skal tage stilling til opgaven, før du kan fortsætte i systemet:")
    
    col1, col2, col3 = st.columns(3)
    aktuel_bruger = st.session_state.get("user", "ukendt")
    import tools.admin_page.opgaver as opg
    
    if col1.button("Godkend", use_container_width=True):
        df_disk = opg.indlaes_opgaver()
        if not df_disk.empty and "id" in df_disk.columns:
            df_disk["id"] = pd.to_numeric(df_disk["id"], errors="coerce")
            clean_id = int(opgave_id)
            
            df_disk.loc[df_disk["id"] == clean_id, "status"] = "I gang"
            if "scout_status" in df_disk.columns:
                df_disk.loc[df_disk["id"] == clean_id, "scout_status"] = "Igangsat"
                
            opg.gem_opgaver(df_disk)
        
        try:
            import tools.admin_page.admin as admin
            admin.save_action_log(aktuel_bruger, "Godkendte opgave", f"ID {opgave_id}: {opgave_titel}")
        except Exception:
            pass
            
        st.success("Opgave sat i gang!")
        st.session_state["task_handled"] = True
        st.rerun()
        
    if col2.button("Udskyd", use_container_width=True):
        df_disk = opg.indlaes_opgaver()
        if not df_disk.empty and "id" in df_disk.columns:
            df_disk["id"] = pd.to_numeric(df_disk["id"], errors="coerce")
            clean_id = int(opgave_id)
            
            df_disk.loc[df_disk["id"] == clean_id, "status"] = "Udskudt"
            if "scout_status" in df_disk.columns:
                df_disk.loc[df_disk["id"] == clean_id, "scout_status"] = "Afventer"
                
            opg.gem_opgaver(df_disk)
        
        try:
            import tools.admin_page.admin as admin
            admin.save_action_log(aktuel_bruger, "Udskød opgave", f"ID {opgave_id}: {opgave_titel}")
        except Exception:
            pass
            
        st.warning("Opgave udskudt til senere.")
        st.session_state["task_handled"] = True
        st.rerun()
        
    if col3.button("Afvis", use_container_width=True):
        df_disk = opg.indlaes_opgaver()
        if not df_disk.empty and "id" in df_disk.columns:
            df_disk["id"] = pd.to_numeric(df_disk["id"], errors="coerce")
            clean_id = int(opgave_id)
            
            df_disk.loc[df_disk["id"] == clean_id, "status"] = "Færdig"
            if "scout_status" in df_disk.columns:
                df_disk.loc[df_disk["id"] == clean_id, "scout_status"] = "Afvist"
                
            opg.gem_opgaver(df_disk)
        
        try:
            import tools.admin_page.admin as admin
            admin.save_action_log(aktuel_bruger, "Afviste opgave", f"ID {opgave_id}: {opgave_titel}")
        except Exception:
            pass
            
        st.error("Opgave afvist.")
        st.session_state["task_handled"] = True
        st.rerun()


# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown(f"""
        <style>
            [data-testid="stAppViewContainer"] {{ padding: 0 !important; }}
            [data-testid="stHeader"] {{ display: none; }}
            .stApp {{ background: linear-gradient(to right, white 35%, transparent 35%); }}
            [data-testid="stAppViewContainer"]::before {{
                content: ""; position: fixed; right: 0; top: 0; width: 65%; height: 100vh;
                background-image: url('https://static1.squarespace.com/static/573c1b7d01dbae9b52cd0936/573d6bdc37013bcc611eefd5/6477a814a3929d7ab0fa3006/1685610754298/GettyImages-1252722215.jpg?format=1500w');
                background-size: cover; background-position: left; opacity: 0.7; 
            }}
        </style>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([35, 65])
    
    with col_left:
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        _, center, _ = st.columns([0.8, 2.4, 0.8])
        with center:
            st.markdown(f'<div style="display: flex; justify-content: center;"><img src="{HIF_LOGO_URL}" style="width: 70px;"></div>', unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>HIF Data HUB</h2>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("BRUGER", placeholder="Brugernavn", label_visibility="collapsed").lower().strip()
                p = st.text_input("KODE", type="password", placeholder="Adgangskode", label_visibility="collapsed")
                if st.form_submit_button("LOG IND", use_container_width=True):
                    if u in USER_DB and USER_DB[u]["pass"] == p:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = u
                        st.session_state["task_handled"] = False

                        try:
                            import tools.admin_page.admin as admin
                            admin.save_action_log(u, "Login", "HIF Data Hub")
                        except Exception as log_e:
                            st.warning(f"Login lykkedes, men kunne ikke skrive til log: {log_e}")

                        st.rerun()
                    else: st.error("Ugyldig login")
    st.stop()


# --- 2.5. TJEK FOR UAFSLUTTEDE OPGAVER VED LOGIN ---
if st.session_state.get("logged_in") and not st.session_state.get("task_handled", False):
    aktuel_bruger = st.session_state["user"]
    try:
        import tools.admin_page.opgaver as opg
        df_alle_opgaver = opg.indlaes_opgaver()
        
        mine_aktive = df_alle_opgaver[
            (df_alle_opgaver["tildelt_til"] == aktuel_bruger) & 
            (df_alle_opgaver["status"] == "Afventer")
        ]
        
        if not mine_aktive.empty:
            foerste_opgave = mine_aktive.iloc[0]
            vis_opgave_popup(
                foerste_opgave["id"], 
                foerste_opgave["titel"], 
                foerste_opgave["beskrivelse"]
            )
        else:
            st.session_state["task_handled"] = True
    except Exception:
        st.session_state["task_handled"] = True


# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("""
        <style>
            [data-testid="stSidebarUserContent"] {
                padding-top: 1rem !important;
                overflow: hidden !important; 
                display: flex;
                flex-direction: column;
                height: 98vh; 
            }
            .nav-wrapper { flex-grow: 1; }
            .custom-hr {
                margin: 5px 0px !important;
                opacity: 0.2;
                border: 0;
                border-top: 1px solid #31333F;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-wrapper">', unsafe_allow_html=True)

    menu_style = {
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "color": "#31333F", "border-radius": "4px"},
        "nav-link-selected": {"background-color": HIF_ROD, "color": "white"}
    }

    from data.users import get_role_permissions
    user_info = USER_DB.get(st.session_state["user"], {})
    bruger_rolle = user_info.get("role", "scout")
    tilladelser = get_role_permissions().get(bruger_rolle, [])

    alle_omraader = ["HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "SCOUTING", "TILPASNING", "TESTSIDE", "ADMIN", "ADMIN_SCOUTING", "PROFIL"]

    if tilladelser == "ALL":
        synlige_hoved_options = alle_omraader
    else:
        menu_map_checker = {
            "HVIDOVRE IF": ["HVIDOVRE IF", "Forside"],
            "HOLDANALYSE": ["HOLDANALYSE", "Modstanderanalyse", "Kampoversigt", "Kampudvikling", "Afslutninger", "Målsekvenser", "Grafer", "BETINIA LIGAEN", "HIF ANALYSE"],
            "SPILLERANALYSE": ["SPILLERANALYSE", "Spiller-stats", "Spilleraktioner", "Spiller-profil", "Spilleroversigt", "Spillerprofil"],
            "TRUPPEN": ["TRUPPEN", "Oversigt", "Forecast"],
            "SCOUTING": ["SCOUTING", "Scoutrapport", "Database", "Emnedatabase", "Sammenligning", "Top10-scouting", "Opgaver", "Opret emne"],
            "TILPASNING": ["TILPASNING", "Spillerdata", "Spiller-score", "Standardsituationer"],
            "TESTSIDE": ["TESTSIDE", "Performance", "Winning Performance", "1. Div-tilpasning", "Charts", "Oversigt", "Forecast", "Model", "Transfers"],
            "ADMIN": ["ADMIN", "System Log", "Profil", "Datakatalog", "Konklusion", "Teamradar", "Spillerradar", "Fysisk profil", "Hold: Fysisk profil", "Intern analyse", "Top 5: Spillere", "Ordbog"],
            "ADMIN_SCOUTING": ["ADMIN_SCOUTING"],
            "PROFIL": ["PROFIL", "Profil"]
        }
        synlige_hoved_options = [
            hm for hm in alle_omraader 
            if any(item in tilladelser for item in menu_map_checker.get(hm, [hm]))
        ]
    
    if not synlige_hoved_options:
        synlige_hoved_options = ["SCOUTING"]

    if "main_menu_selection" not in st.session_state or st.session_state["main_menu_selection"] not in synlige_hoved_options:
        st.session_state["main_menu_selection"] = synlige_hoved_options[0]
    
    hoved_omraade = option_menu(
        None, options=synlige_hoved_options,
        icons=["play-fill"] * len(synlige_hoved_options),
        default_index=synlige_hoved_options.index(st.session_state["main_menu_selection"]),
        key="main_menu_widget", styles=menu_style
    )
    st.session_state["main_menu_selection"] = hoved_omraade

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    if hoved_omraade == "PROFIL":
        st.session_state["sub_menu_selection"] = "Profil"
    else:
        menu_map = {
            "HVIDOVRE IF": ["Forside"],
            "HOLDANALYSE": ["Modstanderanalyse", "Kampoversigt", "Kampudvikling", "Afslutninger", "Målsekvenser", "Grafer"],
            "SPILLERANALYSE": ["Spiller-stats", "Spilleraktioner", "Spiller-profil", "Spilleroversigt", "Spillerprofil"],
            "SCOUTING": ["Scoutrapport", "Database", "Emnedatabase", "Sammenligning", "Top10-scouting", "Opgaver"],
            "TILPASNING": ["Spillerdata", "Spiller-score", "Standardsituationer"],
            "TESTSIDE": ["Performance", "Winning Performance", "1. Div-tilpasning", "Charts", "Oversigt", "Forecast", "Model", "Transfers"],
            "ADMIN": ["System Log", "Profil", "Datakatalog", "Konklusion", "Teamradar", "Spillerradar", "Fysisk profil", "Hold: Fysisk profil", "Intern analyse", "Top 5: Spillere", "Ordbog"],
            "ADMIN_SCOUTING": ["Opgaver"]
        }
        
        mulige_under = menu_map.get(hoved_omraade, ["Forside"])
        if tilladelser == "ALL":
            aktuel_undermenu = mulige_under
        else:
            aktuel_undermenu = [u for u in mulige_under if u in tilladelser]
            
        if not aktuel_undermenu:
            aktuel_undermenu = [mulige_under[0]]
        
        if "sub_menu_selection" not in st.session_state or st.session_state["sub_menu_selection"] not in aktuel_undermenu:
            u_index = 0
        else:
            u_index = aktuel_undermenu.index(st.session_state["sub_menu_selection"])

        sel = option_menu(
            None, options=aktuel_undermenu,
            icons=["play-fill"] * len(aktuel_undermenu),
            default_index=u_index,
            key=f"sub_menu_{hoved_omraade}", 
            styles=menu_style
        )
        st.session_state["sub_menu_selection"] = sel

    _nuvaerende_fane = f"{hoved_omraade} -> {st.session_state.get('sub_menu_selection', '')}"
    if st.session_state.get("_forrige_fane") != _nuvaerende_fane:
        try:
            import tools.admin_page.admin as admin
            admin.save_action_log(st.session_state["user"], "Skiftede fane", _nuvaerende_fane)
        except Exception as log_e:
            st.warning(f"Kunne ikke skrive faneskift til log: {log_e}")
        st.session_state["_forrige_fane"] = _nuvaerende_fane

    st.markdown('</div>', unsafe_allow_html=True) 

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    if st.button("Ryd cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. DATA LOADING & RENDERING ---
if st.session_state['main_menu_selection'] == "PROFIL":
    render_hif_header("PROFIL")
else:
    render_hif_header(f"{st.session_state['main_menu_selection']}  |  {st.session_state['sub_menu_selection'].upper()}")

try:
    s = st.session_state["sub_menu_selection"]
    m = st.session_state["main_menu_selection"]

    if m == "PROFIL":
        import tools.admin_page.profil as profil
        profil.vis_side({})

    elif m == "HVIDOVRE IF":
        if s == "Forside":
            import HIF_head as fh
            fh.vis_side()
        else:
            dp_quick = hif_load.get_squad_only()
            if s == "Oversigt":
                import tools.truppen.players as pl
                pl.vis_side(dp_quick["players"])
            elif s == "Forecast":
                import tools.truppen.squad as sq
                sq.vis_side(dp_quick["players"])

    elif m == "SCOUTING":
        if s == "Opgaver":
            import tools.admin_page.opgaver as opg
            opg.vis_side()
        else:
            # Hent ugenummeret, så den kun henter nye data fra Snowflake én gang om ugen
            aktuel_uge = datetime.now().isocalendar()[1]
            
            with st.spinner("Henter scouting-data... (Henter automatisk kun 1 gang ugentligt)"):
                dp = hif_load.get_scouting_package(aktuel_uge)
                
            if s == "Scoutrapport":
                import tools.scouting.scout_input as si
                si.vis_side(dp)
            elif s == "Database":
                import tools.scouting.scout_db as sdb
                sdb.vis_side(dp["scout_reports"], dp["players"], dp["sql_players"], dp["career"])
            elif s == "Emnedatabase":
                import tools.scouting.emne_db as edb
                edb.vis_side()
            elif s == "Sammenligning":
                import tools.scouting.sammenligning as comp
                comp.vis_side(dp["players"], None, dp["wyscout_players"], dp["career"], dp["sql_players"], dp["advanced_stats"], dp.get("primaer_positioner"))
            elif s == "Top10-scouting":
                import tools.scouting.top10_scouting as t10
                t10.vis_side(dp.get("advanced_stats"), dp.get("primaer_positioner"))
                
    elif m == "SPILLERANALYSE":
        if s == "Spillerprofil":
            import tools.players.player_profile as pp
            pp.vis_side()
        elif s == "Spilleroversigt":
            import tools.players.player_rank as pr
            pr.vis_side()
        elif s == "Målsekvenser":
            import tools.hifanalyse.sequences as ms
            ms.vis_side()
        elif s == "Spilleraktioner":
            import tools.players.player_actions as pa
            pa.vis_side()
        elif s == "Spiller-stats":
            import tools.players.player_stats as ps
            ps.vis_side()
        elif s == "Spiller-profil":
            import tools.players.player_profile2 as pp2
            pp2.vis_side()

    elif m == "HOLDANALYSE":
        if s == "Ligaoversigt":
            import tools.ligaen.test_teams as tt
            tt.vis_side()
        elif s == "Kampoversigt":
            import tools.ligaen.test_matches as tm
            tm.vis_side()
        elif s == "Afslutninger":
            import tools.ligaen.leagueshots as ls
            ls.vis_side()
        elif s == "Modstanderanalyse":
            import tools.hifanalyse.modstander_oversigt as mo
            mo.vis_side()
        elif s == "Grafer":
            import tools.ligaen.dataviz as dviz
            dviz.vis_side()
        elif s == "Målsekvenser":
            import tools.ligaen.sequences as ms
            ms.vis_side()
        elif s == "Kampudvikling":
            import tools.ligaen.kampudvikling as ku
            ku.vis_side()

    elif m == "TILPASNING":
        if s == "Spillerdata":
            import tools.tilpasning.spiller_tilpasning as tilpasning
            tilpasning.vis_side()
        elif s == "Spiller-score":
            import tools.players.player_score as pscore
            pscore.vis_side()
        elif s == "Standardsituationer":
            import tools.standarder.setpieces as std
            std.vis_side()

    elif m == "TESTSIDE":
        if s == "1. Div-tilpasning":
            import tools.tilpasning.div_tilpasning as div
            div.vis_side()
        elif s == "Grafer":
            import tools.ligaen.dataviz as dviz
            dviz.vis_side()
        elif s == "Winning Performance":
            import tools.analyse.winning_performance as wp
            wp.vis_side()
        elif s == "Performance":
            import tools.analyse.baseline_performance as bp
            bp.vis_side()
        elif s == "Model":
            import tools.ligaen.model as xg
            xg.vis_side()
        elif s == "Transfers":
            import tools.scouting.transfer_input as t_input
            t_input.vis_side()

    elif m == "ADMIN":
        if s == "System Log":
            import tools.admin_page.admin as admin
            admin.vis_log()
        elif s == "Profil":
            import tools.admin_page.profil as profil
            profil.vis_side({})
        elif s == "Konklusion":
            import tools.analyse.konklusion as kon
            kon.vis_side()
        elif s == "Datakatalog":
            import tools.admin_page.data_katalog as dk
            dk.vis_side(hif_load._get_snowflake_conn())
        elif s == "Fysisk profil":
            import tools.players.fysisk_player as fp
            fp.vis_side()
        elif s == "Hold: Fysisk profil":
            import tools.ligaen.hold_fysisk as hf
            hf.vis_side()
        elif s == "Intern analyse":
            import tools.admin_page.intern_modstanderanalyse as im
            im.vis_side()
        elif s == "Top 5: Spillere":
            import tools.players.top_players as tp
            tp.vis_side()
        elif s == "Ordbog":
            import utils.ordbog as ob
            ob.vis_side()
        elif s == "Spillerradar":
            import tools.players.spillerradar as sr
            sr.vis_side()
        elif s == "Teamradar":
            import tools.hifanalyse.teamradar as tr
            tr.vis_side()
        elif s == "Opgaver":
            import tools.admin_page.opgaver as opg
            opg.vis_side()

    elif m == "ADMIN_SCOUTING":
        if s == "Opgaver":
            import tools.admin_page.opgaver as opg
            opg.vis_side()

except Exception as e:
    st.error(f"Fejl ved indlæsning: {e}")
