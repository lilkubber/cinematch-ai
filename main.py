import streamlit as st
import requests
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Safe", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; font-size: 18px; }
.movie-card { background-color: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px; }
.movie-title { font-size: 22px; font-weight: bold; color: #E50914; }
.movie-meta { font-size: 14px; color: #888; margin-bottom: 10px; }
.movie-rating { color: #FFD700; font-weight: bold; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİ YAPAY ZEKA FONKSİYONU ---
def get_safe_recommendations(prompt_text):
    # Secrets Kontrolü
    if "groq" not in st.secrets:
        st.error("❌ HATA: Secrets ayarlarında [groq] anahtarı yok!")
        return None
        
    api_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Yapay Zekaya "Bana JSON ver" diyoruz.
    # Puanı, yılı ve özeti yapay zeka kendi hafızasından yazacak.
    system_prompt = """
    Sen bir film uzmanısın. Türkçe cevap ver.
    Cevabın SADECE şu JSON formatında olmalı, başka hiçbir kelime etme:
    {
        "movies": [
            { "isim": "Film Adı", "yil": "2023", "puan": "8.5", "ozet": "İlgi çekici kısa özet." },
            { "isim": "Film Adı 2", "yil": "2022", "puan": "7.1", "ozet": "İlgi çekici kısa özet." },
            { "isim": "Film Adı 3", "yil": "2020", "puan": "9.0", "ozet": "İlgi çekici kısa özet." }
        ]
    }
    """
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"İstek: {prompt_text}. Bana en iyi 3 filmi öner."}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        # Timeout süresini artırdık (30 saniye) ki yarıda kesilip beyaz ekran olmasın
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            st.error(f"API Hatası: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Bağlantı Sorunu: {e}")
        return None

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch AI (Güvenli Mod)")
st.caption("Veriler doğrudan Yapay Zeka hafızasından çekiliyor.")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür Seç", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with col2:
    detay = st.text_input("Detay Gir", placeholder="Örn: Sürpriz sonlu, uzayda geçen...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Yapay zeka analiz ediyor..."):
        
        json_str = get_safe_recommendations(f"Tür: {tur}, Detay: {detay}")
        
        if json_str:
            try:
                # JSON Temizliği (Bazen yapay zeka başına ```json koyar, siliyoruz)
                if "```json" in json_str: json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str: json_str = json_str.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_str)
                filmler = data.get("movies", [])
                
                if filmler:
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        with cols[i]:
                            # Film Kartı Tasarımı
                            st.markdown(f"""
                            <div class="movie-card">
                                <div class="movie-title">{film['isim']}</div>
                                <div class="movie-meta">📅 {film['yil']}</div>
                                <div class="movie-rating">⭐ {film['puan']}/10</div>
                                <p style="font-size:14px; margin-top:10px;">{film['ozet']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.warning("Uygun film bulunamadı.")
            except Exception as e:
                st.error("Veri işleme hatası.")
                st.code(json_str)
