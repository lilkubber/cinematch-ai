import streamlit as st
import google.generativeai as genai
import requests
from supabase import create_client, Client

# --- 1. AYARLAR & TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Tasarımı Sabitleyelim
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.movie-card { background: #1a1a1a; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; text-align: center; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; font-weight: bold; width: 100%; height: 50px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BAĞLANTILAR ---
# Gemini Ayarı - En sağlam model ismini kullanıyoruz
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("Secrets: Gemini API Key eksik!")

# Supabase Ayarı
supabase = None
if "supabase" in st.secrets:
    try:
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        st.error("Veritabanı bağlantısı kurulamadı.")

# --- 3. FONKSİYONLAR ---
def get_poster_safe(movie_name):
    """TMDB'den poster çeker."""
    try:
        if "tmdb" in st.secrets:
            api_key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&language=tr-TR"
            res = requests.get(url, timeout=3).json()
            if res['results']:
                path = res['results'][0]['poster_path']
                return f"https://image.tmdb.org/t/p/w500{path}"
    except: pass
    return None

# --- 4. ANA ARAYÜZ ---
st.title("🎬 CineMatch AI")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Film Türü", ["Aksiyon", "Bilim Kurgu", "Dram", "Komedi", "Korku"])
with col2:
    detay = st.text_input("Nasıl bir film istersin?", placeholder="Örn: Christopher Nolan tarzı...")

if st.button("FİLM BUL 🚀"):
    # Hata uyarısı aldığımız model ismini 'gemini-1.5-flash' yerine 'gemini-1.5-pro' veya 'gemini-1.5-flash-latest' yapıyoruz
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    with st.status("🔍 Yapay zeka filmleri seçiyor...", expanded=True) as status:
        try:
            prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. SADECE film isimlerini 'Film1, Film2, Film3' şeklinde virgülle ayırarak yaz. Başka hiçbir şey yazma."
            
            response = model.generate_content(prompt)
            
            if response and response.text:
                film_isimleri = [f.strip() for f in response.text.split(',') if len(f.strip()) > 1][:3]
                status.update(label="✅ Öneriler Hazır!", state="complete", expanded=False)
                
                cols = st.columns(3)
                for i, isim in enumerate(film_isimleri):
                    with cols[i]:
                        st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                        poster_url = get_poster_safe(isim)
                        if poster_url:
                            st.image(poster_url, use_container_width=True)
                        else:
                            st.write("🖼️ Afiş Bulunamadı")
                        st.subheader(isim)
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("Yapay zeka yanıt vermedi, lütfen tekrar deneyin.")
                
        except Exception as e:
            status.update(label="❌ Hata!", state="error")
            st.error(f"Teknik Hata: {e}")
