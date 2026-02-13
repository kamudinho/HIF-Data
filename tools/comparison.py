def hent_spiller_data(navn):
    try:
        # Find ID'et i det samlede dataframe
        p_id = samlet_df[samlet_df['Navn'] == navn]['ID'].iloc[0]
        
        # GitHub/Wyscout ID-fix: Vi konverterer altid til ren integer-streng
        # for at undgå "12345.0" vs "12345" problemet
        search_id = str(int(float(p_id))) if pd.notna(p_id) else "0"
        
        # 1. Hent Basis Info (Position og Klub)
        klub = "Ukendt klub"
        pos = "Ukendt"
        if navn in df_hif['Full_Name'].values:
            klub = "Hillerød Fodbold"
            pos = df_hif[df_hif['Full_Name'] == navn]['POSITION'].iloc[0]
        elif navn in df_scout['NAVN'].values:
            match = df_scout[df_scout['NAVN'] == navn].iloc[0]
            klub = match.get('KLUB', 'Scouted klub')
            pos = match.get('POSITION', 'Ukendt')

        # 2. Hent Wyscout Stats (player_events fra dit repo)
        # Vi sikrer os at vi sammenligner strenge
        stats_match = player_events[player_events['PLAYER_WYID'].astype(str).str.contains(search_id, na=False)]
        stats = stats_match.iloc[0].to_dict() if not stats_match.empty else {}

        # 3. Hent Scouting Data (df_scout fra dit repo)
        # Her gør vi ID-kolonnen i df_scout søgbar ved at fjerne .0 midlertidigt
        scout_match = df_scout[df_scout['ID'].astype(str).str.split('.').str[0] == search_id]
        
        tech_vals = []
        scout_dict = {'s': 'Ingen data', 'u': 'Ingen data', 'v': 'Ingen vurdering', 'klub': klub, 'pos': pos}

        if not scout_match.empty:
            nyeste = scout_match.sort_values('DATO', ascending=False).iloc[0]
            
            # Map værdier til radaren (TEKNIK, FART osv.)
            for label, excel_col in radar_defs.items():
                val = nyeste.get(excel_col, 0)
                # Hvis værdien er NaN eller tom, sæt til 0
                tech_vals.append(float(val) if pd.notna(val) else 0.0)
            
            scout_dict.update({
                's': nyeste.get('STYRKER', 'Ingen data'),
                'u': f"**Potentiale:** {nyeste.get('POTENTIALE','')}\n\n**Udvikling:** {nyeste.get('UDVIKLING','')}",
                'v': nyeste.get('VURDERING', 'Ingen data')
            })
        else:
            # Hvis ingen data findes i scout-filen for dette ID
            tech_vals = [0.0] * len(radar_defs)

        return stats, scout_dict, tech_vals
    except Exception as e:
        # Hvis alt fejler, returnerer vi tomme værdier så appen ikke crasher på GitHub
        return {}, {'s': 'Datafejl', 'u': 'Datafejl', 'v': 'Datafejl', 'klub': 'Ukendt', 'pos': 'Ukendt'}, [0.0]*len(radar_defs)
