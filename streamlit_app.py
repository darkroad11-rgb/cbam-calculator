import pandas as pd
import re
import os

# --- CONFIGURAZIONE NOMI FILE ---
# Assicurati che questi nomi corrispondano esattamente ai file nella tua cartella
FILE_BENCHMARKS = "carboneer-20251217-cbam-defaults-benchmarks.xlsx - cbam-benchmarks.csv"
FILE_DEFAULTS = "carboneer-20251217-cbam-defaults-benchmarks.xlsx - cbam-default-values.csv"
FILE_INPUT = "cbam_input_da_compilare.csv"

def pulisci_e_prepara_dati():
    print("Fase 1: Pulizia dati in corso...")
    
    # Pulizia Benchmarks
    df_bm = pd.read_csv(FILE_BENCHMARKS)
    cleaned_bm = []
    current_sector = "Unknown"
    
    for _, row in df_bm.iterrows():
        cn = str(row['CN code']).strip()
        val_b = str(row['Column B']).strip()
        
        if cn != 'nan' and val_b == 'nan':
            current_sector = cn
            continue
        if cn == 'nan' or val_b == 'nan': continue
        
        # Estrazione valore e tag (es: "0,666 (A)" -> 0.666, A)
        match = re.search(r"([0-9,]+)\s*(?:\((.*)\))?", val_b)
        if match:
            num = float(match.group(1).replace(',', '.'))
            tag_completo = match.group(2) if match.group(2) else ""
            
            # Gestione tag composti tipo F)(1
            main_tag = tag_completo
            year_tag = ""
            if ')(' in tag_completo:
                parts = tag_completo.split(')(')
                main_tag, year_tag = parts[0], parts[1]
            elif tag_completo in ['1', '2']:
                main_tag, year_tag = "", tag_completo
                
            cleaned_bm.append({
                'CN_code': cn, 'Value': num, 'Main_Tag': main_tag, 'Year_Tag': year_tag
            })
    
    df_bm_final = pd.DataFrame(cleaned_bm)

    # Pulizia Default Values
    df_def = pd.read_csv(FILE_DEFAULTS)
    cols_to_fix = ['2026 Default Value (Including mark-up)', 
                   '2027 Default Value (Including mark-up)', 
                   '2028 Default Value (Including mark-up)']
    
    for col in cols_to_fix:
        df_def[col] = pd.to_numeric(df_def[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    return df_bm_final, df_def

def crea_template_se_manca():
    if not os.path.exists(FILE_INPUT):
        template = pd.DataFrame({
            'hs_code': ['72024910'],
            'country_origin': ['China'],
            'year': [2026],
            'volume_tn': [1.0],
            'actual_emissions_tco2': [0], # Lascia 0 per usare i Default
            'production_route_tag': ['A'], # A, B, C, D, E, F, G, H, J
            'ets_price': [75.0],
            'free_allowance_perc': [97.5]
        })
        template.to_csv(FILE_INPUT, index=False)
        print(f"--> Creato file '{FILE_INPUT}'. Compilalo con i tuoi dati e riavvia lo script.")
        return True
    return False

def esegui_calcolo(df_bm, df_def):
    print("Fase 2: Calcolo in corso...")
    inputs = pd.read_csv(FILE_INPUT)
    results = []

    for _, row in inputs.iterrows():
        hs = str(row['hs_code'])
        yr = int(row['year'])
        country = row['country_origin']
        route = str(row['production_route_tag'])
        
        # 1. Trova Benchmark
        yr_tag = '1' if yr <= 2027 else '2'
        bm_match = df_bm[(df_bm['CN_code'] == hs) & (df_bm['Main_Tag'] == route)]
        
        # Filtro per anno se esiste
        bm_yr = bm_match[bm_match['Year_Tag'] == yr_tag]
        if not bm_yr.empty:
            bm_val = bm_yr['Value'].values[0]
        elif not bm_match.empty:
            bm_val = bm_match['Value'].values[0]
        else:
            bm_val = 0

        # 2. Trova Emissioni (Reali o Default)
        if row['actual_emissions_tco2'] > 0:
            emiss_val = row['actual_emissions_tco2']
            tipo = "Reale"
        else:
            col_anno = f'{yr} Default Value (Including mark-up)'
            def_match = df_def[(df_def['Country'] == country) & (df_def['Product CN Code'].astype(str) == hs)]
            if def_match.empty: # Fallback Other Countries
                def_match = df_def[(df_def['Country'].str.contains('Other')) & (df_def['Product CN Code'].astype(str) == hs)]
            
            emiss_val = def_match[col_anno].values[0] if not def_match.empty else 0
            tipo = "Default"

        # 3. Formula CBAM
        gap = max(0, emiss_val - (bm_val * (row['free_allowance_perc']/100)))
        costo_totale = gap * row['ets_price'] * row['volume_tn']

        results.append({
            'HS Code': hs, 'Paese': country, 'Tipo Emissione': tipo,
            'Valore Emissione': emiss_val, 'Benchmark': bm_val, 'Totale da Pagare (€)': costo_totale
        })

    pd.DataFrame(results).to_csv("risultati_cbam.csv", index=False)
    print("--> Fatto! Risultati salvati in 'risultati_cbam.csv'")

# ESECUZIONE
if __name__ == "__main__":
    if not os.path.exists(FILE_BENCHMARKS) or not os.path.exists(FILE_DEFAULTS):
        print("ERRORE: I file Excel/CSV originali non sono nella cartella!")
    else:
        df_bm, df_def = pulisci_e_prepara_dati()
        if not crea_template_se_manca():
            esegui_calcolo(df_bm, df_def)
