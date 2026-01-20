import streamlit as st
from supabase import create_client, Client
import requests
import json
import random
import time
from datetime import date, datetime
import re

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# PREMIUM KARANLIK TEMA CSS
def local_css():
    st.markdown(f"""
    <style>
    /* GENEL */
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    
    /* INPUTLAR */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {{
        background-color: #222; color: white; border: 1px solid #444; border-radius: 8px;
    }}
    
    /* BUTONLAR */
    .stButton>button {{
        background: linear-gradient(90deg, #E50914 0%, #B20710 100%);
        color: white; border: none; border-radius: 6px; height: 3em; font-weight: bold; font-size: 16px;
    }}
    .stButton>button:hover {{ box-shadow: 0 0 15px rgba(229, 9, 20, 0.6); }}
    
    /* PAYWALL */
    .paywall-container {{
        background: linear-gradient(135deg, #1a1a1a 0%, #000 100%);
        border: 1px solid #FFD700; border-radius: 12px; padding: 30px;
        text-align: center; color: white; margin: 20px 0;
        box-shadow: 0 0 25px rgba(255, 215, 0, 0.15);
    }}
    .paywall-btn {{
        background: #FFD700; color: #000; padding: 12px 35px; border-radius: 50px;
        font-weight: 800; text-decoration: none; display: inline-block; margin-top: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. VERİTABANI BAĞLANTISI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Veritabanı hatası: {e}")
    st.stop()

# --- 3. OTURUM YÖNETİMİ ---
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_usage' not in st.session_state: st.session_state.guest_usage = 0
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []
# Bulunan modeli hafızada tutalım ki her seferinde aramasın
if 'active_model_name' not in st.session_state: st.session_state.active_model_name = None

# --- 4. KRİTİK FONKSİYON: OTOMATİK MODEL SEÇİCİ ---
def get_best_available_model(api_key):
    """
    Bu fonksiyon API Key'in yetkili olduğu modelleri listeler
    ve 'flash' ismini içeren ilk modeli seçer. Böylece 404 hatası engellenir.
    """
    if st.session_state.active_model_name:
        return st.session_state.active_model_name

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = requests.get(list_url)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            
            # 1. Öncelik: Adında 'flash' geçen modeller (Hızlı ve Ucuz)
            for m in models:
                name = m['name'].replace('models/', '')
                if 'generateContent' in m['supportedGenerationMethods'] and 'flash' in name:
                    st.session_state.active_model_name = name
                    return name
            
            # 2. Öncelik: Adında 'pro' geçen modeller
            for m in models:
                name = m['name'].replace('models/', '')
                if 'generateContent' in m['supportedGenerationMethods'] and 'pro' in name:
                    st.session_state.active_model_name = name
                    return name
            
            # 3. Öncelik: Herhangi bir model
            for m in models:
                name = m['name'].replace('models/', '')
                if 'generateContent' in m['supportedGenerationMethods']:
                    st.session_state.active_model_name = name
                    return name
                    
    except Exception as e:
        print(f"Model listeleme hatası: {e}")
    
    # Hiçbir şey bulamazsa en standart olana dön (Fallback)
    return "gemini-1.5-flash"

# --- 5. DİĞER YARDIMCI FONKSİYONLAR ---
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            # Haftalık sıfırlama
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

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🍿 CineMatch AI")
    if st.session_state.user:
        user = st.session_state.user
        st.success(f"👤 {user['username']}")
        if user['is_premium']:
            st.info("💎 PREMIUM HESAP")
        else:
            kalan = 3 - user['daily_usage']
            st.caption(f"Haftalık Hak: {kalan}/3")
            st.progress(user['daily_usage']/3)
        if st.button("Çıkış"):
            st.session_state.user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            el = st.text_input("E-Posta", key="l_e")
            pl = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap"): login_user(el, pl)
        with tab2:
            ur = st.text_input("Ad", key="r_u")
            er = st.text_input("E-Posta", key="r_e")
            pr = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kayıt Ol"): register_user(ur, er, pr)
    
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.markdown("---")
        st.markdown("""
        <div style="background:#FFD700; color:black; padding:10px; border-radius:8px; text-align:center;">
            <strong>👑 Premium Ol</strong><br>$0.99 - Sınırsız
            <a href="https://www.buymeacoffee.com" target="_blank" style="display:block; margin-top:5px; background:black; color:white; padding:5px; border-radius:4px; text-decoration:none;">SATIN AL</a>
        </div>
        """, unsafe_allow_html=True)

# --- 7. ANA EKRAN ---
st.title("🍿 CineMatch AI")
st.caption("Yapay zeka senin için en iyi filmi seçsin.")

izin_var = check_limits()

if not izin_var:
    st.markdown("""
    <div class="paywall-container">
        <h2>🚧 HAKKINIZ BİTTİ</h2>
        <p>3 ücretsiz deneme hakkını doldurdun.</p>
        <div style="font-size:2.5em; font-weight:800; color:#FFD700;">$0.99</div>
        <a href="https://www.buymeacoffee.com" target="_blank" class="paywall-btn">PREMIUM AL</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Form
col_mod = st.columns(5)
secilen_mod = st.radio("Mod:", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız"], horizontal=True)
secilen_tur = st.selectbox("Tür:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Komedi", "Dram"])
secilen_detay = st.text_input("Detay:", placeholder="Örn: Sürpriz sonlu, 2023 yapımı...")

if st.button("FİLM BUL 🚀", use_container_width=True):
    with st.spinner("Model aranıyor ve film seçiliyor..."):
        try:
            api_key = st.secrets["google"]["api_key"]
            
            # --- OTOMATİK MODEL SEÇİMİ (404 ÇÖZÜMÜ) ---
            target_model = get_best_available_model(api_key)
            # ------------------------------------------
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
            
            yasakli = ", ".join(st.session_state.gosterilen_filmler)
            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {secilen_tur}. Details: {secilen_detay}. Context: {secilen_mod}.
            Ignore these: [{yasakli}].
            Return EXACTLY 3 movies. JSON Format:
            [{{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }}]
            """
            
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
            
            if resp.status_code == 200:
                content = resp.json()['candidates'][0]['content']['parts'][0]['text']
                filmler = json.loads(content.replace('```json', '').replace('```', '').strip())
                update_usage()
                
                cols = st.columns(3)
                for i, film in enumerate(filmler):
                    st.session_state.gosterilen_filmler.append(film['film_adi'])
                    with cols[i]:
                        st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                        st.markdown(f"**{film['film_adi']}** ({film['yil']})")
                        st.caption(f"⭐ {film['puan']}")
                        st.info(film['neden'])
            elif resp.status_code == 429:
                st.error("⚠️ Kota doldu (429). Lütfen 1 dakika bekleyin.")
            else:
                st.error(f"Hata ({target_model}): {resp.status_code}")
                
        except Exception as e:
            st.error(f"Bağlantı hatası: {e}")