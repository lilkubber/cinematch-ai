import streamlit as st
import json
from openai import OpenAI

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Pro", page_icon="🎬", layout="wide")

# CSS: Resim yüklenemezse gri bir kutu görünmesi için
st.markdown("""
<style>
.stApp { background-color: #050505; color: #ffffff; }
.movie-card { 
    background: #1a1a1a; 
    padding: 15px; 
    border-radius: 12px; 
    border: 1px solid #333; 
    min-height: 400px;
}
.placeholder-poster {
    background: #333;
    height: 300px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #555;
    font-size: 40px;
}
.movie-title { font-size: 20px; font-weight: bold; color: #E50914; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİ VERİ ÇEKME (BEYAZ EKRAN ÖNLEYİCİ) ---
def get_tmdb_data_safe(movie_name):
    """Resim çekme işlemini 'requests' kütüphanesi ile ama hata yutarak yapar."""
    import requests # Sadece burada çağırıyoruz
    try:
        if "tmdb" not in st.secrets:
            return None
            
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&language=tr-TR"
        
        # Sadece 2 saniye bekle, cevap gelmezse 'yok' say (Beyaz ekranı engeller)
        response = requests.get(url, timeout=2.5)
        
        if response.status_code == 200:
            res = response.json()
            if res.get('results'):
                movie = res['results'][0]
                return {
                    "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
                    "puan": movie.get('vote_average', 'N/A')
                }
    except:
        return None # Hata olsa da sessiz kal, siteyi çökertme
    return None

# --- 3. ANA ARAYÜZ ---
st.title("🎬 CineMatch Pro")

c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Dram", "Komedi", "Korku"])
with c2: detay = st.text_input("Detay", placeholder="Örn: Christopher Nolan tarzı...")

if st.button("FİLM BUL 🚀"):
    # OpenAI motoru ile Groq bağlantısı (En sağlamı buydu)
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=st.secrets["groq"]["api_key"])
    
    with st.status("🎬 Filmler hazırlanıyor...", expanded=True) as status:
        try:
            prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. Sadece isimlerini 'Film 1, Film 2, Film 3' şeklinde virgülle ayırarak yaz."
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_text = response.choices[0].message.content.strip()
            # Film isimlerini temizle
            film_isimleri = [f.strip() for f in raw_text.replace('\n', ',').split(',') if len(f.strip()) > 2][:3]
            
            status.update(label="✅ Filmler Bulundu!", state="complete", expanded=False)
            
            # Ekrana Basma Bölümü
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    with st.container():
                        st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                        
                        # Resim çekme denemesi
                        data = get_tmdb_data_safe(isim)
                        
                        if data and data['poster']:
                            st.image(data['poster'], use_container_width=True)
                        else:
                            # Resim yüklenemezse veya hata verirse gri kutu göster
                            st.markdown('<div class="placeholder-poster">🎬</div>', unsafe_allow_html=True)
                        
                        st.markdown(f"<div class='movie-title'>{isim}</div>", unsafe_allow_html=True)
                        if data:
                            st.write(f"⭐ Puan: {data['puan']}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Sistemde bir aksama oldu, lütfen tekrar deneyin.")
