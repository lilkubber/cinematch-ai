import streamlit as st
import google.generativeai as genai
import requests
from supabase import create_client, Client

# --- 1. SAYFA AYARLARI & TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; color: #e5e5e5; }
    .movie-card { background: #1a1a1a; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; text-align: center; min-height: 480px; }
    .stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; font-weight: bold; width: 100%; height: 45px; border-radius: 5px; }
    .premium-badge { background: #FFD700; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .movie-title { color: #E50914; font-size: 18px; font-weight: bold; margin-top: 10px; height: 50px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. BAĞLANTILAR (Secrets Kontrolü) ---
# Supabase Bağlantısı
supabase = None
if "supabase" in st.secrets:
    try:
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
else:
    st.warning("⚠️ Veritabanı (Supabase) ayarları eksik.")

# Gemini Konfigürasyonu
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("🚨 Gemini API Key bulunamadı!")

# --- 3. SESSION STATE & DİL ---
if 'user' not in st.session_state: st.session_state.user = None
if 'lang' not in st.session_state: st.session_state.lang = "TR"

texts = {
    "TR": {"welcome": "Hoş Geldin", "find": "FİLM BUL 🚀", "type": "Tür", "detail": "Detaylar", "login": "Giriş Yap", "register": "Kayıt Ol", "logout": "Çıkış"},
    "EN": {"welcome": "Welcome", "find": "FIND MOVIES 🚀", "type": "Genre", "detail": "Details", "login": "Login", "register": "Register", "logout": "Logout"}
}
T = texts[st.session_state.lang]

# --- 4. YARDIMCI FONKSİYONLAR ---
def get_movie_data(movie_name):
    """TMDB üzerinden gerçek poster ve puan çeker."""
    try:
        if "tmdb" in st.secrets:
            api_key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&language=tr-TR"
            res = requests.get(url, timeout=3).json()
            if res.get('results'):
                m = res['results'][0]
                return {
                    "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else None,
                    "puan": round(m.get('vote_average', 0), 1),
                    "ozet": m.get('overview', 'Özet bulunamadı.')[:150] + "..."
                }
    except: pass
    return None

# --- 5. SIDEBAR (Giriş & Üyelik & Dil) ---
with st.sidebar:
    st.title("🍿 CineMatch AI")
    st.session_state.lang = st.selectbox("🌐 Dil / Language", ["TR", "EN"])
    
    if st.session_state.user:
        u = st.session_state.user
        st.write(f"👤 {T['welcome']}, **{u['username']}**")
        if u.get('is_premium'): st.markdown('<span class="premium-badge">💎 PREMIUM</span>', unsafe_allow_html=True)
        if st.button(T['logout']):
            st.session_state.user = None
            st.rerun()
    elif supabase:
        auth_mode = st.radio("İşlem", [T['login'], T['register']])
        email = st.text_input("E-posta")
        pw = st.text_input("Şifre", type="password")
        if auth_mode == T['login']:
            if st.button(T['login']):
                res = supabase.table("users").select("*").eq("email", email).eq("password", pw).execute()
                if res.data:
                    st.session_state.user = res.data[0]
                    st.rerun()
                else: st.error("Hatalı bilgiler.")
        else:
            uname = st.text_input("Kullanıcı Adı")
            if st.button(T['register']):
                supabase.table("users").insert({"username": uname, "email": email, "password": pw, "is_premium": False}).execute()
                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")

# --- 6. ANA EKRAN & FİLM ÖNERİSİ ---
st.title("🎬 CineMatch AI")

c1, c2 = st.columns([1, 2])
with c1:
    tur = st.selectbox(T['type'], ["Aksiyon", "Bilim Kurgu", "Dram", "Komedi", "Korku", "Animasyon"])
with c2:
    detay = st.text_input(T['detail'], placeholder="Örn: 2024 yapımı, sürpriz sonlu...")

if st.button(T['find']):
    with st.status("🔍 Yapay zeka analiz ediyor...", expanded=True) as status:
        prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. SADECE film isimlerini 'Film1, Film2, Film3' şeklinde virgülle ayırarak yaz. Başka hiçbir şey yazma."
        
        response_text = ""
        # 404 Hatasını engellemek için Model Fallback (Yedekleme)
        for model_name in ['gemini-1.5-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    response_text = response.text
                    break
            except: continue
        
        if response_text:
            film_isimleri = [f.strip() for f in response_text.split(',') if len(f.strip()) > 1][:3]
            status.update(label="✅ Filmler Hazır!", state="complete", expanded=False)
            
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                    data = get_movie_data(isim)
                    if data and data['poster']:
                        st.image(data['poster'], use_container_width=True)
                    else:
                        st.markdown("<br><br>🖼️ Afiş Bulunamadı<br><br>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='movie-title'>{isim}</div>", unsafe_allow_html=True)
                    if data:
                        st.write(f"⭐ IMDb: {data['puan']}")
                        st.caption(data['ozet'])
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            status.update(label="❌ Hata Oluştu", state="error")
            st.error("Yapay zeka şu an yanıt veremiyor. Lütfen API Key ve internet bağlantınızı kontrol edin.")
