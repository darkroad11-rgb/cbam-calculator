import pandas as pd
import os

# --- LOGICA DI CALCOLO CBAM ---

def calcola_cbam():
    # 1. Caricamento Dati
    try:
        df_bm = pd.read_csv('db_benchmarks.csv')
        df_def = pd.read_csv('db_defaults.csv')
        inputs = pd.read_csv('template_input.csv')
    except FileNotFoundError:
        print("Errore: Assicurati che db_benchmarks.csv, db_defaults.csv e template_input.csv siano nella cartella.")
        return

    risultati = []

    for _, row in inputs.iterrows():
        hs = str(row['hs_code']).strip()
        paese = row['country_origin']
        anno = int(row['year'])
        qta = row['quantity_tons']
        emiss_reali = row['actual_emissions_tco2_t']
        rotta = str(row['production_route_letter']).strip().upper()
        prezzo_ets = row['ets_price_eur']
        free_allowance = row['free_allowance_perc'] / 100

        # --- A. DETERMINAZIONE BENCHMARK ---
        # Filtro per codice HS e rotta (A, B, C, D, etc.)
        bm_hs = df_bm[df_bm['HS_Code'].astype(str) == hs]
        
        # Gestione Anno per Benchmark: (1) per 2026-27, (2) per 2028-30
        periodo = '1' if anno <= 2027 else '2'
        
        # Cerco il benchmark specifico per rotta e periodo
        match_bm = bm_hs[(bm_hs['Route_Tag'] == rotta) & (bm_hs['Year_Period'].astype(str) == periodo)]
        if match_bm.empty:
            # Fallback se non c'è distinzione di anno
            match_bm = bm_hs[bm_hs['Route_Tag'] == rotta]
        
        valore_bm = match_bm['Benchmark_Value'].values[0] if not match_bm.empty else 0

        # --- B. DETERMINAZIONE EMISSIONI ---
        # Se emissione reale è 0 o vuota, cerco nei default
        if pd.isna(emiss_reali) or emiss_reali <= 0:
            # Cerco per Paese e Codice HS
            filtro_def = df_def[(df_def['Country'] == paese) & (df_def['HS_Code'].astype(str) == hs)]
            
            # Fallback: Se non trovo il paese, cerco "Other Countries"
            if filtro_def.empty:
                filtro_def = df_def[(df_def['Country'].str.contains('Other', case=False)) & (df_def['HS_Code'].astype(str) == hs)]
            
            # Scelta colonna anno (2026, 2027, 2028+)
            col_anno = 'V2026' if anno == 2026 else ('V2027' if anno == 2027 else 'V2028')
            
            valore_emissione = filtro_def[col_anno].values[0] if not filtro_def.empty else 0
            tipo_emiss = "Default"
        else:
            valore_emissione = emiss_reali
            tipo_emiss = "Reale"

        # --- C. CALCOLO COSTO ---
        # Formula: (Emissioni - (Benchmark * Free Allowance)) * Prezzo ETS * Quantità
        gap = max(0, valore_emissione - (valore_bm * free_allowance))
        costo_totale = gap * prezzo_ets * qta

        risultati.append({
            'HS Code': hs,
            'Paese': paese,
            'Anno': anno,
            'Tipo Emissione': tipo_emiss,
            'Emissione Usata': valore_emissione,
            'Benchmark Usato': valore_bm,
            'Costo Totale CBAM (€)': round(costo_totale, 2)
        })

    # Salvataggio Risultati
    df_output = pd.DataFrame(risultati)
    df_output.to_csv('risultati_finali_cbam.csv', index=False)
    print("Calcolo completato! Apri 'risultati_finali_cbam.csv' per vedere i dettagli.")

if __name__ == "__main__":
    calcola_cbam()

