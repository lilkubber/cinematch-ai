import streamlit as st
import requests
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Tasarım
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; font-size: 18px; }
.movie-title { font-size: 18px; font-weight: bold; margin-top: 10px; color: #fff; }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

def get_groq_json(prompt_text):
    if "groq" not in st.secrets:
        st.error("Groq API Key bulunamadı! Secrets ayarlarını kontrol et.")
        return None
        
    api_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        "response_format": {"type": "json_object"} 
    }
    
    try:
        res = requests.post(url, headers=headers, json=data, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            st.error(f"AI Hatası: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

def get_poster(movie_name):
    try:
        # Eğer TMDB anahtarı yoksa direkt yedek resme git, çökme
        if "tmdb" not in st.secrets:
            return "https://via.placeholder.com/500x750?text=Poster+Yok"

        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url, timeout=2).json()
        
        if res['results']:
            return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except:
        pass
    return "https://via.placeholder.com/500x750?text=Resim+Yok"

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch AI")
st.caption("Yapay zeka film önerisi.")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram", "Romantik"])
with col2:
    detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Filmler seçiliyor..."):
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}.
        Return EXACTLY 3 movies. JSON Format:
        {{
            "movies": [
                {{ "isim": "Film Adı", "yil": "2023", "puan": "8.5", "ozet": "Kısa açıklama..." }}
            ]
        }}
        """
        
        json_data = get_groq_json(prompt)
        
        if json_data:
            try:
                data = json.loads(json_data)
                filmler = data.get("movies", [])
                
                if filmler:
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        with cols[i]:
                            st.image(get_poster(film['isim']), use_container_width=True)
                            st.markdown(f"<div class='movie-title'>{film['isim']} ({film['yil']})</div>", unsafe_allow_html=True)
                            st.caption(f"⭐ {film['puan']}")
                            st.info(film['ozet'])
                else:
                    st.warning("Film bulunamadı.")
            except:
                st.error("Veri işleme hatası.")
