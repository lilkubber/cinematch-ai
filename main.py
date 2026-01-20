import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json

st.set_page_config(page_title="CineMatch AI", page_icon="🎬", layout="wide")

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

try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    genai.configure(api_key=st.secrets["google"]["api_key"])
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

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
    st.markdown("### 📋 Geçmiş Aramalarım")
    
    if st.button("Geçmişimi Göster"):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                if data.data:
                    for satir in data.data:
                        st.caption(f"📅 {satir['created_at'][:10]}")
                        st.info(f"{satir['favorite_genre']}")
                        st.markdown("---")
                else:
                    st.warning("Bu isimle kayıtlı geçmiş bulunamadı.")
            except Exception as e:
                st.error(f"Hata: {e}")
        else:
            st.warning("Geçmişi görmek için yukarıya adını yazmalısın.")

if btn and ad:
    st.info(f"🧠 {ad} için 6 harika film seçiliyor...")
    
    try:
        supabase.table("users").insert({"username": ad, "favorite_genre": f"{tur} - {detay}"}).execute()
    except:
        pass

    prompt = f"""
    Kullanıcı: {ad}
    Tür: {tur}
    Detay: {detay}
    
    Bana bu kriterlere uyan tam 6 ADET film öner.
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
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        filmler = json.loads(text_response)
        
        st.success("İşte senin için seçtiklerim! 👇")
        st.divider()
        
        for i in range(0, len(filmler), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(filmler):
                    film = filmler[i+j]
                    with cols[j]:
                        poster_url = get_movie_poster(film['film_adi'])
                        st.image(poster_url, use_container_width=True)
                        st.subheader(f"{film['turkce_ad']}")
                        st.caption(f"📅 {film['yil']} | ⭐ {film['puan']}")
                        st.info(f"{film['neden']}")
            st.divider()
                
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")