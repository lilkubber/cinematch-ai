import streamlit as st
import json
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# --- 2. HATA YAKALAYICI (BEYAZ EKRAN ÖNLEYİCİ) ---
try:
    import requests
except ImportError:
    st.error("🚨 KRİTİK HATA: 'requests' kütüphanesi bulunamadı!")
    st.warning("👉 ÇÖZÜM: 'requirements.txt' dosyasının içine 'requests' yazıp kaydetmen lazım.")
    st.stop() # Kodun geri kalanını çalıştırma, çökmesin.

# --- 3. TASARIM ---
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. FONKSİYONLAR ---
def get_groq_json(prompt_text):
    if "groq" not in st.secrets:
        st.error("❌ HATA: Secrets ayarlarında [groq] anahtarı yok.")
        return None
    
    try:
        api_key = st.secrets["groq"]["api_key"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt_text}],
            "response_format": {"type": "json_object"} 
        }
        res = requests.post(url, headers=headers, json=data, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            st.error(f"API Hatası: {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

def get_poster(movie_name):
    try:
        if "tmdb" in st.secrets:
            api_key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
            res = requests.get(url, timeout=2).json()
            if res['results']: return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except: pass
    return "https://via.placeholder.com/500x750?text=Resim+Yok"

# --- 5. ARAYÜZ ---
st.title("🍿 CineMatch AI")

col1, col2 = st.columns([1, 2])
with col1: tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with col2: detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Aranıyor..."):
        prompt = f"""
        Role: Movie curator. Language: Turkish. Genre: {tur}. Details: {detay}.
        Return EXACTLY 3 movies. JSON Format: {{ "movies": [ {{ "isim": "Ad", "yil": "2023", "puan": "8.0", "ozet": "..." }} ] }}
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
                            st.subheader(f"{film['isim']}")
                            st.caption(f"⭐ {film['puan']}")
                            st.info(film['ozet'])
                else: st.warning("Film bulunamadı.")
            except: st.error("Veri hatası.")
