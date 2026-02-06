import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- 1. CONFIGURAÇÃO VISUAL PREMIUM ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS CUSTOMIZADO (CARD STYLE)
st.markdown("""
    <style>
    /* Fundo geral */
    .main {background-color: #f8f9fa;}
    
    /* Estilo dos Cards de Imóveis */
    .imovel-card {
        background-color: white;
        border-radius: 12px;
        padding: 0px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        transition: transform 0.2s;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }
    .imovel-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    .card-img {
        width: 100%;
        height: 180px;
        object-fit: cover;
    }
    .card-body {
        padding: 15px;
    }
    .price-tag {
        color: #2c3e50;
        font-weight: 800;
        font-size: 1.2rem;
    }
    .location-tag {
        color: #7f8c8d;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .btn-ver {
        display: block;
        width: 100%;
        padding: 10px;
        background-color: #ff5a5f; /* Cor Airbnb */
        color: white !important;
        text-align: center;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 10px;
    }
    .btn-ver:hover {
        background-color: #e04e53;
    }
    
    /* Ajuste do Mapa */
    iframe {border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# --- 3. BARRA LATERAL (FILTROS) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=60)
st.sidebar.title("Filtros")

# Filtro de Cidade (Pega do banco as cidades disponíveis)
cidades_disponiveis = ["Todas"]
df_raw = pd.DataFrame()

if supabase:
    try:
        # Pega tudo para filtrar no pandas (mais rápido para poucos dados < 10k)
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(1000).execute()
        df_raw = pd.DataFrame(response.data)
        
        if not df_raw.empty and 'endereco' in df_raw.columns:
            # Tenta extrair cidades unicas (simplificado)
            unique_cities = df_raw['endereco'].unique().tolist()
            cidades_disponiveis += unique_cities
    except:
        pass

filtro_cidade = st.sidebar.selectbox("Cidade / Zona", cidades_disponiveis)
filtro_preco = st.sidebar.slider("Preço Máximo (€)", 300, 3000, 1500, step=50)

st.sidebar.divider()
st.sidebar.markdown("### 💎 Acesso Premium")
st.sidebar.info("Receba alertas no e-mail assim que um imóvel novo aparecer.")
with st.sidebar.form("lead_magnet"):
    email_lead = st.text_input("Seu E-mail")
    zona_lead = st.text_input("Cidade de Interesse")
    btn_lead = st.form_submit_button("Ativar Alertas")
    if btn_lead and supabase and email_lead:
        supabase.table("alertas_clientes").insert({
            "user_id": email_lead, "termo_busca": zona_lead, "ativo": True, "plano": "site_sidebar"
        }).execute()
        st.sidebar.success("✅ Ativado!")

# --- 4. LÓGICA DE DADOS ---
df_filtrado = df_raw.copy()

if not df_filtrado.empty:
    # 1. Filtra Cidade
    if filtro_cidade != "Todas":
        df_filtrado = df_filtrado[df_filtrado['endereco'] == filtro_cidade]
    
    # 2. Filtra Preço (Remove quem tem preço 0 se quiser, ou mantem como "Consultar")
    # Vamos considerar preço 0 como "dentro" pois pode ser "Sob Consulta"
    df_filtrado = df_filtrado[
        (df_filtrado['preco'] <= filtro_preco) | (df_filtrado['preco'] == 0) | (df_filtrado['preco'].isnull())
    ]

# --- 5. LAYOUT PRINCIPAL ---

col_title, col_metric = st.columns([3, 1])
with col_title:
    st.title("Receita Imob Portugal")
    st.caption("Monitoramento em tempo real de Idealista, Imovirtual e CustoJusto.")
with col_metric:
    if not df_filtrado.empty:
        st.metric("Imóveis Encontrados", len(df_filtrado))

# ABA 1: MAPA
# ABA 2: GALERIA (CARDS)
tab_mapa, tab_galeria = st.tabs(["🗺️ Visualizar no Mapa", "🏡 Visualizar em Lista"])

with tab_mapa:
    if not df_filtrado.empty:
        # Calcula centro dinâmico baseado nos dados filtrados
        lat_mean = df_filtrado['lat'].mean()
        lon_mean = df_filtrado['lon'].mean()
        
        m = folium.Map(location=[lat_mean, lon_mean], zoom_start=6, tiles="CartoDB positron")
        
        # Auto-Zoom (Fit Bounds)
        sw = df_filtrado[['lat', 'lon']].min().values.tolist()
        ne = df_filtrado[['lat', 'lon']].max().values.tolist()
        if sw != ne: # Só ajusta se tiver pontos distantes
            m.fit_bounds([sw, ne])

        marker_cluster = MarkerCluster().add_to(m)

        for _, row in df_filtrado.iterrows():
            if row['lat'] and row['lon']:
                # Preço Formatado
                preco_txt = f"€ {row['preco']:,.0f}" if row.get('preco') and row['preco'] > 0 else "Sob Consulta"
                img_url = row.get('imagem') if row.get('imagem') else "https://via.placeholder.com/300x200.png?text=Sem+Foto"
                
                html = f"""
                <div style="width:200px">
                    <img src="{img_url}" style="width:100%; height:120px; object-fit:cover; border-radius:8px 8px 0 0;">
                    <div style="padding:5px">
                        <b>{preco_txt}</b><br>
                        <span style="font-size:12px">{row.get('titulo', '')[:40]}...</span><br>
                        <a href="{row.get('link')}" target="_blank" style="color:#ff5a5f; font-weight:bold; text-decoration:none;">Ver Anúncio</a>
                    </div>
                </div>
                """
                folium.Marker(
                    [row['lat'], row['lon']],
                    popup=html,
                    icon=folium.Icon(color="red", icon="home")
                ).add_to(marker_cluster)

        st_folium(m, width=None, height=500)
    else:
        st.warning("Nenhum imóvel encontrado com estes filtros.")

with tab_galeria:
    if not df_filtrado.empty:
        # Grid System (3 colunas)
        cols = st.columns(3)
        for i, (index, row) in enumerate(df_filtrado.iterrows()):
            # Imagem Placeholder se não tiver
            img = row.get('imagem')
            if not img or str(img) == 'nan': 
                img = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60" # Foto genérica bonita
            
            preco = f"€ {row['preco']:,.0f}" if row.get('preco') and row['preco'] > 0 else "Sob Consulta"
            titulo = row.get('titulo', 'Imóvel sem título')
            local = row.get('endereco', 'Portugal')
            link = row.get('link', '#')
            
            # HTML do Card
            card_html = f"""
            <div class="imovel-card">
                <img src="{img}" class="card-img">
                <div class="card-body">
                    <div class="price-tag">{preco}</div>
                    <div style="height: 3em; overflow: hidden; margin-bottom: 5px;">
                        <strong>{titulo}</strong>
                    </div>
                    <div class="location-tag">📍 {local}</div>
                    <a href="{link}" target="_blank" class="btn-ver">Ver Detalhes</a>
                </div>
            </div>
            """
            
            # Distribui nas colunas (0, 1, 2)
            with cols[i % 3]:
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("Ajuste os filtros para ver os imóveis.")