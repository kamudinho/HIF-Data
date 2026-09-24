# --- 5. RUTEVALG (ROUTER) ---
    try:
        import importlib.util
        import sys
        import pathlib

        if m == "Forside":
            mod_path = pathlib.Path("pages/01_oversigt/forside.py")
            if mod_path.exists():
                spec = importlib.util.spec_from_file_location("forside", mod_path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["forside"] = mod
                spec.loader.exec_module(mod)
            else:
                st.warning("Kunne ikke finde 'pages/01_oversigt/forside.py'. Sørg for filen ligger i mappen.")

        elif m == "HOLDANALYSE":
            if s == "Modstanderanalyse":
                mod_path = pathlib.Path("pages/02_holdanalyse/Modstanderanalyse.py")
                if mod_path.exists():
                    spec = importlib.util.spec_from_file_location("Modstanderanalyse", mod_path)
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["Modstanderanalyse"] = mod
                    spec.loader.exec_module(mod)
                else:
                    st.warning("Kunne ikke finde 'pages/02_holdanalyse/Modstanderanalyse.py'.")

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

        elif m == "KAMPANALYSE":
            st.markdown(f'<div class="main-header">Kampanalyse: {s}</div>', unsafe_allow_html=True)
            st.info(f"Modul for {s} er under opbygning...")

    except ImportError as e:
        st.error(f"Kunne ikke indhente modulet for '{s}'. Detaljer: {e}")
    except Exception as e:
        st.error(f"Der opstod en fejl under indlæsning af siden: {e}")
