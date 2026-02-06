import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuração Visual
st.set_page_config(
    page_title="Receita Imob | Inteligência Imobiliária",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo CSS
st.markdown("""
    <style>
    .main {background-color: #f9f9f9;}
    h1 {color: #2c3e50;}
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão Segura
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- CABEÇALHO ---
col_logo, col_text = st.columns([1, 4])
with col_logo:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=80)
with col_text:
    st.title("Receita Imob")
    st.markdown("**Encontramos o seu imóvel antes de ele ser anunciado.** Nossa inteligência artificial monitora o mercado 24h por dia.")

st.divider()

# --- COLUNAS PRINCIPAIS ---
col_mapa, col_premium = st.columns([2, 1])

# --- ÁREA 1: O MAPA ---
with col_mapa:
    st.subheader("📍 Monitoramento em Tempo Real")
    
    df = pd.DataFrame()
    if supabase:
        try:
            # Pega os últimos 100 imóveis para o mapa não ficar pesado
            response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(100).execute()
            df = pd.DataFrame(response.data)
        except:
            pass

    if not df.empty:
        # Centraliza o mapa
        lat_centro = df['lat'].mean() if 'lat' in df.columns and len(df) > 0 else 39.5
        lon_centro = df['lon'].mean() if 'lon' in df.columns and len(df) > 0 else -8.0
        
        m = folium.Map(location=[lat_centro, lon_centro], zoom_start=7)

        for index, row in df.iterrows():
            lat, lon = row.get('lat'), row.get('lon')
            # Só plota se tiver coordenadas válidas (diferente de 0)
            if lat and lon and lat != 0:
                html = f"""
                <div style='font-family: Arial; width: 180px;'>
                    <h4 style='margin:0; color:#2c3e50;'>{row.get('titulo', 'Imóvel')}</h4>
                    <p style='margin:5px 0; font-size:12px;'>📍 {row.get('endereco', '')}</p>
                    <p style='margin:5px 0; font-weight:bold; color:#27ae60;'>€ {row.get('preco', 'Sob Consulta')}</p>
                    <a href='{row.get('link', '#')}' target='_blank' style='display:block; background:#ff4b4b; color:white; text-align:center; padding:5px; text-decoration:none; border-radius:4px; font-size:12px;'>Ver Detalhes</a>
                </div>
                """
                folium.Marker(
                    [lat, lon],
                    popup=html,
                    icon=folium.Icon(color="red", icon="home")
                ).add_to(m)

        st_folium(m, width=None, height=500)
    else:
        st.info("📡 Calibrando satélites... O mapa será atualizado assim que o Bot encontrar novos imóveis.")

# --- ÁREA 2: CADASTRO PREMIUM (EMAIL) ---
with col_premium:
    st.container(border=True)
    st.markdown("### 💎 Receba Alertas por E-mail")
    st.write("Selecione múltiplas opções e receba tudo na sua caixa de entrada.")
    
    with st.form("form_cadastro"):
        nome = st.text_input("Seu Nome")
        email = st.text_input("Seu Melhor E-mail")
        zona = st.text_input("Cidade ou Bairro", placeholder="Ex: Figueira da Foz")
        
        # MUDANÇA AQUI: Multiselect em vez de Selectbox
        tipos = st.multiselect(
            "O que procura? (Selecione vários)", 
            ["Apartamento T1", "Apartamento T2", "Apartamento T3", "Apartamento T4+", "Casa/Moradia", "Quarto"],
            default=["Apartamento T2"]
        )
        
        btn_assinar = st.form_submit_button("🚀 Ativar Alertas Personalizados")
        
        if btn_assinar and supabase:
            if email and zona and tipos:
                # Junta a lista ["T2", "T3"] numa string "Apartamento T2 Apartamento T3 Figueira da Foz"
                tipos_texto = " ".join(tipos)
                termo_busca = f"{tipos_texto} {zona}"
                
                dados = {
                    "user_id": email,
                    "termo_busca": termo_busca,
                    "plano": "waitlist",
                    "ativo": True
                }
                try:
                    supabase.table("alertas_clientes").insert(dados).execute()
                    st.success(f"Configurado! Vamos buscar por **{tipos_texto}** em **{zona}**.")
                    st.balloons()
                except Exception as e:
                    st.error("Erro ao cadastrar. Verifique se o e-mail já está na lista.")
            else:
                st.warning("Preencha todos os campos para garantirmos a melhor busca.")

# --- RODAPÉ ---
st.markdown("---")
st.markdown("<center><small>Receita Consensual Imob © 2026</small></center>", unsafe_allow_html=True)