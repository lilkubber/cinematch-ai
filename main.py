import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# --- CSS YÜKLEME FONKSİYONU ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS dosyası bulunamadı: {file_name}")

# CSS Dosyasını Çağır
local_css("style.css")

# --- FONKSİYONLAR ---
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

# --- BAĞLANTILAR ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    genai.configure(api_key=st.secrets["google"]["api_key"])
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- ARAYÜZ ---
# Başlığı Ortala ve İkon Ekle
st.markdown("<h1>🍿 CineMatch AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #bbb; font-size: 1.2rem;'>Yapay Zeka Destekli Kişisel Sinema Asistanın</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Film Kriterleri")
    with st.form("film_formu"):
        ad = st.text_input("Adın:", placeholder="İsminiz...")
        tur = st.selectbox("Tür:", ["Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"])
        detay = st.text_area("Özel İstekler:", placeholder="Örn: Hacker temalı, beyin yakan, sürpriz sonlu...")
        btn = st.form_submit_button("🚀 Filmleri Getir")
    
    st.divider()
    st.markdown("### 📋 Geçmişin")
    if st.button("Geçmişi Göster"):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                if data.data:
                    for satir in data.data:
                        st.caption(f"📅 {satir['created_at'][:10]}")
                        st.info(f"{satir['favorite_genre']}")
                        st.markdown("---")
                else:
                    st.warning("Kayıt bulunamadı.")
            except:
                st.error("Hata oluştu.")

# --- SONUÇ EKRANI ---
if btn and ad:
    # Yükleniyor animasyonu (Spinner)
    with st.spinner(f"🎬 {ad} için en iyi filmler aranıyor..."):
        # Kayıt
        try:
            supabase.table("users").insert({"username": ad, "favorite_genre": f"{tur} - {detay}"}).execute()
        except:
            pass

        # Yapay Zeka
        prompt = f"""
        Kullanıcı: {ad}
        Tür: {tur}
        Detay: {detay}
        Bana 6 ADET film öner. JSON formatında:
        [
            {{
                "film_adi": "Original Name",
                "turkce_ad": "Türkçe Adı",
                "yil": "2023",
                "puan": "8.5",
                "neden": "Kısa ve vurucu bir neden."
            }}, ...
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            filmler = json.loads(text_response)
            
            st.markdown("---")
            
            # Kart Görünümü
            for i in range(0, len(filmler), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(filmler):
                        film = filmler[i+j]
                        with cols[j]:
                            poster_url = get_movie_poster(film['film_adi'])
                            st.image(poster_url, use_container_width=True)
                            st.markdown(f"### {film['turkce_ad']}")
                            st.caption(f"⭐ IMDb: {film['puan']} | 📅 {film['yil']}")
                            st.markdown(f"_{film['neden']}_")
                st.markdown("<br>", unsafe_allow_html=True) # Boşluk bırak
                
        except Exception as e:
            st.error(f"Hata: {e}")