import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PROFISSIONAL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Login Box */
    .login-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dcdcdc;
        margin-bottom: 20px;
    }
    
    /* Badge PRO */
    .badge-pro {
        background-color: #ffd700;
        color: black;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Botão Principal */
    .stButton>button {
        background-color: #000;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & SESSÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# Inicializa variaveis de sessão (Memória do navegador)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ''
if 'user_plan' not in st.session_state:
    st.session_state['user_plan'] = 'free'

# --- 3. BARRA LATERAL (LOGIN & CONTA) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)

if not st.session_state['logged_in']:
    # --- TELA DE LOGIN ---
    st.sidebar.header("🔐 Área do Membro")
    with st.sidebar.form("login_form"):
        email_login = st.text_input("E-mail")
        senha_login = st.text_input("Senha", type="password")
        btn_entrar = st.form_submit_button("Entrar")
        
        if btn_entrar and supabase:
            try:
                # Verifica no banco
                response = supabase.table("usuarios").select("*").eq("email", email_login).eq("senha", senha_login).execute()
                if response.data:
                    user = response.data[0]
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = user['nome']
                    st.session_state['user_plan'] = user['plano']
                    st.rerun() # Recarrega a página logado
                else:
                    st.error("E-mail ou senha incorretos.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
    
    st.sidebar.markdown("---")
    st.sidebar.info("Não tem conta? Fale com o suporte para assinar o plano PRO.")

else:
    # --- TELA LOGADO (PERFIL) ---
    st.sidebar.success(f"Bem-vindo, {st.session_state['user_name']}!")
    
    if st.session_state['user_plan'] == 'pro':
        st.sidebar.markdown("<span class='badge-pro'>💎 MEMBRO PRO</span>", unsafe_allow_html=True)
        st.sidebar.write("✅ Filtros Avançados: Ativo")
        st.sidebar.write("✅ Alertas em Tempo Real: Ativo")
    else:
        st.sidebar.warning("Plano Gratuito")
        st.sidebar.button("💎 Quero ser PRO")

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.session_state['user_plan'] = 'free'
        st.rerun()

# --- 4. HEADER & BANNER ---
col_head1, col_head2 = st.columns([1, 12])
with col_head2:
    st.title("Receita Imob")
    if st.session_state['user_plan'] != 'pro':
        st.caption("Versão Gratuita - Atualizada a cada 30min")
    else:
        st.caption("⚡ Versão PRO - Monitoramento em Tempo Real Ativo")

# Banner só aparece para quem NÃO é Pro
if st.session_state['user_plan'] != 'pro':
    st.info("🔒 Você está visualizando o modo visitante. Assine o PRO para liberar filtros múltiplos e alertas instantâneos.")

# --- 5. ÁREA DE BUSCA INTELIGENTE ---
with st.container(border=True):
    c1, c2, c3 = st.columns([4, 2, 1])
    
    with c1:
        local_busca = st.text_input("📍 Onde você quer morar?", placeholder="Ex: Porto, Aveiro, Lisboa...")
    
    with c2:
        # LÓGICA DE BLOQUEIO DO FILTRO
        opcoes_tipo = ["Apartamento T1", "Apartamento T2", "Apartamento T3", "Quarto", "Casa"]
        
        filtro_tipo = st.multiselect(
            "Tipo de Imóvel", 
            opcoes_tipo,
            default=["Apartamento T1"]
        )
        
        # AQUI É O PULO DO GATO: Se não for PRO, bloqueia
        if len(filtro_tipo) > 1 and st.session_state['user_plan'] != 'pro':
            st.toast("🔒 Multi-seleção é exclusivo para assinantes PRO.", icon="🚫")
            filtro_tipo = [filtro_tipo[0]] # Força a ficar só com 1
            st.warning("⚠️ Limite Grátis: Apenas 1 tipo por vez.")

    with c3:
        st.write("") 
        st.write("") 
        buscar = st.button("🔍 Buscar")

# --- 6. DADOS E MAPA ---
df = pd.DataFrame()
map_center = [39.5, -8.0]
zoom_start = 7

if supabase:
    try:
        query = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(800)
        response = query.execute()
        df = pd.DataFrame(response.data)
        
        # Filtro de Texto (Local)
        if local_busca and not df.empty:
            df = df[df['endereco'].str.contains(local_busca, case=False, na=False)]
            # Ajusta zoom se achou algo
            if not df.empty:
                map_center = [df['lat'].mean(), df['lon'].mean()]
                zoom_start = 12
            else:
                # Se não achou no banco, tenta geocoding para centralizar o mapa vazio lá
                try:
                    loc = Nominatim(user_agent="rimob").geocode(f"{local_busca}, Portugal")
                    if loc:
                        map_center = [loc.latitude, loc.longitude]
                        zoom_start = 13
                except: pass

    except Exception as e:
        st.error(f"Erro de conexão: {e}")

# Renderiza Mapa
st.divider()

if not df.empty:
    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="CartoDB positron")
    Fullscreen().add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        if row['lat'] and row['lon'] and row['lat'] != 0:
            # Foto
            img_url = row.get('imagem')
            if not img_url: img_url = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            
            # Preço
            preco = row.get('preco', 0)
            preco_fmt = f"€ {preco:,.0f}" if preco > 0 else "Sob Consulta"
            
            # Popup
            html = f"""
            <div style="width:200px; font-family:sans-serif;">
                <img src="{img_url}" style="width:100%; height:120px; object-fit:cover; border-radius:8px 8px 0 0;">
                <div style="padding:8px;">
                    <div style="color:#2c3e50; font-weight:bold;">{preco_fmt}</div>
                    <div style="font-size:12px; margin-top:4px;">{row.get('titulo', '')[:40]}...</div>
                    <a href="{row.get('link')}" target="_blank" style="display:block; background:#000; color:fff; text-align:center; padding:6px; border-radius:4px; text-decoration:none; margin-top:8px; font-size:11px;">Ver Detalhes</a>
                </div>
            </div>
            """
            folium.Marker(
                [row['lat'], row['lon']],
                popup=html,
                icon=folium.Icon(color="black", icon="home", prefix="fa")
            ).add_to(marker_cluster)

    st_folium(m, width=None, height=600)
    st.caption(f"Exibindo {len(df)} resultados.")
else:
    st.info("Nenhum imóvel encontrado nesta região no momento.")

# --- 7. ÁREA PREMIUM (ALERTAS) ---
st.divider()
st.header("🔔 Alertas Automáticos")

if st.session_state['user_plan'] == 'pro':
    # VISÃO DO PRO: Painel de Controle
    st.success("✅ Seu plano PRO permite criar alertas ilimitados.")
    with st.form("alerta_pro"):
        c_a1, c_a2 = st.columns(2)
        with c_a1: st.text_input("Qual zona monitorar?", placeholder="Ex: Matosinhos Sul")
        with c_a2: st.multiselect("Tipos", ["T1", "T2", "T3"], default=["T2"])
        if st.form_submit_button("Criar Novo Robô de Alerta"):
            st.success("Robô configurado! Você receberá e-mails assim que encontrarmos.")
            # Aqui conectaria ao Supabase tabela alertas
            
else:
    # VISÃO DO FREE: Propaganda
    st.write("Deseja ser avisado quando um imóvel aparecer aqui?")
    c_l1, c_l2 = st.columns([3,1])
    with c_l1: st.text_input("Seu E-mail", placeholder="seu@email.com", disabled=True, help="Disponível apenas para PRO")
    with c_l2: st.button("Destravar Alertas", disabled=True)
    st.caption("🔒 Faça login como PRO para ativar esta função.")