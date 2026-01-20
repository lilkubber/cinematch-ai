import streamlit as st
from supabase import create_client, Client
import requests
import json
import time
from datetime import date, datetime
import re

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# CSS
def local_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e0e0e; color: #e5e5e5; }}
    .stTextInput > div > div > input {{ background-color: #222; color: white; }}
    .stButton>button {{ background: #E50914; color: white; border: none; height: 3em; }}
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. BAĞLANTILAR (HATA KONTROLLÜ) ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"❌ Veritabanı Hatası: {e}")
    st.stop()

# --- 3. FONKSİYONLAR ---
def get_groq_recommendation(prompt_text):
    # Debug: Hangi anahtarı kullanıyoruz? (Sadece ilk 4 harf)
    key = st.secrets["groq"]["api_key"]
    st.write(f"🔑 Groq Anahtarı Kontrol: {key[:4]}... (Okundu)")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    # Model olarak Llama-3-70b kullanıyoruz (En kararlısı)
    data = {
        "model": "llama3-70b-8192", 
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.5,
        "response_format": {"type": "json_object"}
    }
    
    st.write("📡 Groq'a istek gönderiliyor...")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        st.write("✅ Groq yanıt verdi!")
        return response.json()['choices'][0]['message']['content']
    else:
        st.error(f"❌ Groq Hatası: {response.status_code} - {response.text}")
        return None

def get_movie_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        res = requests.get(url).json()
        if res['results']: 
            return f"https://image.tmdb.org/t/p/w500{res['results'][0]['poster_path']}"
        return "https://via.placeholder.com/500x750?text=No+Img"
    except Exception as e:
        st.write(f"⚠️ Poster Hatası ({movie_name}): {e}")
        return "https://via.placeholder.com/500x750?text=Error"

# --- 4. ARAYÜZ ---
st.title("🍿 CineMatch AI (Debug Modu)")

# Basit Form
tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi"])
detay = st.text_input("Detay", "Sürpriz sonlu")

if st.button("FİLM BUL 🚀"):
    st.write("🏁 İşlem Başladı...")
    
    prompt = f"""
    Return EXACTLY 3 movies in Turkish.
    Genre: {tur}. Details: {detay}.
    JSON Format: {{ "movies": [ {{ "film_adi": "Name", "puan": "8.5", "yil": "2023", "neden": "Reason" }} ] }}
    """
    
    # 1. Groq Çağrısı
    json_str = get_groq_recommendation(prompt)
    
    if json_str:
        st.write("📄 JSON Verisi Alındı:")
        st.code(json_str) # Gelen veriyi ekrana basıyoruz ki görelim
        
        try:
            # 2. JSON Temizleme ve Çevirme
            data = json.loads(json_str)
            if "movies" in data: filmler = data["movies"]
            else: filmler = data
            
            st.write(f"🎬 {len(filmler)} film bulundu. Posterler çekiliyor...")
            
            # 3. Ekrana Basma
            cols = st.columns(3)
            for i, film in enumerate(filmler):
                with cols[i]:
                    st.write(f"🖼️ {film['film_adi']} posteri aranıyor...")
                    img_url = get_movie_poster(film['film_adi'])
                    st.image(img_url, use_container_width=True)
                    st.markdown(f"**{film['film_adi']}**")
                    st.info(film['neden'])
            
            st.success("✨ İşlem Başarıyla Tamamlandı!")
            
        except Exception as e:
            st.error(f"❌ JSON veya Döngü Hatası: {e}")
    else:
        st.error("❌ Veri boş geldi.")