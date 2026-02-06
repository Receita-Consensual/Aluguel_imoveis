import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster # A mágica da performance
from streamlit_folium import st_folium

st.set_page_config(page_title="Receita Imob", page_icon="🏠", layout="wide")

# CSS para esconder menu e melhorar visual
st.markdown("""<style>.main {background-color:#f4f6f9;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# Header
col1, col2 = st.columns([1, 6])
with col1: st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=70)
with col2: 
    st.title("Receita Consensual Imob")
    st.caption("Inteligência Artificial aplicada ao Arrendamento")

# --- LÓGICA DO MAPA ---
st.subheader("🗺️ Mapa de Oportunidades")

df = pd.DataFrame()
if supabase:
    try:
        # Pega mais imóveis (500) porque o Cluster aguenta!
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(500).execute()
        df = pd.DataFrame(response.data)
    except:
        pass

if not df.empty:
    # Centraliza o mapa
    lat_c = df['lat'].mean() if 'lat' in df.columns else 39.5
    lon_c = df['lon'].mean() if 'lon' in df.columns else -8.0
    
    # Cria o mapa base (Mais limpo)
    m = folium.Map(location=[lat_c, lon_c], zoom_start=6, tiles="CartoDB positron")
    
    # CRIA O AGRUPAMENTO (CLUSTERING)
    marker_cluster = MarkerCluster().add_to(m)

    for index, row in df.iterrows():
        lat, lon = row.get('lat'), row.get('lon')
        if lat and lon and lat != 0:
            
            # HTML DO POPUP COM FOTO
            img_html = f"<img src='{row['imagem']}' width='100%' style='border-radius:4px; margin-bottom:5px;'>" if row.get('imagem') else ""
            
            html = f"""
            <div style='width: 220px; font-family: sans-serif;'>
                {img_html}
                <h5 style='margin:0; color:#2c3e50;'>{row.get('titulo', 'Imóvel')}</h5>
                <p style='margin:5px 0; font-size:12px; color:#7f8c8d;'>📍 {row.get('endereco', '')}</p>
                <a href='{row.get('link', '#')}' target='_blank' style='display:block; background:#ff4b4b; color:white; text-align:center; padding:8px; text-decoration:none; border-radius:4px; font-size:12px; font-weight:bold;'>Ver Anúncio Completo</a>
            </div>
            """
            
            folium.Marker(
                [lat, lon],
                popup=html,
                icon=folium.Icon(color="red", icon="home")
            ).add_to(marker_cluster) # Adiciona ao Cluster, não direto ao mapa

    st_folium(m, width=None, height=600)

else:
    st.info("Aguardando dados do satélite...")

# --- BARRA LATERAL (BUSCA GLOBAL) ---
st.sidebar.header("🔎 Nova Busca")
st.sidebar.info("Não achou o que queria no mapa? Peça para o Robô buscar agora.")

with st.sidebar.form("nova_busca"):
    nome = st.text_input("Nome")
    email = st.text_input("E-mail")
    # Aqui o usuário digita QUALQUER lugar
    busca_livre = st.text_input("O que você procura?", placeholder="Ex: T2 em Coimbra perto do Rio")
    
    enviar = st.form_submit_button("🚀 Iniciar Rastreamento")
    
    if enviar and supabase:
        if email and busca_livre:
            supabase.table("alertas_clientes").insert({
                "user_id": email,
                "termo_busca": busca_livre,
                "ativo": True,
                "plano": "site"
            }).execute()
            st.sidebar.success(f"O Robô começou a varrer a internet por: **{busca_livre}**")
            st.sidebar.warning("Volte em 15 minutos para ver os resultados no mapa!")