import streamlit as st
from supabase import create_client, Client
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuração da Página
st.set_page_config(page_title="Imóveis Aveiro | Receita Consensual", layout="wide")

st.title("🗺️ Monitor de Aluguéis - Aveiro")
st.write("Visão em tempo real de oportunidades capturadas pelo Bot.")

# 2. Conexão com Supabase (Pega as senhas dos 'Segredos' do Streamlit)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 3. Buscar Dados
rows = supabase.table("imoveis").select("*").execute()
df = pd.DataFrame(rows.data)

# 4. Mostrar Métricas
if not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Imóveis Encontrados", len(df))
    col1.metric("Preço Médio", f"€ {df['preco'].mean():.2f}")
    
    # 5. Criar o Mapa
    m = folium.Map(location=[40.6405, -8.6538], zoom_start=13) # Centro de Aveiro

    for index, row in df.iterrows():
        # HTML do Popup
        html = f"""
        <b>{row['titulo']}</b><br>
        💶 €{row['preco']}<br>
        <a href='{row['link']}' target='_blank'>Ver Anúncio</a>
        """
        folium.Marker(
            [row['lat'], row['lon']],
            popup=html,
            tooltip=f"€ {row['preco']}"
        ).add_to(m)

    # Renderiza o mapa no Streamlit
    st_folium(m, width=1200, height=500)
    
    # Mostra a tabela abaixo
    st.dataframe(df[['titulo', 'preco', 'endereco', 'link']])

else:
    st.warning("Nenhum imóvel encontrado no banco de dados ainda.")