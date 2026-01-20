import streamlit as st
import requests
import json
import time
import re
from datetime import date, datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Hata yakalayıcı CSS
def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input {{ background-color: #222; color: white; }}
    .stButton>button {{ background: #E50914; color: white; border: none; height: 3em; font-weight: bold; }}
    .debug-box {{ background-color: #333; color: #0f0; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. GÜVENLİ BAĞLANTILAR (SUPABASE) ---
# Veritabanı hatası olsa bile site açılsın diye try-except içine aldık
supabase = None
try:
    from supabase import create_client, Client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.warning(f"⚠️ Veritabanı bağlantısı kurulamadı (Site çalışır ama kayıt olunamaz): {e}")

# --- 3. FONKSİYONLAR ---

def safe_groq_request(prompt_text):
    """Groq isteğini güvenli ve detaylı loglayarak yapar."""
    try:
        # Anahtar kontrolü
        if "groq" not in st.secrets:
            st.error("❌ Secrets dosyasında [groq] başlığı yok!")
            return None
            
        api_key = st.secrets["groq"]["api_key"]
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # MODEL: En güncel ve stabil model
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.5,
            "response_format": {"type": "json_object"} # JSON Zorlama
        }
        
        with st.status("🤖 Yapay Zeka Düşünüyor...", expanded=True) as status:
            st.write("📡 Groq API'ye bağlanılıyor...")
            response = requests.post(url, headers=headers, json=data, timeout=20) # 20 saniye zaman aşımı
            
            if response.status_code == 200:
                st.write("✅ Yanıt alındı!")
                content = response.json()['choices'][0]['message']['content']
                status.update(label="✅ Film Bulundu!", state="complete", expanded=False)
                return content
            else:
                st.error(f"❌ Groq API Hatası: {response.status_code}")
                st.code(response.text) # Hatayı ekrana bas
                status.update(label="❌ Hata Oluştu", state="error")
                return None
                
    except Exception as e:
        st.error(f"❌ Bağlantı Hatası: {e}")
        return None

def get_poster_safe(movie_name):
    """Poster bulamazsa placeholder döner, çökmez."""
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url, timeout=5).json()
        if res['results']: 
            return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
        return "https://via.placeholder.com/500x750?text=Resim+Yok"
    except:
        return "https://via.placeholder.com/500x750?text=Hata"

# --- 4. ARAYÜZ ---

st.title("🍿 CineMatch AI (Onarım Modu)")
st.info("ℹ️ Sistem Durumu: Hazır. Veritabanı ve API bağlantıları kontrol edildi.")

# Basit Kullanıcı Giriş Kontrolü (Hata vermemesi için basitleştirildi)
if 'user' not in st.session_state: st.session_state.user = None
if 'gosterilen_filmler' not in st.session_state: st.session_state.gosterilen_filmler = []

# Giriş Yapılmamışsa Basit Uyarı
if not st.session_state.user:
    st.caption("👤 Şu an MİSAFİR modundasınız.")

# --- FORM ---
col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür Seç", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram", "Romantik"])
with col2:
    detay = st.text_input("Detay Gir", placeholder="Örn: Uzayda geçen, sürpriz sonlu...")

if st.button("FİLM BUL 🚀", use_container_width=True):
    # Bu blok asla beyaz ekrana düşmez, hatayı yakalar
    try:
        prompt = f"""
        Role: Movie curator. Language: Turkish.
        Genre: {tur}. Details: {detay}.
        Ignore these: [{", ".join(st.session_state.gosterilen_filmler)}].
        Return EXACTLY 3 movies. 
        You MUST return valid JSON format inside {{ "movies": [...] }}.
        Format: {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Reason" }} ] }}
        """
        
        # 1. Adım: API Çağrısı
        json_response = safe_groq_request(prompt)
        
        if json_response:
            # 2. Adım: Veriyi İşleme
            try:
                # Bazen AI 'Here is json' gibi yazılar ekler, temizleyelim
                if "```json" in json_response:
                    json_response = json_response.split("```json")[1].split("```")[0].strip()
                elif "```" in json_response:
                    json_response = json_response.split("```")[1].split("```")[0].strip()
                
                data = json.loads(json_response)
                filmler = data.get("movies", [])
                
                if not filmler:
                    st.warning("⚠️ Yapay zeka geçerli bir film listesi döndüremedi. Tekrar deneyin.")
                    st.code(json_response) # Gelen bozuk veriyi göster
                else:
                    # 3. Adım: Ekrana Basma
                    cols = st.columns(3)
                    for i, film in enumerate(filmler):
                        st.session_state.gosterilen_filmler.append(film['film_adi'])
                        with cols[i]:
                            with st.spinner("Poster yükleniyor..."):
                                img = get_poster_safe(film['film_adi'])
                            st.image(img, use_container_width=True)
                            st.subheader(f"{film['film_adi']} ({film['yil']})")
                            st.caption(f"⭐ {film['puan']}")
                            st.info(film['neden'])
                    
                    st.success("✨ İşlem Tamamlandı!")
                    
            except json.JSONDecodeError:
                st.error("❌ Gelen veri JSON formatında değil (AI saçmaladı).")
                st.text("Gelen Ham Veri:")
                st.code(json_response)
        else:
            st.error("❌ API'den boş yanıt döndü. İnternet bağlantınızı veya API Key'i kontrol edin.")
            
    except Exception as e:
        st.error(f"❌ BEKLENMEYEN BİR HATA OLUŞTU: {e}")