import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🎬", layout="wide")

# --- 2. FONKSİYONLAR ---
def get_movie_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        response = requests.get(url).json()
        
        if response['results']:
            poster_path = response['results'][0]['poster_path']
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
        else:
            return "https://via.placeholder.com/500x750?text=Resim+Yok"
    except:
        return "https://via.placeholder.com/500x750?text=Hata"

# --- 3. BAĞLANTILAR ---
try:
    # Supabase Bağlantısı
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    
    # Google AI Bağlantısı
    genai.configure(api_key=st.secrets["google"]["api_key"])
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- 4. ARAYÜZ TASARIMI ---
st.title("🎬 CineMatch AI")
st.caption("Yapay Zeka Destekli Film Öneri Asistanı")

with st.sidebar:
    st.header("Film Kriterleri")
    with st.form("film_formu"):
        ad = st.text_input("Adın:", placeholder="Örn: Kubilay")
        tur = st.selectbox("Tür:", ["Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"])
        detay = st.text_area("Özel İstekler:", placeholder="Örn: 2020 sonrası olsun, sürpriz sonlu olsun...")
        btn = st.form_submit_button("✨ Filmleri Getir")
    
    st.divider()
    st.markdown("### 📋 Son İstekler")
    if st.button("Geçmişi Yenile"):
        try:
            data = supabase.table("users").select("*").order("created_at", desc=True).limit(5).execute()
            for satir in data.data:
                st.text(f"👤 {satir['username']}")
                st.caption(f"{satir['favorite_genre']}")
                st.markdown("---")
        except:
            st.write("Veri yok.")

# --- 5. ANA AKIŞ ---
if btn and ad:
    st.info("🧠 Yapay zeka filmleri seçiyor ve posterleri indiriyor...")
    
    # A. Veritabanına Kayıt
    try:
        supabase.table("users").insert({"username": ad, "favorite_genre": f"{tur} - {detay}"}).execute()
    except:
        pass

    # B. Gemini Prompt
    prompt = f"""
    Kullanıcı: {ad}
    Tür: {tur}
    Detay: {detay}
    
    Bana bu kriterlere uyan 3 adet film öner.
    Cevabı SADECE şu JSON formatında ver:
    [
        {{
            "film_adi": "Filmin Orijinal Adı",
            "turkce_ad": "Filmin Türkçe Adı",
            "yil": "2023",
            "puan": "8.5",
            "neden": "Kısa öneri nedeni."
        }},
        ...
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON Temizliği (Markdown tagleri gelirse temizle)
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        filmler = json.loads(text_response)
        
        st.success("İşte senin için seçtiklerim! 👇")
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for i, film in enumerate(filmler):
            with cols[i]:
                poster_url = get_movie_poster(film['film_adi'])
                st.image(poster_url, use_container_width=True)
                st.subheader(f"{film['turkce_ad']}")
                st.caption(f"📅 {film['yil']} | ⭐ {film['puan']}")
                st.info(f"{film['neden']}")
                
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")