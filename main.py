import streamlit as st
from supabase import create_client, Client
import requests
import json
import time
from datetime import date, datetime
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# CSS Yükleme
def local_css(file_name):
    st.markdown(f"""
    <style>
    .stButton>button {{ width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }}
    .paywall-container {{
        background: linear-gradient(135deg, #1e1e1e 0%, #3a0000 100%);
        border: 2px solid #ff4b4b; border-radius: 15px; padding: 30px;
        text-align: center; color: white; margin: 20px 0;
    }}
    .paywall-btn {{
        background-color: #ffd700; color: black; padding: 10px 30px;
        border-radius: 50px; text-decoration: none; font-weight: bold;
    }}
    </style>
    """, unsafe_allow_html=True)

local_css("style.css")

# --- 2. VERİTABANI BAĞLANTISI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Veritabanı hatası: {e}")
    st.stop()

# --- 3. OTURUM YÖNETİMİ (Burayı düzelttim) ---
if 'user' not in st.session_state:
    st.session_state.user = None # Giriş yapılmadı
if 'guest_usage' not in st.session_state:
    st.session_state.guest_usage = 0 # Misafir sayacı 0'dan başlar
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

# --- 4. YARDIMCI FONKSİYONLAR ---
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            # Haftalık kontrol
            try:
                last = datetime.strptime(str(user_data['last_active']), "%Y-%m-%d").date()
                if (date.today() - last).days >= 7:
                    supabase.table("users").update({"daily_usage": 0, "last_active": str(date.today())}).eq("id", user_data['id']).execute()
                    user_data['daily_usage'] = 0
            except: pass
            
            st.session_state.user = user_data
            st.toast(f"Hoş geldin!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Hatalı bilgi.")
    except Exception as e:
        st.error(f"Giriş hatası: {e}")

def register_user(username, email, password):
    if not is_valid_email(email):
        st.warning("Geçersiz e-posta.")
        return
    try:
        check = supabase.table("users").select("*").eq("email", email).execute()
        if check.data:
            st.warning("Bu e-posta kayıtlı.")
        else:
            supabase.table("users").insert({
                "username": username, "email": email, "password": password,
                "is_premium": False, "daily_usage": 0, "last_active": str(date.today())
            }).execute()
            st.success("Kayıt tamam! Giriş yapabilirsin.")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def check_limits():
    """Limit kontrolü - Hata ayıklama için print ekledim"""
    # 1. Giriş yapmış kullanıcı
    if st.session_state.user:
        if st.session_state.user['is_premium']: return True
        return st.session_state.user['daily_usage'] < 3
    
    # 2. Misafir (Giriş yapmamış)
    else:
        # Eğer guest_usage session'da yoksa 0 yap
        if 'guest_usage' not in st.session_state:
            st.session_state.guest_usage = 0
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

# --- 5. SIDEBAR ---
with st.sidebar:
    if st.session_state.user:
        user = st.session_state.user
        st.header(f"👤 {user['username']}")
        if user['is_premium']: st.success("🌟 PREMIUM")
        else:
            kalan = 3 - user['daily_usage']
            st.info(f"Kalan Hak: {kalan}/3")
        if st.button("Çıkış"):
            st.session_state.user = None
            st.rerun()
    else:
        st.header("👤 Giriş / Kayıt")
        t1, t2 = st.tabs(["Giriş", "Kayıt"])
        with t1:
            el = st.text_input("E-Posta", key="l_e")
            pl = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş"): login_user(el, pl)
        with t2:
            ur = st.text_input("Ad", key="r_u")
            er = st.text_input("E-Posta", key="r_e")
            pr = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kayıt"): register_user(ur, er, pr)
    
    st.markdown("---")
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.info("💎 Premium: $0.99 (Sınırsız)")

# --- 6. ANA EKRAN ---
st.title("🍿 CineMatch AI")

izin_var = check_limits()

if not izin_var:
    st.markdown("""
        <div class='paywall-container'>
            <h2>🚧 Deneme Hakkınız Bitti!</h2>
            <p>Haftalık 3 hakkınızı doldurdunuz.</p>
            <div class='paywall-price'>$0.99</div>
            <a href='https://www.buymeacoffee.com' target='_blank' class='paywall-btn'>PREMIUM AL</a>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# --- ARAMA FORMU ---
col_mod = st.columns(5)
secilen_mod = st.radio("Mod:", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız"], horizontal=True)

secilen_tur = st.selectbox("Tür:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Dram"])
secilen_detay = st.text_area("Detay:", placeholder="Örn: 2023 yapımı, sürpriz sonlu...")

if st.button("🚀 Film Bul", use_container_width=True):
    with st.spinner("Aranıyor..."):
        try:
            api_key = st.secrets["google"]["api_key"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {secilen_tur}. Details: {secilen_detay}. Context: {secilen_mod}.
            Ignore: [{", ".join(st.session_state.gosterilen_filmler)}].
            Return EXACTLY 3 movies. JSON Format:
            [{{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }}]
            """
            
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
            
            if resp.status_code == 200:
                content = resp.json()['candidates'][0]['content']['parts'][0]['text']
                filmler = json.loads(content.replace('```json', '').replace('```', '').strip())
                
                update_usage() # Hakkı düş
                
                cols = st.columns(3)
                for i, film in enumerate(filmler):
                    st.session_state.gosterilen_filmler.append(film['film_adi'])
                    with cols[i]:
                        st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                        st.subheader(film['film_adi'])
                        st.caption(f"⭐ {film['puan']}")
                        st.info(film['neden'])
                
                if not st.session_state.user:
                    st.toast(f"Misafir hakkı: {3 - st.session_state.guest_usage} kaldı!")
            
            elif resp.status_code == 429:
                st.error("Sunucu yoğun (429). Lütfen API Key kotanızı kontrol edin.")
            else:
                st.error(f"Hata Kodu: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")