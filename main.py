import streamlit as st
import google.generativeai as genai
import requests
from supabase import create_client, Client

# --- 1. AYARLAR & TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

def local_css():
    st.markdown("""
    <style>
    .stApp { background-color: #0e0e0e; color: #e5e5e5; }
    .movie-card { background: #1a1a1a; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; min-height: 450px; }
    .stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; font-weight: bold; width: 100%; }
    .premium-badge { background: #FFD700; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .movie-title { color: #E50914; font-size: 18px; font-weight: bold; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. BAĞLANTILAR (Gemini & Supabase) ---
# Gemini Ayarı
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("Gemini API Key bulunamadı!")

# Supabase Ayarı
supabase = None
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except:
    st.error("Veritabanı bağlantısı kurulamadı.")

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'lang' not in st.session_state: st.session_state.lang = "TR"

# --- 4. DİL DESTEĞİ ---
texts = {
    "TR": {"welcome": "Hoş Geldin", "find": "FİLM BUL", "type": "Tür", "detail": "Detay", "login": "Giriş Yap", "register": "Kayıt Ol", "logout": "Çıkış"},
    "EN": {"welcome": "Welcome", "find": "FIND MOVIE", "type": "Genre", "detail": "Detail", "login": "Login", "register": "Sign Up", "logout": "Logout"}
}
T = texts[st.session_state.lang]

# --- 5. YARDIMCI FONKSİYONLAR ---
def get_poster_data(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&language=tr-TR"
        res = requests.get(url, timeout=3).json()
        if res['results']:
            m = res['results'][0]
            return {
                "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m['poster_path'] else None,
                "puan": round(m['vote_average'], 1),
                "ozet": m['overview'][:150] + "..." if m['overview'] else "Özet yok."
            }
    except: return None
    return None

# --- 6. SIDEBAR (Giriş/Kayıt/Dil) ---
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
    else:
        auth_mode = st.radio("Hesap", [T['login'], T['register']])
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

# --- 7. ANA EKRAN ---
st.title("🎬 CineMatch")

c1, c2 = st.columns([1, 2])
with c1: 
    tur = st.selectbox(T['type'], ["Aksiyon", "Bilim Kurgu", "Dram", "Komedi", "Korku", "Animasyon"])
with c2: 
    detay = st.text_input(T['detail'], placeholder="Örn: Uzayda geçen, gerilimli...")

if st.button(T['find']):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.status("🔍 Gemini filmleri seçiyor...", expanded=True) as status:
        prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. SADECE film isimlerini 'Film1, Film2, Film3' şeklinde virgülle ayırarak yaz."
        
        try:
            response = model.generate_content(prompt)
            film_isimleri = [f.strip() for f in response.text.split(',') if len(f.strip()) > 1][:3]
            status.update(label="✅ Filmler Bulundu!", state="complete", expanded=False)
            
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                    data = get_poster_data(isim)
                    
                    if data and data['poster']:
                        st.image(data['poster'], use_container_width=True)
                    else:
                        st.markdown("🖼️ *Afiş Yok*")
                    
                    st.markdown(f"<div class='movie-title'>{isim}</div>", unsafe_allow_html=True)
                    if data:
                        st.write(f"⭐ IMDb: {data['puan']}")
                        st.caption(data['ozet'])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
        except Exception as e:
            st.error("Gemini şu an yanıt veremiyor, lütfen az sonra tekrar deneyin.")
