import streamlit as st
from supabase import create_client, Client
import requests
import json
import time
from datetime import date, datetime
import re

# --- 1. SAYFA VE TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input, .stSelectbox > div > div > div {{
        background-color: #222; color: white; border: 1px solid #444; border-radius: 8px;
    }}
    .stButton>button {{
        background: linear-gradient(90deg, #E50914 0%, #B20710 100%);
        color: white; border: none; height: 3em; font-weight: bold; font-size: 16px;
    }}
    .paywall-container {{
        background: linear-gradient(135deg, #1a1a1a 0%, #000 100%);
        border: 1px solid #FFD700; border-radius: 12px; padding: 30px;
        text-align: center; color: white; margin: 20px 0;
    }}
    .paywall-btn {{
        background: #FFD700; color: #000; padding: 12px 35px; border-radius: 50px;
        font-weight: 800; text-decoration: none; display: inline-block; margin-top: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. VERİTABANI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Veritabanı hatası: {e}")
    st.stop()

# --- 3. OTURUM ---
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_usage' not in st.session_state: st.session_state.guest_usage = 0
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# --- 4. YARDIMCI FONKSİYONLAR ---
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            try:
                last = datetime.strptime(str(user_data['last_active']), "%Y-%m-%d").date()
                if (date.today() - last).days >= 7:
                    supabase.table("users").update({"daily_usage": 0, "last_active": str(date.today())}).eq("id", user_data['id']).execute()
                    user_data['daily_usage'] = 0
            except: pass
            st.session_state.user = user_data
            st.rerun()
        else:
            st.error("Hatalı bilgi.")
    except: st.error("Giriş hatası.")

def register_user(username, email, password):
    if not is_valid_email(email):
        st.warning("Geçersiz e-posta.")
        return
    try:
        check = supabase.table("users").select("*").eq("email", email).execute()
        if check.data: st.warning("Bu e-posta kayıtlı.")
        else:
            supabase.table("users").insert({
                "username": username, "email": email, "password": password,
                "is_premium": False, "daily_usage": 0, "last_active": str(date.today())
            }).execute()
            st.success("Kayıt tamam! Giriş yapabilirsin.")
    except: st.error("Kayıt hatası.")

def check_limits():
    if st.session_state.user and st.session_state.user['is_premium']: return True
    if st.session_state.user: return st.session_state.user['daily_usage'] < 3
    if 'guest_usage' not in st.session_state: st.session_state.guest_usage = 0
    return st.session_state.guest_usage < 3

def update_usage():
    if st.session_state.user:
        if not st.session_state.user['is_premium']:
            new_count = st.session_state.user['daily_usage'] + 1
            supabase.table("users").update({"daily_usage": new_count}).eq("id", st.session_state.user['id']).execute()
            st.session_state.user['daily_usage'] = new_count
    else:
        st.session_state.guest_usage += 1

def get_movie_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url).json()
        if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
        return "https://via.placeholder.com/500x750?text=No+Img"
    except: return "https://via.placeholder.com/500x750?text=Error"

# --- 5. GROQ AI MOTORU (GÜNCELLENDİ) ---
def get_groq_recommendation(prompt_text):
    groq_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    
    data = {
        "model": "llama-3.3-70b-versatile", # <--- İŞTE YENİ VE GÜÇLÜ MODEL BURADA
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.5,
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        st.error(f"API Hatası: {response.status_code}")
        return None

# --- 6. ARAYÜZ ---
with st.sidebar:
    st.markdown("### 🍿 CineMatch AI")
    if st.session_state.user:
        user = st.session_state.user
        st.success(f"👤 {user['username']}")
        if user['is_premium']: st.info("💎 PREMIUM")
        else:
            kalan = 3 - user['daily_usage']
            st.progress(user['daily_usage']/3)
            st.caption(f"Hak: {kalan}/3")
        if st.button("Çıkış"):
            st.session_state.user = None
            st.rerun()
    else:
        t1, t2 = st.tabs(["Giriş", "Kayıt"])
        with t1:
            e = st.text_input("E-Posta", key="le")
            p = st.text_input("Şifre", type="password", key="lp")
            if st.button("Giriş"): login_user(e, p)
        with t2:
            u = st.text_input("Ad", key="ru")
            e = st.text_input("E-Posta", key="re")
            p = st.text_input("Şifre", type="password", key="rp")
            if st.button("Kayıt"): register_user(u, e, p)
    
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.markdown("---")
        st.markdown("<div style='background:#FFD700;color:black;padding:10px;border-radius:8px;text-align:center;'><b>👑 Premium Ol</b><br>$0.99</div>", unsafe_allow_html=True)

st.title("🍿 CineMatch AI")

if not check_limits():
    st.markdown("""
    <div class="paywall-container">
        <h2>🚧 HAKKINIZ BİTTİ</h2>
        <p>3 ücretsiz deneme hakkı doldu.</p>
        <div style="font-size:2.5em;font-weight:800;color:#FFD700;">$0.99</div>
        <a href="#" class="paywall-btn">PREMIUM AL</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Komedi", "Dram"])
with c2: detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu...")
mod = st.radio("Mod", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız"], horizontal=True)

if st.button("FİLM BUL 🚀", use_container_width=True):
    with st.spinner("Yapay zeka analiz ediyor..."):
        yasakli = ", ".join(st.session_state.gosterilen_filmler)
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}. Context: {mod}.
        Ignore: [{yasakli}].
        Return EXACTLY 3 movies. JSON Format ONLY:
        {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }} ] }}
        """
        
        json_str = get_groq_recommendation(prompt)
        
        if json_str:
            try:
                if "```json" in json_str: json_str = json_str.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                filmler = data.get("movies", [])
                
                if filmler:
                    update_usage()
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        st.session_state.gosterilen_filmler.append(film['film_adi'])
                        with cols[i]:
                            st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                            st.markdown(f"**{film['film_adi']}** ({film['yil']})")
                            st.caption(f"⭐ {film['puan']}")
                            st.info(film['neden'])
                else: st.error("Uygun film bulunamadı.")
            except Exception as e: st.error(f"Veri işleme hatası: {e}")