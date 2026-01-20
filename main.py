import streamlit as st
import requests
import json
import time
from datetime import date, datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input {{ background-color: #222; color: white; border: 1px solid #444; }}
    .stButton>button {{ background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. GÜVENLİ KÜTÜPHANE YÜKLEME ---
# Burası çok önemli: Supabase'i burada import ediyoruz.
# Eğer yüklü değilse site çökmez, sadece uyarı verir.
supabase = None
try:
    from supabase import create_client
    if "supabase" in st.secrets:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        supabase = create_client(url, key)
except ImportError:
    st.warning("⚠️ 'supabase' kütüphanesi bulunamadı. Lütfen requirements.txt dosyasına 'supabase' ekleyin.")
except Exception as e:
    st.warning(f"⚠️ Veritabanı bağlantı hatası: {e}")

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# --- 4. FONKSİYONLAR ---
def get_groq_response(prompt):
    try:
        if "groq" not in st.secrets:
            st.error("Secrets ayarlarında [groq] anahtarı yok!")
            return None
        key = st.secrets["groq"]["api_key"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None
    except Exception as e:
        st.error(f"API Hatası: {e}")
        return None

def get_poster(movie_name):
    try:
        if "tmdb" in st.secrets:
            key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={key}&query={movie_name}"
            res = requests.get(url, timeout=2).json()
            if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except: pass
    return "https://via.placeholder.com/500x750?text=Poster+Yok"

# --- 5. ÜYELİK SİSTEMİ ---
def login_ui():
    if not supabase:
        st.info("Veritabanı bağlantısı yok, Misafir Modu aktif.")
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
                except: st.error("Giriş başarısız.")
        with tab2:
            u = st.text_input("Ad", key="ru")
            e_reg = st.text_input("Mail", key="re")
            p_reg = st.text_input("Şifre", type="password", key="rp")
            if st.button("Kayıt Ol"):
                try:
                    supabase.table("users").insert({"username":u, "email":e_reg, "password":p_reg}).execute()
                    st.success("Kayıt olundu!")
                except: st.error("Kayıt hatası.")

# --- 6. ARAYÜZ ---
with st.sidebar:
    st.title("🍿 CineMatch")
    login_ui()
    
st.title("🍿 CineMatch AI")

# Form
c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with c2: detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı...")

if st.button("FİLM BUL 🚀", use_container_width=True):
    with st.spinner("Aranıyor..."):
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}.
        Return EXACTLY 3 movies. JSON Format:
        {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Reason" }} ] }}
        """
        
        json_str = get_groq_response(prompt)
        
        if json_str:
            try:
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
                            st.caption(f"⭐ {film['puan']}")
                            st.info(film['neden'])
                else: st.warning("Film bulunamadı.")
            except: st.error("Veri işleme hatası.")