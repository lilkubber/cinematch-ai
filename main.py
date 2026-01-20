import streamlit as st
import http.client
import json
import urllib.parse # URL uyumlu hale getirmek için (standart kütüphane)

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Pro", page_icon="🍿", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; font-size: 18px; }
.movie-title { font-size: 18px; font-weight: bold; margin-top: 10px; color: #fff; }
</style>
""", unsafe_allow_html=True)

# --- 2. HAFİF FONKSİYONLAR (http.client ile) ---

def get_groq_json(prompt_text):
    """AI'dan JSON formatında veri ister (Kütüphanesiz)."""
    if "groq" not in st.secrets:
        st.error("Groq API Key eksik!")
        return None
        
    api_key = st.secrets["groq"]["api_key"]
    conn = http.client.HTTPSConnection("api.groq.com")
    
    # JSON Formatını zorlayan Prompt
    system_prompt = """
    Sen bir film asistanısın. Türkçe cevap ver.
    Cevabın SADECE geçerli bir JSON formatında olmalı.
    Şu formatı kullan:
    {
        "movies": [
            { "isim": "Film Adı", "yil": "2023", "puan": "8.5", "ozet": "Kısa özet." }
        ]
    }
    """
    
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"İstek: {prompt_text}. Bana tam 3 film öner."}
        ],
        "response_format": {"type": "json_object"}
    })
    
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    
    try:
        conn.request("POST", "/openai/v1/chat/completions", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            return json.loads(data.decode("utf-8"))['choices'][0]['message']['content']
        return None
    except:
        return None
    finally:
        conn.close()

def get_poster_atomic(movie_name):
    """TMDB'den poster çeker (requests kullanmadan, saf python ile)."""
    try:
        if "tmdb" not in st.secrets:
            return "https://via.placeholder.com/500x750?text=Ayarlar+Eksik"
            
        api_key = st.secrets["tmdb"]["api_key"]
        # Film adını URL formatına çevir (Örn: "Baba 2" -> "Baba%202")
        safe_name = urllib.parse.quote(movie_name)
        
        conn = http.client.HTTPSConnection("api.themoviedb.org")
        conn.request("GET", f"/3/search/movie?api_key={api_key}&query={safe_name}")
        
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            json_data = json.loads(data.decode("utf-8"))
            if json_data['results']:
                path = json_data['results'][0]['poster_path']
                if path:
                    return f"https://image.tmdb.org/t/p/w500{path}"
        
        conn.close()
    except:
        pass
        
    return "https://via.placeholder.com/500x750?text=Resim+Yok"

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch AI")
st.caption("Atom Pro Modu: Hızlı, Posterli ve Güvenli.")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram", "Romantik", "Gerilim"])
with col2:
    detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı, sürpriz sonlu...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Filmler ve posterler hazırlanıyor..."):
        
        json_res = get_groq_json(f"Tür: {tur}, Detay: {detay}")
        
        if json_res:
            try:
                # Gelen veriyi JSON'a çevir
                data = json.loads(json_res)
                filmler = data.get("movies", [])
                
                if filmler:
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        with cols[i]:
                            # Posteri hafif yöntemle çek
                            img_url = get_poster_atomic(film['isim'])
                            
                            st.image(img_url, use_container_width=True)
                            st.markdown(f"<div class='movie-title'>{film['isim']} ({film['yil']})</div>", unsafe_allow_html=True)
                            st.caption(f"⭐ IMDb: {film['puan']}")
                            st.info(film['ozet'])
                else:
                    st.warning("Film bulunamadı.")
            except Exception as e:
                st.error("Veri işlenirken hata oluştu.")
        else:
            st.error("Bağlantı hatası.")
