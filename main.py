import streamlit as st
import requests
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Tasarım (Netflix Stili)
st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; font-size: 18px; border-radius: 4px; }
.movie-card { background-color: #1f1f1f; padding: 15px; border-radius: 8px; height: 100%; }
.movie-title { font-size: 18px; font-weight: bold; margin-bottom: 5px; color: #fff; }
.rating { color: #46d369; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

def get_groq_data(prompt_text):
    """Groq API'den güvenli veri çeker."""
    if "groq" not in st.secrets:
        st.error("Groq API Key eksik!")
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
        
        # Timeout süresini artırdık ki cevap gelmeden kapanmasın
        res = requests.post(url, headers=headers, json=data, timeout=15)
        
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None
    except:
        return None

def get_poster_safe(movie_name):
    """Poster bulamazsa ASLA çökmez, yedek resim döner."""
    placeholder = "https://via.placeholder.com/500x750/000000/FFFFFF?text=Resim+Yok"
    
    try:
        if "tmdb" not in st.secrets:
            return placeholder

        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        
        # Timeout'u kısa tutuyoruz (2 saniye). Cevap vermezse hemen geç.
        res = requests.get(url, timeout=2)
        
        if res.status_code == 200:
            data = res.json()
            if data['results'] and data['results'][0]['poster_path']:
                return f"https://image.tmdb.org/t/p/w500{data['results'][0]['poster_path']}"
                
    except:
        pass # Hata olursa sessiz kal ve placeholder dön
        
    return placeholder

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch AI")
st.caption("Yapay zeka destekli film öneri asistanı.")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram", "Romantik", "Gerilim"])
with col2:
    detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu, ödüllü...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Yapay zeka analiz yapıyor..."):
        
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}.
        Return EXACTLY 3 movies.
        JSON Format:
        {{
            "movies": [
                {{ "isim": "Film Adı", "yil": "2023", "puan": "8.5", "ozet": "Çok kısa açıklama." }},
                {{ "isim": "Film Adı", "yil": "2022", "puan": "7.2", "ozet": "Çok kısa açıklama." }},
                {{ "isim": "Film Adı", "yil": "2024", "puan": "9.0", "ozet": "Çok kısa açıklama." }}
            ]
        }}
        """
        
        json_res = get_groq_data(prompt)
        
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
                            # Posteri güvenli fonksiyonla al
                            img_url = get_poster_safe(film['isim'])
                            
                            # Kart Görünümü
                            st.image(img_url, use_container_width=True)
                            st.markdown(f"<div class='movie-title'>{film['isim']}</div>", unsafe_allow_html=True)
                            st.caption(f"📅 {film['yil']} | ⭐ {film['puan']}")
                            st.info(film['ozet'])
                else:
                    st.warning("Uygun film bulunamadı.")
            except:
                st.error("Veri işlenirken hata oluştu.")
        else:
            st.error("Bağlantı hatası veya zaman aşımı.")
