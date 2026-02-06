import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob (BETA)",
    page_icon="🚧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS LIMPO
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .popup-card { width: 220px; font-family: sans-serif; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .popup-img { width: 100%; height: 120px; object-fit: cover; }
    .popup-body { padding: 10px; background: white; }
    .popup-price { color: #27ae60; font-weight: 800; font-size: 15px; }
    .popup-title { font-size: 13px; font-weight: 600; color: #333; margin: 5px 0; line-height: 1.2; }
    .popup-btn { 
        display: block; background: #2e86de; color: white; text-align: center; 
        padding: 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 12px; margin-top: 8px;
    }
    
    /* Caixa de Feedback */
    .feedback-box {
        background-color: #f1f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4757;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & CACHE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

@st.cache_data(ttl=300) 
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        # Filtra lat!=0 e ordena
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(600).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

# --- 3. SIDEBAR: REPORTAR BUGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=50)
    st.title("Central Beta 🚧")
    st.write("Encontrou um erro? O mapa travou? O endereço está errado?")
    
    with st.form("bug_report"):
        nome_bug = st.text_input("Teu Nome")
        desc_bug = st.text_area("O que aconteceu?")
        if st.form_submit_button("🐛 Reportar Bug") and supabase and desc_bug:
            # Salva no supabase (usando a tabela alertas por enquanto ou crie uma nova 'bugs')
            supabase.table("alertas_clientes").insert({
                "user_id": "BUG_REPORT", 
                "termo_busca": desc_bug, 
                "ativo": False, 
                "plano": f"bug_de_{nome_bug}"
            }).execute()
            st.success("Obrigado! Vamos corrigir.")
            
    st.divider()
    st.info("Desenvolvido por Nicolas & Ana.")

# --- 4. HEADER & PESQUISA ---
c1, c2 = st.columns([1, 10])
with c2:
    st.title("Receita Imob | Versão Beta")
    st.markdown("""
    <div class="feedback-box">
        🚧 <b>Estamos em Testes!</b><br>
        O acesso é gratuito. Use à vontade, mas saiba que pode haver erros.
        Ajude-nos a melhorar reportando problemas na barra lateral.
    </div>
    """, unsafe_allow_html=True)

df_total = carregar_dados()

# Filtros (SEM BLOQUEIO PRO - TUDO LIBERADO NO BETA)
with st.container(border=True):
    c_search, c_type, c_btn = st.columns([3, 2, 1])
    with c_search:
        local_input = st.text_input("Para onde vamos?", placeholder="Ex: Aveiro, Porto, Lisboa...")
    with c_type:
        # Tudo liberado para teste
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1", "T2"])
    with c_btn:
        st.write(""); st.write("")
        filtrar = st.button("🔍 Buscar", use_container_width=True)

# --- 5. LÓGICA DO MAPA ---
map_center = [39.55, -7.85] 
zoom_start = 7
df_show = df_total.copy()

if local_input and not df_show.empty:
    df_show = df_show[df_show['endereco'].str.contains(local_input, case=False, na=False)]

if local_input:
    if not df_show.empty:
        map_center = [df_show['lat'].mean(), df_show['lon'].mean()]
        zoom_start = 12
    else:
        try:
            loc = Nominatim(user_agent="ri_beta").geocode(f"{local_input}, Portugal")
            if loc:
                map_center = [loc.latitude, loc.longitude]
                zoom_start = 13
                st.toast(f"Ainda sem imóveis em {local_input}, mas estamos monitorando!")
        except: pass

st.divider()

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)
marker_cluster = MarkerCluster().add_to(m)

if not df_show.empty:
    for _, row in df_show.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
            html = f"""
            <div class="popup-card">
                <img src="{img}" class="popup-img">
                <div class="popup-body">
                    <div class="popup-price">{preco}</div>
                    <div class="popup-title">{row.get('titulo','')[:45]}...</div>
                    <a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Anúncio</a>
                </div>
            </div>
            """
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="blue", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])

# --- 6. CAPTURA DE LEADS (FUTURO DINHEIRO) ---
st.write("---")
st.header("🚀 Quer garantir acesso VIP no lançamento oficial?")
st.write("Quem se inscrever agora vai manter o acesso com desconto vitalício quando o app ficar pago.")

with st.form("lista_espera"):
    col_lead1, col_lead2 = st.columns(2)
    with col_lead1:
        email_lead = st.text_input("Seu melhor E-mail")
    with col_lead2:
        cidade_lead = st.text_input("Cidade de Interesse")
        
    if st.form_submit_button("✅ Entrar na Lista de Fundadores") and email_lead and supabase:
        supabase.table("alertas_clientes").insert({
            "user_id": email_lead, 
            "termo_busca": cidade_lead, 
            "ativo": True, 
            "plano": "beta_founder"
        }).execute()
        st.balloons()
        st.success("Parabéns! Você é um Membro Fundador. Aproveite o beta grátis!")