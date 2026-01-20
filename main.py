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
    /* GENEL SAYFA YAPISI (NETFLIX BLACK) */
    .stApp {{
        background-color: #141414;
        color: #e5e5e5;
    }}
    
    /* INPUT ALANLARI */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {{
        background-color: #333333;
        color: white;
        border: 1px solid #444;
        border-radius: 4px;
    }}
    
    /* BUTONLAR (NETFLIX RED) */
    .stButton>button {{
        background: linear-gradient(180deg, #E50914 0%, #B00610 100%);
        color: white;
        border: none;
        border-radius: 4px;
        height: 3em;
        font-weight: bold;
        font-size: 16px;
        transition: transform 0.2s;
    }}
    .stButton>button:hover {{
        transform: scale(1.02);
        box-shadow: 0 0 10px rgba(229, 9, 20, 0.5);
    }}
    .stButton>button:disabled {{
        background: #555;
        color: #888;
    }}

    /* PREMIUM PAYWALL KUTUSU (GOLD) */
    .paywall-container {{
        background: linear-gradient(135deg, #000000 0%, #1c1c1c 100%);
        border: 2px solid #FFD700;
        border-radius: 10px;
        padding: 40px;
        text-align: center;
        color: white;
        margin: 30px 0;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
    }}
    .paywall-header {{
        font-size: 2.2em;
        font-weight: 800;
        color: #FFD700;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }}
    .paywall-price {{
        font-size: 3.5em;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 0 10px #FFD700;
        margin: 10px 0;
    }}
    .paywall-btn {{
        display: inline-block;
        background: #FFD700;
        color: #000;
        padding: 15px 50px;
        border-radius: 50px;
        font-weight: 900;
        font-size: 1.2em;
        text-decoration: none;
        margin-top: 20px;
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.4);
        transition: all 0.3s;
    }}
    .paywall-btn:hover {{
        background: white;
        box-shadow: 0 0 30px rgba(255, 255, 255, 0.6);
        transform: scale(1.05);
    }}

    /* SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: #000000;
        border-right: 1px solid #333;
    }}
    
    /* FİLM KARTLARI */
    .movie-card {{
        background: #1f1f1f;
        padding: 10px;
        border-radius: 8px;
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

# --- 4. YARDIMCI FONKSİYONLAR ---
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def login_user(email, password):
    try:
        response = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            # Haftalık sıfırlama kontrolü
            try:
                last = datetime.strptime(str(user_data['last_active']), "%Y-%m-%d").date()
                if (date.today() - last).days >= 7:
                    supabase.table("users").update({"daily_usage": 0, "last_active": str(date.today())}).eq("id", user_data['id']).execute()
                    user_data['daily_usage'] = 0
            except: pass
            
            st.session_state.user = user_data
            st.toast(f"Hoş geldin!", icon="👋")
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
    """Limit Kontrolü"""
    # 1. Premium
    if st.session_state.user and st.session_state.user['is_premium']: return True
    
    # 2. Standart Üye (3 Hak)
    if st.session_state.user:
        return st.session_state.user['daily_usage'] < 3
    
    # 3. Misafir (3 Hak)
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

# --- 5. SIDEBAR (GİRİŞ & PROFİL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.markdown("### 🍿 CineMatch AI")
    
    if st.session_state.user:
        user = st.session_state.user
        st.divider()
        st.write(f"👤 **{user['username']}**")
        
        if user['is_premium']:
            st.success("💎 PREMIUM ÜYE")
        else:
            kalan = 3 - user['daily_usage']
            st.info(f"Haftalık Kalan: {kalan}/3")
            st.progress(user['daily_usage'] / 3)
        
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()
    else:
        st.divider()
        st.write("👤 **Giriş / Kayıt**")
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            el = st.text_input("E-Posta", key="l_e")
            pl = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap"): login_user(el, pl)
        with tab2:
            ur = st.text_input("Kullanıcı Adı", key="r_u")
            er = st.text_input("E-Posta", key="r_e")
            pr = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kayıt Ol"): register_user(ur, er, pr)
    
    # PREMIUM REKLAM KUTUSU (Sidebar)
    if not (st.session_state.user and st.session_state.user['is_premium']):
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(45deg, #FFD700, #FDB931); padding: 15px; border-radius: 8px; color: black; text-align: center;">
            <strong style="font-size: 1.2em;">👑 Premium Ol</strong>
            <p style="margin: 5px 0; font-size: 0.9em;">Sınırsız Film, Özel Modlar</p>
            <h3 style="margin: 0;">$0.99</h3>
        </div>
        """, unsafe_allow_html=True)

# --- 6. ANA EKRAN ---

# Başlık
st.markdown("<h1 style='text-align: center; color: #E50914; font-size: 3em; font-weight: 900;'>CineMatch AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #bbb; margin-bottom: 40px;'>Yapay Zeka Destekli Kişisel Sinema Küratörün</p>", unsafe_allow_html=True)

izin_var = check_limits()

# --- PAYWALL (LİMİT DOLUNCA) ---
if not izin_var:
    st.markdown(
        """
        <div class='paywall-container'>
            <div class='paywall-header'>🚧 İZLEME KEYFİ YARIM KALMASIN</div>
            <p style='font-size: 1.2em; color: #ccc;'>3 filmlik ücretsiz deneme hakkınızı doldurdunuz.</p>
            <div class='paywall-price'>$0.99</div>
            <p style='color: #FFD700; font-weight: bold;'>BİR KAHVE PARASINA SINIRSIZ ERİŞİM</p>
            <a href='https://www.buymeacoffee.com' target='_blank' class='paywall-btn'>🚀 PREMIUM HESABA GEÇ</a>
            <br><br>
            <small style='color: #666;'>Giriş yaptıysanız haftaya haklarınız yenilenir.</small>
        </div>
        """, unsafe_allow_html=True
    )
    st.stop() # Kodun geri kalanını durdur

# --- ARAMA FORMU ---
col_mod = st.columns(5)
secilen_mod = st.radio("Mod Seçimi:", ["Normal", "💑 Sevgili", "👨‍👩‍👧‍👦 Aile", "🍕 Arkadaş", "🧘 Yalnız"], horizontal=True, label_visibility="collapsed")

col_sel1, col_sel2 = st.columns([1, 2])
with col_sel1:
    secilen_tur = st.selectbox("Tür", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Dram", "Suç"])
with col_sel2:
    secilen_detay = st.text_input("Detay (Ne hissediyorsun?)", placeholder="Örn: 2023 yapımı, beyin yakan, sonu sürprizli...")

if st.button("FİLM ÖNERİSİ AL", use_container_width=True):
    with st.spinner("Yapay zeka veritabanını tarıyor..."):
        try:
            # 🚀 KRİTİK DÜZELTME: Senin listende kesin olan model adını kullanıyoruz
            # 404 hatasını çözen sihirli satır burası 👇
            model_name = "gemini-2.0-flash-lite-preview-02-05"
            
            api_key = st.secrets["google"]["api_key"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            yasakli = ", ".join(st.session_state.gosterilen_filmler)
            
            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {secilen_tur}. Details: {secilen_detay}. Context: {secilen_mod}.
            Ignore: [{yasakli}].
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
                        st.markdown(f"### {film['film_adi']}")
                        st.markdown(f"**⭐ {film['puan']}** | 📅 {film['yil']}")
                        st.info(film['neden'])
                
                if not st.session_state.user:
                    kalan = 3 - st.session_state.guest_usage
                    st.toast(f"Deneme hakkı: {kalan} kaldı!", icon="⏳")
            
            elif resp.status_code == 429:
                st.error("Sunucu çok yoğun (Kota Doldu). Lütfen 1 dakika bekleyin veya Premium API kullanın.")
            elif resp.status_code == 404:
                 # YEDEK PLAN: Eğer 2.0-flash bulunamazsa gemini-pro (Eski model) dene
                st.warning("Model bulunamadı, yedek sunucuya bağlanılıyor...")
                fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                resp_fb = requests.post(fallback_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp_fb.status_code == 200:
                    content = resp_fb.json()['candidates'][0]['content']['parts'][0]['text']
                    filmler = json.loads(content.replace('```json', '').replace('```', '').strip())
                    update_usage()
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        st.session_state.gosterilen_filmler.append(film['film_adi'])
                        with cols[i]:
                            st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                            st.markdown(f"### {film['film_adi']}")
                            st.info(film['neden'])
                else:
                    st.error(f"Yedek sunucu da yanıt vermedi. Hata: {resp_fb.status_code}")
            else:
                st.error(f"Sunucu Hatası: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")