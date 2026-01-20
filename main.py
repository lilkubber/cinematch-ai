import streamlit as st
import requests
import json
import time
import re
from datetime import date, datetime

# --- 1. AYARLAR VE TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input {{ background-color: #222; color: white; border: 1px solid #444; }}
    .stButton>button {{ background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; font-weight: bold; }}
    .paywall-box {{ border: 2px solid #FFD700; padding: 20px; border-radius: 10px; text-align: center; background: #1a1a1a; margin-top: 20px; }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. VERİTABANI BAĞLANTISI (SUPABASE) ---
# Hata yakalayıcı ekledik ki bağlantı yoksa site çökmesin, uyarı versin.
supabase = None
try:
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"⚠️ Veritabanı Bağlantı Hatası: Lütfen Streamlit Cloud Secrets ayarlarını kontrol edin. Hata: {e}")

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_usage' not in st.session_state: st.session_state.guest_usage = 0
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# --- 4. YARDIMCI FONKSİYONLAR ---

def login_user(email, password):
    if not supabase: return
    try:
        res = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if res.data:
            user = res.data[0]
            # Haftalık sıfırlama kontrolü
            try:
                last = datetime.strptime(str(user['last_active']), "%Y-%m-%d").date()
                if (date.today() - last).days >= 7:
                    supabase.table("users").update({"daily_usage": 0, "last_active": str(date.today())}).eq("id", user['id']).execute()
                    user['daily_usage'] = 0
            except: pass
            
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Hatalı e-posta veya şifre.")
    except Exception as e:
        st.error(f"Giriş hatası: {e}")

def register_user(username, email, password):
    if not supabase: return
    try:
        # E-posta var mı kontrol et
        check = supabase.table("users").select("*").eq("email", email).execute()
        if check.data:
            st.warning("Bu e-posta zaten kayıtlı.")
        else:
            supabase.table("users").insert({
                "username": username, "email": email, "password": password,
                "is_premium": False, "daily_usage": 0, "last_active": str(date.today())
            }).execute()
            st.success("Kayıt başarılı! Şimdi giriş yapabilirsin.")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def update_usage():
    """Kullanım hakkını düşer."""
    if st.session_state.user:
        if not st.session_state.user['is_premium']:
            new = st.session_state.user['daily_usage'] + 1
            if supabase:
                supabase.table("users").update({"daily_usage": new}).eq("id", st.session_state.user['id']).execute()
            st.session_state.user['daily_usage'] = new
    else:
        st.session_state.guest_usage += 1

def check_limits():
    """Kullanıcının hakkı var mı?"""
    # Premium ise sınırsız
    if st.session_state.user and st.session_state.user['is_premium']: return True
    # Üye ise 3 hak
    if st.session_state.user: return st.session_state.user['daily_usage'] < 3
    # Misafir ise 3 hak
    return st.session_state.guest_usage < 3

def get_groq_response(prompt):
    try:
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
    except: return None

def get_poster(movie_name):
    try:
        key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={key}&query={movie_name}"
        res = requests.get(url, timeout=3).json()
        if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except: pass
    return "https://via.placeholder.com/500x750?text=No+Poster"

# --- 5. SIDEBAR (ÜYELİK) ---
with st.sidebar:
    st.title("🍿 CineMatch")
    
    if st.session_state.user:
        u = st.session_state.user
        st.success(f"Hoş geldin, {u['username']}")
        
        if u['is_premium']:
            st.info("💎 PREMIUM ÜYE")
        else:
            kalan = 3 - u['daily_usage']
            st.write(f"Kalan Hakkın: **{kalan}/3**")
            st.progress(u['daily_usage']/3)
            
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            email = st.text_input("E-Posta", key="le")
            password = st.text_input("Şifre", type="password", key="lp")
            if st.button("Giriş Yap"): login_user(email, password)
        with tab2:
            reg_user = st.text_input("Adın", key="ru")
            reg_email = st.text_input("E-Posta", key="re")
            reg_pass = st.text_input("Şifre", type="password", key="rp")
            if st.button("Kayıt Ol"): register_user(reg_user, reg_email, reg_pass)
            
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.markdown("---")
        st.markdown("""
        <div style='background:#FFD700; color:black; padding:10px; border-radius:10px; text-align:center;'>
            <b>👑 Premium'a Geç</b><br>Sınırsız Film Keyfi<br>$0.99
        </div>
        """, unsafe_allow_html=True)

# --- 6. ANA EKRAN ---
st.title("🍿 CineMatch AI")
st.caption("Moduna göre film öneren yapay zeka.")

# Limit Kontrolü ve Paywall
if not check_limits():
    st.markdown("""
    <div class="paywall-box">
        <h2>🚧 Ücretsiz Hakkınız Doldu!</h2>
        <p>Haftalık 3 film önerisi hakkınızı kullandınız.</p>
        <h1 style="color:#FFD700">$0.99</h1>
        <p>Sınırsız kullanım için Premium alın veya haftaya tekrar gelin.</p>
        <button style="background:#FFD700; color:black; padding:10px 30px; border:none; border-radius:20px; font-weight:bold; cursor:pointer;">PREMIUM AL</button>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Arama Formu
c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram", "Romantik"])
with c2: detay = st.text_input("Detay", placeholder="Örn: Beyin yakan, sonu sürprizli, 2024...")
mod = st.radio("Mod", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız"], horizontal=True)

if st.button("FİLM BUL 🚀", use_container_width=True):
    with st.spinner("Yapay zeka veritabanını tarıyor..."):
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}. Context: {mod}.
        Ignore: [{", ".join(st.session_state.gosterilen_filmler)}].
        Return EXACTLY 3 movies. JSON Format:
        {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }} ] }}
        """
        
        json_res = get_groq_response(prompt)
        
        if json_res:
            try:
                # JSON Temizliği
                if "```json" in json_res: json_res = json_res.split("```json")[1].split("```")[0].strip()
                elif "```" in json_res: json_res = json_res.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_res)
                filmler = data.get("movies", [])
                
                if filmler:
                    update_usage()
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        st.session_state.gosterilen_filmler.append(film['film_adi'])
                        with cols[i]:
                            st.image(get_poster(film['film_adi']), use_container_width=True)
                            st.subheader(f"{film['film_adi']}")
                            st.caption(f"⭐ {film['puan']} | 📅 {film['yil']}")
                            st.info(film['neden'])
                else:
                    st.warning("Uygun film bulunamadı.")
            except: st.error("Veri işleme hatası.")
        else:
            st.error("Bağlantı hatası. Lütfen sayfayı yenileyip tekrar deneyin.")
