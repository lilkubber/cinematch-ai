import streamlit as st
import requests
import json
import time

# --- AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# CSS (Netflix Tarzı)
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stTextInput > div > div > input { background-color: #222; color: white; border: 1px solid #444; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---

def get_groq_response(prompt):
    """Sadece Groq API kullanır, veritabanı yok."""
    try:
        # Hata yakalama: Eğer secrets yoksa uyarı ver ama çökme
        if "groq" not in st.secrets:
            st.error("Lütfen Streamlit Secrets ayarına [groq] anahtarını ekleyin.")
            return None
            
        key = st.secrets["groq"]["api_key"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            st.error(f"Yapay Zeka Hatası: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

def get_poster(movie_name):
    """Poster yoksa boş dön, çökme."""
    try:
        if "tmdb" in st.secrets:
            key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={key}&query={movie_name}"
            res = requests.get(url, timeout=2).json()
            if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except: pass
    return "https://via.placeholder.com/500x750?text=Poster+Yok"

# --- ARAYÜZ ---

# Sidebar (Süs Amaçlı Giriş - Fonksiyonsuz)
with st.sidebar:
    st.title("🍿 CineMatch")
    st.info("Bu sürümde üyelik sistemi geçici olarak devre dışıdır.")
    st.markdown("---")
    st.markdown("<div style='background:#FFD700; color:black; padding:10px; border-radius:8px; text-align:center;'><b>👑 Premium</b><br>Yakında</div>", unsafe_allow_html=True)

st.title("🍿 CineMatch AI")
st.caption("Veritabanı bağımsız, sadece yapay zeka.")

# Form
c1, c2 = st.columns([1, 2])
with c1: tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with c2: detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu...")

if st.button("FİLM BUL 🚀", use_container_width=True):
    with st.spinner("Yapay zeka film seçiyor..."):
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}.
        Return EXACTLY 3 movies. JSON Format:
        {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Kısa açıklama" }} ] }}
        """
        
        json_res = get_groq_response(prompt)
        
        if json_res:
            try:
                # JSON Temizliği
                if "```json" in json_res: json_res = json_res.split("```json")[1].split("```")[0].strip()
                elif "```" in json_res: json_res = json_res.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_res)
                filmler = data.get("movies", [])
                
                if filmler:
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        with cols[i]:
                            st.image(get_poster(film['film_adi']), use_container_width=True)
                            st.subheader(f"{film['film_adi']}")
                            st.caption(f"⭐ {film['puan']} | 📅 {film['yil']}")
                            st.info(film['neden'])
                else:
                    st.warning("Uygun film bulunamadı.")
            except Exception as e: 
                st.error(f"Veri işleme hatası: {e}")
                st.code(json_res)
