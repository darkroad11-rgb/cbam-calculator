import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="CBAM Pro Calculator", layout="wide")

st.title("🌱 Calcolatore CBAM Intelligente")

# --- CARICAMENTO DATI ---
@st.cache_data
def load_data():
    if os.path.exists('db_benchmarks.csv') and os.path.exists('db_defaults.csv'):
        return pd.read_csv('db_benchmarks.csv'), pd.read_csv('db_defaults.csv')
    return None, None

df_bm, df_def = load_data()

if df_bm is None:
    st.error("Database non trovati! Carica 'db_benchmarks.csv' e 'db_defaults.csv'.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📦 Input Merce")
    hs_code = st.text_input("Codice HS (es. 72024910)", "72024910").strip()
    paese = st.text_input("Paese di Origine", "China").strip()
    anno = st.selectbox("Anno", [2026, 2027, 2028, 2029, 2030])
    volume = st.number_input("Volume (t)", value=1.0)

    st.header("⚙️ Metodo Emissioni")
    tipo_input = st.radio("Scegli:", ["Dati Reali (A)", "Valori Default (B)", "Rotta Specifica (C-J)"])
    
    emiss_reali = 0.0
    tag_scelto = ""
    if tipo_input == "Dati Reali (A)":
        emiss_reali = st.number_input("TCO2 reali", value=3.157, format="%.4f")
        tag_scelto = "A"
    elif tipo_input == "Valori Default (B)":
        tag_scelto = "B"
    else:
        tag_scelto = st.selectbox("Rotta:", ["C", "D", "E", "F", "G", "H", "J"])

    st.header("💰 Parametri")
    prezzo_ets = st.number_input("Prezzo ETS (€)", value=75.0)
    fa_default = 97.5 if anno <= 2026 else (95.0 if anno == 2027 else 90.0)
    free_all = st.number_input("Free Allowance (%)", value=fa_default)

# --- LOGICA DI RICERCA AUTOMATICA ---

def find_benchmark(hs, tag, year):
    periodo = "1" if year <= 2027 else "2"
    # Filtro HS
    subset = df_bm[df_bm['HS_Code'].astype(str) == hs]
    
    # 1. Prova match esatto: Tag + Periodo (es. A e 1)
    res = subset[(subset['Route_Tag'] == tag) & (subset['Year_Period'].astype(str) == periodo)]
    if not res.empty: return res['Benchmark_Value'].values[0]
    
    # 2. Prova solo Tag (es. solo A)
    res = subset[subset['Route_Tag'] == tag]
    if not res.empty: return res['Benchmark_Value'].values[0]
    
    # 3. Fallback sul Periodo (es. solo 1) - MOLTO COMUNE
    res = subset[subset['Year_Period'].astype(str) == periodo]
    if not res.empty: return res['Benchmark_Value'].values[0]
    
    return 0.0

def find_default(hs, country, year):
    col = 'V2026' if year == 2026 else ('V2027' if year == 2027 else 'V2028')
    
    # Ricerca a ritroso (8 cifre -> 6 -> 4)
    for length in [8, 6, 4]:
        hs_pref = hs[:length]
        # Cerco per paese
        match = df_def[(df_def['Country'] == country) & (df_def['HS_Code'].astype(str).str.startswith(hs_pref))]
        
        # Se trovo righe ma il valore è vuoto, o non trovo nulla, provo "Other Countries"
        if not match.empty and pd.notna(match[col].values[0]):
            return match[col].values[0]
            
    # Fallback finale su "Other Countries"
    match_other = df_def[(df_def['Country'].str.contains('Other', case=False)) & (df_def['HS_Code'].astype(str).str.startswith(hs[:4]))]
    if not match_other.empty:
        return match_other[col].values[0]
    
    return 0.0

# --- ESECUZIONE ---
if st.button("CALCOLA"):
    bm_val = find_benchmark(hs_code, tag_scelto, anno)
    
    if tipo_input == "Dati Reali (A)":
        emiss_val = emiss_reali
    else:
        emiss_val = find_default(hs_code, paese, anno)
    
    # Calcolo
    gap = emiss_val - (bm_val * (free_all / 100))
    totale = max(0, gap * prezzo_ets * volume)

    # UI
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Emissione applicata", f"{emiss_val:.3f}")
    c2.metric("Benchmark trovato", f"{bm_val:.3f}")
    c3.metric("Totale CBAM", f"€ {totale:,.2f}")
    
    if emiss_val == 0:
        st.warning("⚠️ Attenzione: Valore di default non trovato per questo codice HS/Paese.")
