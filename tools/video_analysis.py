import streamlit as st
import pandas as pd
import os
import re

def vis_side(spillere):
    st.title("⚽ HIF Videoanalyse")

    # 1. Stier
    csv_path = 'data/matches.csv'
    video_dir = 'videos'

    # 2. Indlæs og rens CSV-data
    if os.path.exists(csv_path):
        try:
            # 'utf-8-sig' hjælper med danske tegn og fjerner Excel-skjulte tegn i starten
            df = pd.read_csv(csv_path, sep=None, engine='python', encoding='utf-8-sig')
            
            # Rens kolonnenavne (fjerner alt rod og gør dem store)
            df.columns = [re.sub(r'\W+', '', c).upper() for c in df.columns]
            
            # Lav en renset ID-kolonne til opslag (kun tal)
            if 'EVENT_WYID' in df.columns:
                df['RENS_ID'] = df['EVENT_WYID'].astype(str).apply(lambda x: "".join(re.findall(r'\d+', x)))
            else:
                st.error("Kunne ikke finde kolonnen 'EVENT_WYID' i din CSV.")
                st.write("Jeg fandt disse kolonner:", list(df.columns))
                return
        except Exception as e:
            st.error(f"Fejl ved indlæsning af CSV: {e}")
            return
    else:
        st.error(f"Fandt ikke matches.csv på stien: {csv_path}")
        return

    # 3. Håndter videofiler
    if os.path.exists(video_dir):
        video_filer = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
        if video_filer:
            # Vi bygger et map, der fjerner .mp4 FØR vi renser for usynlige tegn
            video_map = {}
            for f in video_filer:
                filnavn_uden_type = os.path.splitext(f)[0] # Fjerner .mp4 (og dermed 4-tallet)
                clean_id = "".join(re.findall(r'\d+', filnavn_uden_type)) # Fjerner usynlige tegn
                video_map[clean_id] = f

            # Dropdown menu med de rene ID'er fra din videomappe
            valgt_id = st.selectbox("Vælg sekvens (Event ID):", options=list(video_map.keys()))
            
            # 4. Find matchet i dine 5500 rækker
            match_data = df[df['RENS_ID'] == valgt_id]

            if not match_data.empty:
                row = match_data.iloc[0]
                
                # Overskrift med kampen
                st.markdown(f"### 🏟️ {row.get('MATCHLABEL', 'Kamp-data')}")
                
                # Tre kolonner med stats
                c1, c2, c3 = st.columns(3)
                
                # Vi bruger .get() så koden aldrig fejler, hvis en kolonne mangler
                res = row.get('RESULT', row.get('SCORE', 'N/A'))
                c1.metric("Resultat", res)
                
                xg_val = row.get('SHOTXG', 0.00)
                try:
                    c2.metric("xG", f"{float(xg_val):.2f}")
                except:
                    c2.metric("xG", xg_val)
                
                c3.metric("Kropsdel", row.get('SHOTBODYPART', 'N/A'))
                
                st.write(f"📅 **Dato:** {row.get('DATE', 'N/A')}  |  📍 **Side:** {row.get('SIDE', 'N/A')}")
                
                st.divider()
                
                # 5. Afspil videoen (vi bruger det originale filnavn fra mappet)
                video_sti = os.path.join(video_dir, video_map[valgt_id])
                st.video(video_sti)
            else:
                st.error(f"❌ ID {valgt_id} findes i din videomappe, men blev ikke fundet i de 5500 rækker i CSV'en.")
                # Fejlfinding: Vis hvad der faktisk står i CSV
                if st.checkbox("Vis diagnose-data fra CSV"):
                    st.write("Søgte efter ID:", valgt_id)
                    st.write("Første 5 rensede ID'er i CSV:", df['RENS_ID'].head().tolist())
        else:
            st.info(f"Mappen '{video_dir}' er tom. Upload dine .mp4 filer til GitHub.")
    else:
        st.error(f"Mappen '{video_dir}' blev ikke fundet i dit repository.")

# Denne funktion kaldes fra din hovedfil (HIF-dash.py)
