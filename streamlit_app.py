import pandas as pd
import numpy as np

def calculate_cbam():
    # Caricamento database
    benchmarks = pd.read_csv('cbam_benchmarks_final.csv')
    defaults = pd.read_csv('cbam_defaults_final.csv')
    inputs = pd.read_csv('cbam_input_template.csv')

    results = []

    for _, row in inputs.iterrows():
        hs_code = str(row['hs_code'])
        country = row['country_origin']
        year = int(row['year'])
        actual_emissions = row['actual_direct_emissions_tco2_tn']
        route_tag = str(row['production_route_tag']).strip()
        volume = row['volume_imported_tn']
        ets_price = row['ets_price_eur']
        free_allowance_perc = row['free_allowance_perc'] / 100

        # 1. Determinazione Benchmark
        # Filtro per codice HS e Tag di produzione (A, B, C, D, etc.)
        bm_subset = benchmarks[benchmarks['CN_code'] == hs_code]
        
        # Logica Anno per Benchmark (1=2026-27, 2=2028-30)
        year_tag = '1' if year <= 2027 else '2'
        
        # Cerchiamo il benchmark che corrisponde al tag e al periodo
        match = bm_subset[
            (bm_subset['Main_Tag'] == route_tag) & 
            ((bm_subset['Year_Tag'] == year_tag) | (bm_subset['Year_Tag'].isna()) | (bm_subset['Year_Tag'] == ''))
        ]
        
        if match.empty:
            # Fallback su tag generico se specifico non trovato
            match = bm_subset[bm_subset['Main_Tag'] == route_tag]
            
        benchmark_val = match['Benchmark_Value'].values[0] if not match.empty else 0

        # 2. Determinazione Emissioni (Reali o Default)
        if pd.isna(actual_emissions) or actual_emissions == 0:
            # Cerca nei default per paese e codice HS
            def_row = defaults[(defaults['Country'] == country) & (defaults['Product CN Code'] == int(hs_code))]
            
            # Fallback su "Other Countries"
            if def_row.empty:
                def_row = defaults[(defaults['Country'].str.contains('Other Countries', case=False)) & 
                                   (defaults['Product CN Code'] == int(hs_code))]
            
            # Selezione colonna anno
            if year == 2026:
                col_name = '2026 Default Value (Including mark-up)'
            elif year == 2027:
                col_name = '2027 Default Value (Including mark-up)'
            else: # 2028+
                col_name = '2028 Default Value (Including mark-up)'
            
            emissions_to_use = def_row[col_name].values[0] if not def_row.empty else 0
            is_default_used = True
        else:
            emissions_to_use = actual_emissions
            is_default_used = False

        # 3. Calcolo Finale (Formula basata sul tuo esempio Excel)
        # Costo = Volume * (Emissioni - Benchmark * Free_Allowance) * Prezzo_ETS
        emissions_gap = max(0, emissions_to_use - (benchmark_val * free_allowance_perc))
        cbam_cost_per_tn = emissions_gap * ets_price
        total_to_pay = cbam_cost_per_tn * volume

        results.append({
            'HS Code': hs_code,
            'Year': year,
            'Emissions Used': emissions_to_use,
            'Is Default': is_default_used,
            'Benchmark Used': benchmark_val,
            'CBAM Cost/tn': cbam_cost_per_tn,
            'Total to Pay': total_to_pay
        })

    # Salvataggio risultati
    df_results = pd.DataFrame(results)
    df_results.to_csv('cbam_results.csv', index=False)
    print("Calcolo completato! Risultati salvati in 'cbam_results.csv'")

if __name__ == "__main__":
    calculate_cbam()