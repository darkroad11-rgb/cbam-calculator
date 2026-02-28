import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="CBAM Calculator PRO", layout="wide")

st.title("🌱 Calcolatore CBAM Intelligente")

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if os.path.exists('db_benchmarks.csv') and os.path.exists('db_defaults.csv'):
        return pd.read_csv('db_benchmarks.csv', dtype={'HS_Code': str}), pd.read_csv('db_defaults.csv', dtype={'HS_Code': str})
    return None, None

df_bm, df_def = load_data()

if df_bm is None:
    st.error("⚠️ Database non trovati! Assicurati di aver caricato 'db_benchmarks.csv' e 'db_defaults.csv'.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📦 Dati Importazione")
    hs_input = st.text_input("Codice HS (es. 72024910)", "72024910").strip()
    paese_input = st.text_input("Paese di Origine (es. China)", "China").strip()
    anno = st.selectbox("Anno di riferimento", [2026, 2027, 2028, 2029, 2030])
    volume = st.number_input("Volume importato (tonnellate)", value=1.0, min_value=0.0)

    st.header("⚙️ Emissioni")
    metodo = st.radio("Metodo:", ["Dati Reali (Tag A)", "Valori Default (Tag B)", "Rotte Acciaio (C-J)"])
    
    emiss_reali = 0.0
    tag_scelto = ""
    if metodo == "Dati Reali (Tag A)":
        emiss_reali = st.number_input("Inserisci TCO2/t reali", value=3.157, format="%.4f")
        tag_scelto = "A"
    elif metodo == "Valori Default (Tag B)":
        tag_scelto = "B"
    else:
        tag_scelto = st.selectbox("Seleziona Rotta:", ["C", "D", "E", "F", "G", "H", "J"])

    st.header("💰 Parametri Economici")
    prezzo_ets = st.number_input("Prezzo ETS (€)", value=75.0)
    fa_perc = st.number_input("Free Allowance Factor (%)", value=97.5)

# --- FUNZIONI DI RICERCA INTELLIGENTE ---

def get_benchmark(hs, tag, year):
    periodo = "1" if year <= 2027 else "2"
    # Filtro HS esatto
    subset = df_bm[df_bm['HS_Code'] == hs]
    
    # Se non trova l'HS a 8 cifre, prova a cercarlo come prefisso (6 o 4 cifre)
    if subset.empty:
        subset = df_bm[df_bm['HS_Code'].apply(lambda x: hs.startswith(str(x)))]

    if subset.empty: return 0.0

    # 1. Prova Match Tag + Anno
    match = subset[(subset['Tag'] == tag) & (subset['Year'].astype(str) == periodo)]
    if not match.empty: return match['Value'].values[0]

    # 2. Prova solo Tag
    match = subset[subset['Tag'] == tag]
    if not match.empty: return match['Value'].values[0]

    # 3. Fallback solo Anno (molto comune per ferro/acciaio)
    match = subset[subset['Year'].astype(str) == periodo]
    if not match.empty: return match['Value'].values[0]

    # 4. Ultima spiaggia: primo valore disponibile
    return subset['Value'].values[0]

def get_default_emission(hs, country, year):
    col_anno = f"V{min(year, 2028)}" # Usa 2028 per anni successivi
    
    # Liste di tentativi: Paese specifico e poi "Other Countries"
    paesi_da_provare = [country, "Other Countries and Territories", "Other"]
    
    for p in paesi_da_provare:
        # Cerca per lunghezze HS decrescenti (8, 6, 4)
        for length in [8, 6, 4]:
            hs_pref = hs[:length]
            match = df_def[(df_def['Country'].str.contains(p, case=False, na=False)) & 
                           (df_def['HS_Code'].astype(str) == hs_pref)]
            
            if not match.empty:
                val = match[col_anno].values[0]
                if pd.notna(val) and val > 0:
                    return val
    return 0.0

# --- CALCOLO E DISPLAY ---
if st.button("CALCOLA CBAM"):
    # Recupero valori
    bm_val = get_benchmark(hs_input, tag_scelto, anno)
    
    if metodo == "Dati Reali (Tag A)":
        em_val = emiss_reali
    else:
        em_val = get_default_emission(hs_input, paese_input, anno)

    # Formula
    fa_factor = fa_perc / 100
    gap = em_val - (bm_val * fa_factor)
    costo_unitario = max(0, gap * prezzo_ets)
    totale = costo_unitario * volume

    # Interfaccia Risultati
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Emissione (E)", f"{em_val:.4f} tCO2/t")
        st.caption(f"Fonte: {'Manuale' if metodo == 'Dati Reali (Tag A)' else 'Database Default'}")
        
    with col2:
        st.metric("Benchmark (B)", f"{bm_val:.4f}")
        st.caption(f"Tag usato: {tag_scelto if tag_scelto else 'Generale'} | Anno: {anno}")

    with col3:
        st.metric("TOTALE DA PAGARE", f"€ {totale:,.2f}", delta=f"€ {costo_unitario:.2f} / t", delta_color="inverse")

    # Spiegazione Formula
    st.info(f"**Calcolo effettuato:** ({em_val:.4f} - ({bm_val:.4f} * {fa_factor})) * {prezzo_ets} €/t = **€ {costo_unitario:.2f} per tonnellata**")

    if em_val == 0:
        st.warning("⚠️ Non ho trovato valori di default per questo codice HS. Controlla il codice o inserisci dati reali.")

