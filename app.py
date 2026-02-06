import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuração da Página
st.set_page_config(page_title="Receita Consensual | Imóveis", layout="wide", page_icon="🏢")

# 2. Conexão Supabase
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# --- BARRA LATERAL (ÁREA DO CLIENTE) ---
st.sidebar.title("💎 Área Premium")
st.sidebar.write("Configure seus alertas e receba novidades no Telegram.")

with st.sidebar.form("form_alerta"):
    st.write("### Criar Novo Alerta")
    
    # Inputs do usuário
    user_telegram = st.text_input("Seu ID do Telegram", help="Mande /start no nosso bot para saber seu ID")
    local_desejado = st.text_input("Onde você quer morar?", value="Aveiro Centro")
    tipo_imovel = st.selectbox("Tipo", ["Apartamento T1", "Apartamento T2", "Quarto", "Casa"])
    
    # Botão de salvar
    submitted = st.form_submit_button("🔔 Ativar Alerta")
    
    if submitted and supabase:
        if user_telegram and local_desejado:
            termo_final = f"{tipo_imovel} {local_desejado}"
            
            try:
                # Salva na tabela que o Bot lê
                dados = {
                    "user_id": user_telegram, 
                    "termo_busca": termo_final, 
                    "plano": "site_user",
                    "ativo": True
                }
                supabase.table("alertas_clientes").insert(dados).execute()
                st.success(f"Sucesso! O Robô vai buscar '{termo_final}' para você.")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("Preencha o ID e o Local.")

st.sidebar.divider()
st.sidebar.info("💡 **Dica:** Use o mapa ao lado para ver o que já encontramos hoje.")

# --- ÁREA PRINCIPAL (MAPA GRATUITO) ---
st.title("🗺️ Mapa de Oportunidades - Tempo Real")

if not supabase:
    st.error("Erro de conexão com o banco de dados. Verifique as chaves.")
    st.stop()

# Busca imóveis no banco
try:
    response = supabase.table("imoveis").select("*").execute()
    df = pd.DataFrame(response.data)
except:
    df = pd.DataFrame()

if not df.empty:
    # Métricas no topo
    col1, col2, col3 = st.columns(3)
    col1.metric("Imóveis Monitorados", len(df))
    col1.metric("Preço Médio", f"€ {df['preco'].mean():.0f}" if 'preco' in df.columns else "N/A")
    col2.metric("Última Atualização", "Agora mesmo")

    # Mapa
    # Tenta centralizar onde tem mais imóveis ou em Aveiro padrão
    lat_centro = df['lat'].mean() if 'lat' in df.columns else 40.6405
    lon_centro = df['lon'].mean() if 'lon' in df.columns else -8.6538
    
    m = folium.Map(location=[lat_centro, lon_centro], zoom_start=12)

    # Adiciona os pontos
    for index, row in df.iterrows():
        lat = row.get('lat', 0)
        lon = row.get('lon', 0)
        
        if lat != 0 and lon != 0:
            html = f"""
            <div style='font-family: sans-serif; width: 200px;'>
                <b>{row.get('titulo', 'Imóvel')}</b><br>
                📍 {row.get('endereco', '')}<br>
                <a href='{row.get('link', '#')}' target='_blank' style='background-color:#4CAF50; color:white; padding:5px; text-decoration:none; display:block; text-align:center; margin-top:5px; border-radius:4px;'>Ver Anúncio</a>
            </div>
            """
            
            folium.Marker(
                [lat, lon],
                popup=html,
                icon=folium.Icon(color="blue", icon="home")
            ).add_to(m)

    st_folium(m, width=None, height=600)
    
    st.write("### Últimos Encontrados")
    st.dataframe(df[['titulo', 'link', 'endereco']], use_container_width=True)

else:
    st.info("O Robô está caçando imóveis... Volte em alguns minutos ou configure um alerta na barra lateral!")