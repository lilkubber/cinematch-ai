import streamlit as st
import requests
import json

# --- 1. BASİT AYARLAR ---
st.set_page_config(page_title="CineMatch Lite", page_icon="🍿")

# Hata ayıklama için basit CSS
st.markdown("""
<style>
.stApp { background-color: #111; color: #fff; }
.stButton>button { width: 100%; background-color: #e50914; color: white; height: 50px; font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

def get_groq_data(prompt):
    """Groq API'ye bağlanır."""
    try:
        # Secrets kontrolü
        if "groq" not in st.secrets:
            st.error("Secrets dosyasında Groq anahtarı yok!")
            return None
            
        api_key = st.secrets["groq"]["api_key"]
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"} # JSON Zorlama
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            st.error(f"Groq Hatası: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Groq Bağlantı Hatası: {e}")
        return None

def get_poster_url(movie_name):
    """TMDB'den resim çeker, hata verirse boş resim döner."""
    try:
        if "tmdb" in st.secrets:
            api_key = st.secrets["tmdb"]["api_key"]
            url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
            # Timeout süresini kısalttık ki site donmasın
            res = requests.get(url, timeout=2).json()
            if res['results']:
                return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
    except:
        pass
    return "https://via.placeholder.com/500x750?text=Poster+Yok"

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch Lite")
st.caption("Veritabanı yok, giriş yok. Sadece film.")

col1, col2 = st.columns(2)
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with col2:
    detay = st.text_input("Detay", "Sürpriz sonlu, 2024...")

if st.button("FİLM BUL 🚀"):
    st.write("⏳ Yapay zeka düşünüyor...")
    
    prompt = f"""
    Sen bir film uzmanısın. Türkçe cevap ver.
    Tür: {tur}. Detay: {detay}.
    Bana tam olarak 3 film öner.
    Cevabın SADECE şu JSON formatında olsun:
    {{
        "movies": [
            {{ "isim": "Film Adı", "yil": "2023", "puan": "8.5", "neden": "Açıklama" }},
            {{ "isim": "Film Adı 2", "yil": "2022", "puan": "7.0", "neden": "Açıklama" }},
            {{ "isim": "Film Adı 3", "yil": "2024", "puan": "9.0", "neden": "Açıklama" }}
        ]
    }}
    """
    
    json_str = get_groq_data(prompt)
    
    if json_str:
        try:
            # JSON Temizliği
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            
            st.write("✅ Film listesi alındı, posterler yükleniyor...")
            
            cols = st.columns(3)
            for i, film in enumerate(data.get("movies", [])):
                with cols[i]:
                    img_url = get_poster_url(film['isim'])
                    st.image(img_url, use_container_width=True)
                    st.subheader(f"{film['isim']} ({film['yil']})")
                    st.write(f"⭐ {film['puan']}")
                    st.info(film['neden'])
                    
        except Exception as e:
            st.error(f"Veri işleme hatası: {e}")
            st.text("Gelen Veri:")
            st.code(json_str)
