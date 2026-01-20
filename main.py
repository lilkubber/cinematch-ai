import streamlit as st
from supabase import create_client, Client
import requests
import json
import random
import time
from datetime import date, datetime
import re # Email kontrolü için

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# CSS Yükleme (Tasarım)
def local_css(file_name):
    st.markdown(f"""
    <style>
    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }}
    .paywall-container {{
        background: linear-gradient(135deg, #1e1e1e 0%, #3a0000 100%);
        border: 2px solid #ff4b4b;
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        color: white;
        margin: 20px 0;
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.3);
    }}
    .paywall-price {{ font-size: 2.5em; font-weight: 800; color: #ffd700; }}
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
    st.error("Veritabanı hatası.")
    st.stop()

# --- 3. OTURUM YÖNETİMİ ---
if 'user' not in st.session_state: st.session_state.user = None
if 'guest_usage' not in st.session_state: st.session_state.guest_usage = 0
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# --- 4. YARDIMCI FONKSİYONLAR ---

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def login_user(email, password):
    try:
        # Artık e-posta ile giriş yapıyoruz
        response = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            check_weekly_reset(user_data)
            st.session_state.user = user_data
            st.toast(f"Hoş geldin, {user_data['username']}!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("E-posta veya şifre hatalı.")
    except Exception as e:
        st.error(f"Hata: {e}")

def register_user(username, email, password):
    if not is_valid_email(email):
        st.warning("Geçersiz e-posta adresi.")
        return

    try:
        # E-posta kontrolü
        check = supabase.table("users").select("*").eq("email", email).execute()
        if check.data:
            st.warning("Bu e-posta zaten kayıtlı.")
        else:
            supabase.table("users").insert({
                "username": username,
                "email": email,
                "password": password,
                "is_premium": False,
                "daily_usage": 0,
                "last_active": str(date.today())
            }).execute()
            st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def check_weekly_reset(user_data):
    bugun = date.today()
    try:
        last_active = datetime.strptime(str(user_data['last_active']), "%Y-%m-%d").date()
    except:
        last_active = bugun
    
    if (bugun - last_active).days >= 7:
        supabase.table("users").update({"daily_usage": 0, "last_active": str(bugun)}).eq("id", user_data['id']).execute()
        user_data['daily_usage'] = 0

def check_limits():
    """Limit kontrolü (Premium sınırsız, diğerleri 3 hak)"""
    if st.session_state.user:
        if st.session_state.user['is_premium']: return True
        return st.session_state.user['daily_usage'] < 3
    else:
        return st.session_state.guest_usage < 3

def update_usage():
    if st.session_state.user:
        if not st.session_state.user['is_premium']: # Premium değilse düş
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

# --- 5. SIDEBAR (GİRİŞ & PROFİL) ---
with st.sidebar:
    if st.session_state.user:
        user = st.session_state.user
        st.header(f"👤 {user['username']}")
        if user['is_premium']:
            st.success("🌟 PREMIUM")
        else:
            st.info("STANDART ÜYE")
            kalan = 3 - user['daily_usage']
            st.progress(user['daily_usage'] / 3)
            st.caption(f"Haftalık Kalan: {kalan}/3")
        
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()
    else:
        st.header("👤 Giriş / Kayıt")
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            email_l = st.text_input("E-Posta", key="l_e")
            pass_l = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap"): login_user(email_l, pass_l)
        with tab2:
            user_r = st.text_input("Kullanıcı Adı", key="r_u")
            email_r = st.text_input("E-Posta", key="r_e")
            pass_r = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kayıt Ol"):
                if user_r and email_r and pass_r: register_user(user_r, email_r, pass_r)
                else: st.warning("Tüm alanları doldurun.")

    st.markdown("---")
    # HERKESE PREMIUM REKLAMI
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.markdown(
            """
            <div style='background:#ffd700; padding:10px; border-radius:10px; color:black; text-align:center;'>
                <b>💎 Premium Ol</b><br>Sınırsız Arama<br>$0.99
                <a href='https://www.buymeacoffee.com' target='_blank' style='display:block; background:black; color:white; padding:5px; margin-top:5px; text-decoration:none; border-radius:5px;'>SATIN AL</a>
            </div>
            """, unsafe_allow_html=True
        )

# --- 6. ANA EKRAN ---
st.title("🍿 CineMatch AI")

izin_var = check_limits()

# LİMİT DOLDUYSA PAYWALL
if not izin_var:
    st.markdown(
        """
        <div class='paywall-container'>
            <h2>🚧 Hakkınız Bitti!</h2>
            <p>Haftalık 3 arama hakkınızı doldurdunuz.</p>
            <div class='paywall-price'>$0.99</div>
            <p>Sınırsız kullanım için Premium alın.</p>
            <a href='https://www.buymeacoffee.com' target='_blank' class='paywall-btn'>🚀 PREMIUM'A GEÇ</a>
            <br><br>
            <small>Veya haftaya kadar bekleyin.</small>
        </div>
        """, unsafe_allow_html=True
    )
    st.stop() # Sayfanın geri kalanını yükleme

# ARAMA BÖLÜMÜ
col_mod1, col_mod2, col_mod3, col_mod4 = st.columns(4)

# Mod Seçimi (Radio buton yerine buton gibi davranan seçim)
secilen_mod = st.radio("Mod Seçiniz:", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız/Chill"], horizontal=True)

secilen_tur = st.selectbox("Tür:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Dram", "Suç"])
secilen_detay = st.text_area("Ekstra Detay (Opsiyonel):", placeholder="Örn: 2020 sonrası, kafa dağıtmalık...")

if st.button("🚀 Film Bul", use_container_width=True):
    with st.spinner("Yapay zeka filmleri analiz ediyor..."):
        try:
            # REST API (1.5 Flash)
            api_key = st.secrets["google"]["api_key"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            yasakli = ", ".join(st.session_state.gosterilen_filmler)
            
            # Modlara göre Prompt Ayarı
            mod_prompt = ""
            if "Sevgili" in secilen_mod: mod_prompt = "Couple Mode: Romantic or engaging, safe for date night."
            elif "Aile" in secilen_mod: mod_prompt = "Family Mode: No explicit scenes, fun for all ages."
            elif "Arkadaş" in secilen_mod: mod_prompt = "Friends Mode: Fun, action-packed or mind-bending, pizza movie."
            elif "Yalnız" in secilen_mod: mod_prompt = "Chill Mode: Relaxing, hidden gem, or deep story."
            else: mod_prompt = "Standard Search."

            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {secilen_tur}. Details: {secilen_detay}.
            Context: {mod_prompt}
            Ignore: [{yasakli}].
            Return EXACTLY 3 movies. JSON Format:
            [{{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }}]
            """
            
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json"}
            
            resp = requests.post(url, headers=headers, json=data)
            
            if resp.status_code == 200:
                content = resp.json()['candidates'][0]['content']['parts'][0]['text']
                filmler = json.loads(content.replace('```json', '').replace('```', '').strip())
                
                update_usage()
                
                cols = st.columns(3)
                for i, film in enumerate(filmler):
                    st.session_state.gosterilen_filmler.append(film['film_adi'])
                    with cols[i]:
                        st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                        st.subheader(film['film_adi'])
                        st.caption(f"⭐ {film['puan']} | 📅 {film['yil']}")
                        st.info(film['neden'])
                
                # Hak Bilgisi Göster (Toast mesajı)
                if not st.session_state.user:
                    kalan = 3 - st.session_state.guest_usage
                    st.toast(f"Misafir hakkı: {kalan} kaldı!", icon="ℹ️")
            else:
                st.error("Hata oluştu.")
                
        except Exception as e:
            st.error(f"Bağlantı hatası: {e}")