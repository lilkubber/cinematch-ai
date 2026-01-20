import streamlit as st
import requests
import json
import time
import re
from datetime import date, datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input {{ background-color: #222; color: white; border: 1px solid #444; }}
    .stButton>button {{ background: #E50914; color: white; border: none; height: 3em; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. GÜVENLİ VERİTABANI BAĞLANTISI ---
# Burası hata verirse site ÇÖKMEZ, sadece veritabanını devre dışı bırakır.
supabase = None
try:
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    # Veritabanı hatası olsa bile devam et, sadece loga yaz
    print(f"Veritabanı Bağlanamadı: {e}") 

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# --- 4. FONKSİYONLAR ---

def get_groq_response(prompt_text):
    """Test ettiğimiz ve çalıştığını bildiğimiz fonksiyon"""
    try:
        api_key = st.secrets["groq"]["api_key"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.5,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            st.error(f"API Hatası: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

def get_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url, timeout=3).json()
        if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
        return "https://via.placeholder.com/500x750?text=Resim+Yok"
    except: return "https://via.placeholder.com/500x750?text=Hata"

# --- 5. ÜYELİK İŞLEMLERİ (GÜVENLİ) ---
def login_ui():
    if supabase is None:
        st.warning("⚠️ Veritabanı bağlı değil, Misafir Modu aktif.")
        return

    if st.session_state.user:
        st.success(f"👤 {st.session_state.user['username']}")
        if st.button("Çıkış"):
            st.session_state.user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            e = st.text_input("E-Posta", key="le")
            p = st.text_input("Şifre", type="password", key="lp")
            if st.button("Giriş Yap"):
                try:
                    res = supabase.table("users").select("*").eq("email", e).eq("password", p).execute()
                    if res.data:
                        st.session_state.user = res.data[0]
                        st.rerun()
                    else: st.error("Hatalı bilgi.")
                except: st.error("Giriş hatası.")
        with tab2:
            u = st.text_input("Ad", key="ru")
            e_reg = st.text_input("E-Posta", key="re")
            p_reg = st.text_input("Şifre", type="password", key="rp")
            if st.button("Kayıt Ol"):
                try:
                    supabase.table("users").insert({"username":u, "email":e_reg, "password":p_reg}).execute()
                    st.success("Kayıt Başarılı!")
                except: st.error("Kayıt hatası.")

# --- 6. SAYFA DÜZENİ ---
with st.sidebar:
    st.title("🍿 CineMatch")
    login_ui()
    st.markdown("---")
    if not (st.session_state.user and st.session_state.user.get('is_premium')):
        st.info("💎 Premium: $0.99")

st.title("🍿 CineMatch AI")

# Form
c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Tümü", "Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with c2: detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu...")
mod = st.radio("Mod", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🧘 Yalnız"], horizontal=True)

if st.button("FİLM BUL 🚀", use_container_width=True):
    # Beyaz ekran olmaması için her şeyi try-except içine aldık
    try:
        with st.spinner("Film aranıyor..."):
            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {tur}. Details: {detay}. Context: {mod}.
            Return EXACTLY 3 movies. JSON Format:
            {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }} ] }}
            """
            
            json_str = get_groq_response(prompt)
            
            if json_str:
                # JSON Temizliği
                if "```json" in json_str: json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str: json_str = json_str.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_str)
                filmler = data.get("movies", [])
                
                if filmler:
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        with cols[i]:
                            st.image(get_poster(film['film_adi']), use_container_width=True)
                            st.subheader(f"{film['film_adi']}")
                            st.caption(f"⭐ {film['puan']} | 📅 {film['yil']}")
                            st.info(film['neden'])
                else:
                    st.warning("Uygun film bulunamadı.")
    except Exception as e:
        st.error(f"Bir hata oluştu ama sistem çökmedi: {e}")
