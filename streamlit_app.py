import streamlit as st
import pandas as pd
import os

# Configurazione Pagina
st.set_page_config(page_title="Calcolatore CBAM", layout="wide")

st.title("🌱 Applicazione Calcolo CBAM")
st.markdown("Strumento per il calcolo delle emissioni incorporate e dei certificati CBAM.")

# --- FUNZIONE DI CARICAMENTO DATI ---
@st.cache_data
def load_databases():
    if not os.path.exists('db_benchmarks.csv') or not os.path.exists('db_defaults.csv'):
        return None, None
    df_bm = pd.read_csv('db_benchmarks.csv')
    df_def = pd.read_csv('db_defaults.csv')
    return df_bm, df_def

df_bm, df_def = load_databases()

if df_bm is None:
    st.error("❌ Errore: File database non trovati!")
    st.info("Assicurati di aver caricato 'db_benchmarks.csv' e 'db_defaults.csv' nella cartella principale.")
    st.stop()

# --- INTERFACCIA DI INPUT ---
with st.sidebar:
    st.header("Parametri di Calcolo")
    hs_code = st.text_input("Codice HS (8 cifre)", "72024910")
    paese = st.text_input("Paese di Origine", "China")
    anno = st.selectbox("Anno di riferimento", [2026, 2027, 2028, 2029, 2030])
    volume = st.number_input("Volume importato (tonnellate)", value=1.0, min_value=0.0)
    
    st.subheader("Emissioni")
    tipo_emiss = st.radio("Tipo di Dati", ["Default", "Reali (Tag A)"])
    emiss_reali = 0.0
    if tipo_emiss == "Reali (Tag A)":
        emiss_reali = st.number_input("TCO2 dirette reali (per tn)", value=0.0)
        rotta_scelta = "A"
    else:
        rotta_scelta = st.selectbox("Production Route (Tag)", 
                                   ["B", "C", "D", "E", "F", "G", "H", "J"],
                                   help="B=Default, C-J=Rotte specifiche acciaio")

    ets_price = st.number_input("Prezzo ETS (€/tCO2)", value=80.0)
    free_all = st.slider("Free Allowance (%)", 0.0, 100.0, 97.5)

# --- LOGICA DI CALCOLO ---
if st.button("Calcola Risultato"):
    # 1. Trova Benchmark
    bm_hs = df_bm[df_bm['HS_Code'].astype(str) == str(hs_code)]
    periodo = '1' if anno <= 2027 else '2'
    
    match_bm = bm_hs[(bm_hs['Route_Tag'] == rotta_scelta) & (bm_hs['Year_Period'].astype(str) == periodo)]
    if match_bm.empty:
        match_bm = bm_hs[bm_hs['Route_Tag'] == rotta_scelta]
    
    valore_bm = match_bm['Benchmark_Value'].values[0] if not match_bm.empty else 0

    # 2. Trova Emissioni
    if emiss_reali > 0:
        valore_emissione = emiss_reali
        is_default = False
    else:
        filtro_def = df_def[(df_def['Country'] == paese) & (df_def['HS_Code'].astype(str) == str(hs_code))]
        if filtro_def.empty:
            filtro_def = df_def[(df_def['Country'].str.contains('Other', case=False)) & (df_def['HS_Code'].astype(str) == str(hs_code))]
        
        col_anno = 'V2026' if anno == 2026 else ('V2027' if anno == 2027 else 'V2028')
        valore_emissione = filtro_def[col_anno].values[0] if not filtro_def.empty else 0
        is_default = True

    # 3. Calcolo
    gap = max(0, valore_emissione - (valore_bm * (free_all / 100)))
    costo_tn = gap * ets_price
    totale = costo_tn * volume

    # --- MOSTRA RISULTATI ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Emissione Usata", f"{valore_emissione:.3f} tCO2/t", "Default" if is_default else "Reale")
    c2.metric("Benchmark", f"{valore_bm:.3f}")
    c3.metric("Totale da Pagare", f"€ {totale:,.2f}")

    st.info(f"Dettaglio: Gap emissioni di {gap:.3f} tCO2/t moltiplicato per {volume} tonnellate.")


