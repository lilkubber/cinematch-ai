import streamlit as st
import json
import requests
from openai import OpenAI

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Pro", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #050505; color: #ffffff; }
.movie-card { background: #1a1a1a; padding: 15px; border-radius: 12px; border: 1px solid #333; height: 100%; transition: 0.3s; }
.movie-card:hover { border-color: #E50914; transform: translateY(-5px); }
.imdb-puan { color: #f5c518; font-weight: bold; font-size: 18px; }
.movie-title { font-size: 20px; font-weight: bold; color: #fff; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. YARDIMCI FONKSİYONLAR ---

def get_real_data(movie_name):
    """TMDB üzerinden gerçek poster ve puanı çeker."""
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&language=tr-TR"
        res = requests.get(url, timeout=5).json()
        
        if res['results']:
            movie = res['results'][0]
            return {
                "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie['poster_path'] else None,
                "puan": round(movie['vote_average'], 1),
                "ozet": movie['overview'][:150] + "..." if movie['overview'] else "Özet bulunamadı."
            }
    except:
        pass
    return None

# --- 3. ANA AKIŞ ---
st.title("🎬 CineMatch Pro")
st.caption("Gerçek IMDb Verileri ve Afişler")

# Sidebar veya Üst Panel Seçimleri
col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Film Türü", ["Bilim Kurgu", "Aksiyon", "Dram", "Komedi", "Korku", "Suç"])
with col2:
    detay = st.text_input("Nasıl bir film istersin?", placeholder="Örn: Christopher Nolan tarzı, beyin yakan...")

if st.button("FİLMLERİ GETİR 🚀"):
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=st.secrets["groq"]["api_key"])
    
    with st.spinner("Yapay zeka en iyi filmleri seçiyor..."):
        prompt = f"Bana {tur} türünde, şu detaylara uygun 3 film öner: {detay}. Sadece film isimlerini bir liste olarak ver. Yanına açıklama yazma."
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            # AI'dan gelen cevabı satırlara böl
            oneriler = response.choices[0].message.content.strip().split('\n')
            # Temizlik (Numaraları siler)
            film_isimleri = [f.split('.')[-1].strip() for f in oneriler if len(f) > 3][:3]
            
            # Görselleştirme
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    data = get_real_data(isim)
                    if data:
                        if data['poster']:
                            st.image(data['poster'], use_container_width=True)
                        st.markdown(f"<div class='movie-title'>{isim}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='imdb-puan'>⭐ {data['puan']}</span>", unsafe_allow_html=True)
                        st.write(data['ozet'])
                    else:
                        st.warning(f"{isim} için detay bulunamadı.")
        except Exception as e:
            st.error(f"Hata oluştu: {e}")
