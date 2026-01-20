import streamlit as st
from supabase import create_client, Client
import requests
import json
import random
import time
from datetime import date, datetime

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# CSS Yükleme (Tasarım ve Paywall)
def local_css(file_name):
    st.markdown(f"""
    <style>
    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }}
    /* PREMIUM KUTUSU TASARIMI */
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
    .paywall-header {{
        font-size: 2em;
        font-weight: bold;
        color: #ff4b4b;
        margin-bottom: 10px;
    }}
    .paywall-price {{
        font-size: 2.5em;
        font-weight: 800;
        color: #ffd700;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }}
    .paywall-btn {{
        display: inline-block;
        background-color: #ffd700;
        color: black;
        padding: 15px 40px;
        border-radius: 50px;
        font-weight: bold;
        font-size: 1.2em;
        text-decoration: none;
        margin-top: 20px;
        transition: transform 0.2s;
    }}
    .paywall-btn:hover {{
        transform: scale(1.05);
        box-shadow: 0 0 15px #ffd700;
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
if 'user' not in st.session_state:
    st.session_state.user = None
if 'guest_usage' not in st.session_state:
    st.session_state.guest_usage = 0
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

# --- 4. FONKSİYONLAR ---

def login_user(username, password):
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            user_data = response.data[0]
            check_weekly_reset(user_data) # Haftalık sıfırlama kontrolü
            st.session_state.user = user_data
            st.toast(f"Hoş geldin, {username}!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Hatalı bilgi.")
    except Exception as e:
        st.error(f"Hata: {e}")

def register_user(username, password):
    try:
        check = supabase.table("users").select("*").eq("username", username).execute()
        if check.data:
            st.warning("Bu isim alınmış.")
        else:
            supabase.table("users").insert({
                "username": username, "password": password, "is_premium": False, "daily_usage": 0, "last_active": str(date.today())
            }).execute()
            st.success("Kayıt tamam! Giriş yapabilirsin.")
    except Exception as e:
        st.error(f"Hata: {e}")

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
    """Limit kontrolü - DÖNÜŞ DEĞERİ: (İzin Var mı?, Limit Sebebi)"""
    # 1. Premium Üye -> Sınırsız
    if st.session_state.user and st.session_state.user['is_premium']:
        return True, "premium"
    
    # 2. Standart Üye -> Haftalık 3 Hak
    if st.session_state.user and not st.session_state.user['is_premium']:
        if st.session_state.user['daily_usage'] < 3:
            return True, "member"
        else:
            return False, "member_limit"

    # 3. Misafir -> Toplam 3 Hak
    if st.session_state.guest_usage < 3:
        return True, "guest"
    else:
        return False, "guest_limit"

def update_usage():
    if st.session_state.user:
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

# --- 5. SIDEBAR (Üyelik Paneli) ---
with st.sidebar:
    if st.session_state.user:
        user = st.session_state.user
        st.header(f"👤 {user['username']}")
        if user['is_premium']:
            st.success("🌟 PREMIUM")
        else:
            st.info("STANDART")
            kalan = 3 - user['daily_usage']
            st.progress(user['daily_usage'] / 3)
            st.caption(f"Haftalık Hak: {kalan}/3")
        
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()
    else:
        st.header("👤 Giriş / Kayıt")
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        with tab1:
            u = st.text_input("Kullanıcı Adı", key="l_u")
            p = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap"): login_user(u, p)
        with tab2:
            ru = st.text_input("Kullanıcı Adı", key="r_u")
            rp = st.text_input("Şifre", type="password", key="r_p")
            if st.button("Kayıt Ol"): register_user(ru, rp)

# --- 6. ANA EKRAN ---

st.title("🍿 CineMatch AI")

# LİMİT KONTROLÜ
izin_var, durum = check_limits()

# --- BURASI YENİ: PAYWALL EKRANI ---
if not izin_var:
    # Limit dolduysa arama çubuğunu gizle veya kilitle, yerine bu kutuyu göster
    st.markdown(
        """
        <div class='paywall-container'>
            <div class='paywall-header'>🚧 Ücretsiz Hakkınız Bitti!</div>
            <p style='font-size: 1.2em;'>3 filmlik deneme sürenizi doldurdunuz.</p>
            <p>Aradığınız o efsane filmi bulmak için beklemeyin.</p>
            <hr style='border-color: #ff4b4b; opacity: 0.3;'>
            <div class='paywall-price'>$0.99</div>
            <p style='color: #bbb;'>Sadece bir kahve parasına <b>SINIRSIZ</b> erişim.</p>
            <a href='https://www.buymeacoffee.com' target='_blank' class='paywall-btn'>🚀 PREMIUM AL VE DEVAM ET</a>
            <br><br>
            <p style='font-size: 0.9em; color: #888;'>Veya <a href='#' style='color: #888;'>giriş yaparak</a> haftalık 3 hak daha kazan.</p>
        </div>
        """, unsafe_allow_html=True
    )
    # Arama butonunu pasif yapıyoruz
    disable_search = True
else:
    disable_search = False


# ARAMA FORMU (Limit dolsa bile görünür, ama buton çalışmaz)
secilen_tur = st.selectbox("Tür Seçiniz:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Dram", "Suç"])
secilen_detay = st.text_area("Nasıl bir şey arıyorsun?", placeholder="Örn: Beyin yakan, sonu sürprizli, 2020 sonrası...")

col1, col2 = st.columns(2)
with col1:
    # Limit dolduysa buton disabled
    btn_normal = st.button("🚀 Film Bul", use_container_width=True, disabled=disable_search)
with col2:
    is_prem = st.session_state.user and st.session_state.user['is_premium']
    # Sevgili modu sadece premiumlara açık
    btn_couple = st.button("💑 Sevgili Modu", use_container_width=True, disabled=not is_prem)
    if not is_prem:
        st.caption("🔒 Sadece Premium")

# --- 7. FİLM GETİRME İŞLEMİ ---
if (btn_normal and not disable_search) or (btn_couple and is_prem):
    with st.spinner("Yapay zeka film seçiyor..."):
        try:
            # REST API (1.5 Flash - En Hızlı ve Ucuz)
            api_key = st.secrets["google"]["api_key"]
            model_name = "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            yasakli = ", ".join(st.session_state.gosterilen_filmler)
            context = "COUPLE MODE: Safe for date night." if btn_couple else "NORMAL MODE."
            
            prompt = f"""
            Role: Movie curator. Language: Turkish.
            Genre: {secilen_tur}. Details: {secilen_detay}. {context}
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
                
                # Kullanımı düş
                update_usage()
                
                # Sonuçları Göster
                cols = st.columns(3)
                for i, film in enumerate(filmler):
                    st.session_state.gosterilen_filmler.append(film['film_adi'])
                    with cols[i]:
                        st.image(get_movie_poster(film['film_adi']), use_container_width=True)
                        st.subheader(film['film_adi'])
                        st.caption(f"⭐ {film['puan']} | 📅 {film['yil']}")
                        st.info(film['neden'])
                
                # Misafir ise kalan hakkı söyle
                if not st.session_state.user:
                    kalan = 3 - st.session_state.guest_usage
                    if kalan > 0:
                        st.toast(f"Deneme hakkı: {kalan} kaldı!", icon="⏳")
                    else:
                        st.balloons() # Son hak bitince balonlar uçar, sonraki aramada paywall çıkar
                        
            elif resp.status_code == 429:
                st.error("Sunucu çok yoğun, lütfen bekleyin.")
            else:
                st.error("Bir hata oluştu.")
                
        except Exception as e:
            st.error(f"Hata: {e}")