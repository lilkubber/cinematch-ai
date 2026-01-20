import streamlit as st
from supabase import create_client, Client
import requests
import json
import random
import time
from datetime import date, datetime

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
    }}
    .premium-box {{
        padding: 20px;
        background-color: #ffd700;
        color: black;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }}
    .limit-info {{
        font-size: 0.8em;
        color: #666;
        text-align: center;
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
    st.error("Veritabanı bağlantı hatası. Lütfen Secrets ayarlarını kontrol et.")
    st.stop()

# --- 3. OTURUM YÖNETİMİ ---
if 'user' not in st.session_state:
    st.session_state.user = None # Giriş yapmış kullanıcı bilgisi
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

# --- 4. YARDIMCI FONKSİYONLAR ---

def login_user(username, password):
    """Kullanıcı girişi yapar ve haftalık limiti kontrol eder."""
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            
            # --- HAFTALIK SIFIRLAMA MANTIĞI ---
            bugun = date.today()
            # Veritabanından gelen tarihi (YYYY-MM-DD) al
            last_active_str = str(user_data['last_active']) 
            try:
                last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
            except:
                last_active_date = bugun # Hata olursa bugünü baz al
            
            # Kaç gün geçmiş?
            gun_farki = (bugun - last_active_date).days
            
            # Eğer 7 gün veya daha fazla geçmişse hakları fulle
            if gun_farki >= 7:
                supabase.table("users").update({"daily_usage": 0, "last_active": str(bugun)}).eq("id", user_data['id']).execute()
                user_data['daily_usage'] = 0
                user_data['last_active'] = str(bugun)
                st.toast("📅 Yeni hafta! Hakların sıfırlandı.")
            
            st.session_state.user = user_data
            st.success(f"Hoş geldin, {username}!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")
    except Exception as e:
        st.error(f"Giriş hatası: {e}")

def register_user(username, password):
    """Yeni kullanıcı kaydeder."""
    try:
        check = supabase.table("users").select("*").eq("username", username).execute()
        if check.data:
            st.warning("Bu kullanıcı adı zaten alınmış.")
        else:
            supabase.table("users").insert({
                "username": username, 
                "password": password,
                "is_premium": False,
                "daily_usage": 0,
                "last_active": str(date.today()) # Kayıt tarihi başlangıçtır
            }).execute()
            st.success("Kayıt başarılı! Şimdi giriş yapabilirsin.")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def check_limits():
    """Limit kontrolü yapar."""
    user = st.session_state.user
    if not user: return False
    
    if user['is_premium']:
        return True
    
    # LİMİT: Haftada 3 Hak
    limit = 3
    if user['daily_usage'] < limit:
        return True
    else:
        return False

def update_usage():
    """Kullanım sayısını artırır."""
    user = st.session_state.user
    if user:
        new_count = user['daily_usage'] + 1
        # Tarihi güncellemiyoruz! Tarih sadece sıfırlanacağı zaman (7 gün sonra) değişir.
        supabase.table("users").update({"daily_usage": new_count}).eq("id", user['id']).execute()
        st.session_state.user['daily_usage'] = new_count

# Film Afişi
def get_movie_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url).json()
        if res['results']:
            return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
        return "https://via.placeholder.com/500x750?text=No+Img"
    except:
        return "https://via.placeholder.com/500x750?text=Error"

# --- 5. ANA EKRAN MANTIĞI ---

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>🍿 CineMatch AI</h1>", unsafe_allow_html=True)
    st.info("Film önerisi almak için lütfen giriş yapın.")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    with tab1:
        l_user = st.text_input("Kullanıcı Adı", key="l_u")
        l_pass = st.text_input("Şifre", type="password", key="l_p")
        if st.button("Giriş Et"):
            if l_user and l_pass: login_user(l_user, l_pass)
            else: st.warning("Doldurunuz.")
    with tab2:
        r_user = st.text_input("Kullanıcı Adı Seç", key="r_u")
        r_pass = st.text_input("Şifre Seç", type="password", key="r_p")
        if st.button("Kayıt Ol"):
            if r_user and r_pass: register_user(r_user, r_pass)
            else: st.warning("Doldurunuz.")

else:
    user = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        
        if user['is_premium']:
            st.success("🌟 PREMIUM")
            st.write("Sınırsız Erişim")
        else:
            st.info("STANDART")
            kalan = 3 - user['daily_usage']
            st.write(f"Haftalık Hak: **{kalan}/3**")
            st.progress(user['daily_usage'] / 3)
            
            # Kalan gün hesaplama
            last_active_date = datetime.strptime(str(user['last_active']), "%Y-%m-%d").date()
            gecen_gun = (date.today() - last_active_date).days
            kalan_gun = 7 - gecen_gun
            if kalan_gun < 0: kalan_gun = 0
            
            st.caption(f"Yenilenmeye: {kalan_gun} gün var")
            
            if kalan == 0:
                st.error("Bu haftalık hakkın bitti!")
                st.markdown(
                    """
                    <div class='premium-box'>
                        <h3>🚀 Premium Al</h3>
                        <p>Beklemek istemiyor musun?</p>
                        <p>Sadece $1 (35 TL)</p>
                        <a href='https://www.buymeacoffee.com' target='_blank' style='display:block; background:black; color:white; padding:10px; border-radius:5px; text-decoration:none; font-weight:bold;'>HEMEN GEÇ</a>
                    </div>
                    """, unsafe_allow_html=True
                )

        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()

    st.markdown("<h1>🍿 CineMatch AI</h1>", unsafe_allow_html=True)
    
    secilen_tur = st.selectbox("Tür:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Dram"])
    secilen_detay = st.text_area("Detay:", placeholder="Örn: Sürpriz sonlu olsun...")
    
    col1, col2 = st.columns(2)
    with col1:
        btn_normal = st.button("🚀 Normal Ara", use_container_width=True)
    with col2:
        btn_couple = st.button("💑 Sevgili Modu (Pro)", use_container_width=True, disabled=not user['is_premium'])
        if not user['is_premium']: st.caption("🔒 Premium'a özel")

    if btn_normal or (btn_couple and user['is_premium']):
        if not check_limits():
            st.error("🚨 Bu haftalık 3 arama hakkın doldu!")
            st.info(f"Hakların {kalan_gun} gün sonra yenilenecek. Veya $1 verip beklemeden sınırsız yapabilirsin.")
        else:
            with st.spinner("Yapay zeka film seçiyor..."):
                try:
                    # REST API (1.5 Flash)
                    api_key = st.secrets["google"]["api_key"]
                    model_name = "gemini-1.5-flash"
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    
                    yasakli = ", ".join(st.session_state.gosterilen_filmler)
                    prompt_context = "COUPLE MODE: Safe for date night." if btn_couple else "NORMAL MODE."
                    
                    prompt = f"""
                    Role: Movie curator. Language: Turkish.
                    Genre: {secilen_tur}. Details: {secilen_detay}. {prompt_context}
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
                    elif resp.status_code == 429:
                        st.error("Sunucu çok yoğun (429). 1 Dakika bekleyip tekrar dene.")
                    else:
                        st.error(f"Hata: {resp.status_code}")
                        
                except Exception as e:
                    st.error(f"Bağlantı hatası: {e}")