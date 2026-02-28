import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="CBAM Calculator PRO", layout="wide")

st.title("🌱 Calcolatore CBAM Professionale")

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if os.path.exists('db_benchmarks.csv') and os.path.exists('db_defaults.csv'):
        return pd.read_csv('db_benchmarks.csv'), pd.read_csv('db_defaults.csv')
    return None, None

df_bm, df_def = load_data()

if df_bm is None:
    st.error("File database non trovati! Assicurati di aver caricato i file .csv")
    st.stop()

# --- SIDEBAR: INPUT DATI ---
with st.sidebar:
    st.header("1. Informazioni Merce")
    hs_code = st.text_input("Codice HS (es. 72024910)", "72024910")
    paese = st.text_input("Paese di Origine", "China")
    anno = st.selectbox("Anno della dichiarazione", [2026, 2027, 2028, 2029, 2030])
    volume = st.number_input("Volume importato (tonnellate)", value=1.0)

    st.header("2. Emissioni e Rotte")
    metodo = st.radio("Metodo di calcolo", ["Dati Reali (Tag A)", "Valori di Default (Tag B)", "Rotta di Produzione Specifica (C-J)"])
    
    emiss_reali = 0.0
    rotta_tag = ""
    
    if metodo == "Dati Reali (Tag A)":
        emiss_reali = st.number_input("Emissioni Dirette Reali (tCO2/t)", value=3.157, format="%.4f")
        rotta_tag = "A"
    elif metodo == "Valori di Default (Tag B)":
        rotta_tag = "B"
    else:
        rotta_tag = st.selectbox("Seleziona Rotta", ["C", "D", "E", "F", "G", "H", "J"])

    st.header("3. Parametri Finanziari")
    prezzo_ets = st.number_input("Prezzo Medio ETS (€)", value=75.0)
    # Calcolo automatico Free Allowance se non inserita manualmente
    fa_default = 97.5 if anno <= 2026 else (95.0 if anno == 2027 else 90.0)
    free_all_perc = st.number_input("Free Allowance Factor (%)", value=fa_default)
    prezzo_pagato_estero = st.number_input("Prezzo del carbonio già pagato all'estero (€)", value=0.0)

# --- LOGICA DI CALCOLO ---
if st.button("ESEGUI CALCOLO"):
    # A. Identificazione Benchmark corretto
    periodo_tag = "1" if anno <= 2027 else "2"
    
    # Filtro per codice HS
    bm_subset = df_bm[df_bm['HS_Code'].astype(str) == str(hs_code)]
    
    # Cerco il benchmark che corrisponde alla rotta (A, B o C-J) e al periodo (1 o 2)
    match = bm_subset[(bm_subset['Route_Tag'] == rotta_tag) & (bm_subset['Year_Period'].astype(str) == periodo_tag)]
    
    # Fallback se non trova il periodo specifico
    if match.empty:
        match = bm_subset[bm_subset['Route_Tag'] == rotta_tag]
    
    # Se ancora vuoto (es. il codice HS non ha tag A/B ma solo 1/2), prendo quello per anno
    if match.empty:
        match = bm_subset[bm_subset['Year_Period'].astype(str) == periodo_tag]
        
    valore_bm = match['Benchmark_Value'].values[0] if not match.empty else 0.0

    # B. Identificazione Emissioni
    if metodo == "Dati Reali (Tag A)" or (metodo == "Rotta di Produzione Specifica (C-J)" and emiss_reali > 0):
        valore_emiss = emiss_reali
    else:
        # Cerco nei default per paese e codice HS
        def_match = df_def[(df_def['Country'] == paese) & (df_def['HS_Code'].astype(str) == str(hs_code))]
        if def_match.empty:
            def_match = df_def[(df_def['Country'].str.contains('Other', case=False)) & (df_def['HS_Code'].astype(str) == str(hs_code))]
        
        col_anno = 'V2026' if anno == 2026 else ('V2027' if anno == 2027 else 'V2028')
        valore_emiss = def_match[col_anno].values[0] if not def_match.empty else 0.0

    # C. FORMULA CORRETTA (Allineata al tuo Excel)
    # CBAM = [Emissioni - (Benchmark * Free Allowance)] * Prezzo ETS - Prezzo Pagato
    free_allowance_factor = free_all_perc / 100
    gap_emissioni = valore_emiss - (valore_bm * free_allowance_factor)
    costo_certificati = max(0, gap_emissioni * prezzo_ets)
    totale_da_pagare = (costo_certificati * volume) - prezzo_pagato_estero

    # --- RISULTATI ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Emissione applicata", f"{valore_emiss:.3f} tCO2/t")
        st.caption(f"Metodo: {metodo}")
    
    with col2:
        st.metric("Benchmark usato", f"{valore_bm:.3f}")
        st.caption(f"Tag: {rotta_tag} | Periodo: {periodo_tag}")
        
    with col3:
        st.metric("TOTALE DA PAGARE", f"€ {max(0, totale_da_pagare):,.2f}")
        st.caption(f"Per {volume} tonnellate")

    st.success(f"**Dettaglio Formula:** ({valore_emiss:.3f} - ({valore_bm:.3f} * {free_allowance_factor})) * {prezzo_ets} = € {costo_certificati:.2f} per tonnellata.")



