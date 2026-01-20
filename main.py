import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json
import random

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# --- CSS YÜKLEME ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

local_css("style.css")

# --- YARDIMCI FONKSİYONLAR ---
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

# Puanı sayıya çevirip sıralama yapan fonksiyon
def puana_gore_sirala(filmler_listesi):
    def puan_temizle(film):
        try:
            # "8.5/10" gibi gelirse sadece "8.5" kısmını al
            puan_str = str(film.get('puan', '0')).split('/')[0].strip()
            return float(puan_str)
        except:
            return 0.0
    # Büyükten küçüğe sırala (reverse=True)
    return sorted(filmler_listesi, key=puan_temizle, reverse=True)

# --- BAĞLANTILAR ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    genai.configure(api_key=st.secrets["google"]["api_key"])
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- ARAYÜZ ---
st.markdown("<h1>🍿 CineMatch AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #bbb; font-size: 1.2rem;'>Yapay Zeka Destekli Kişisel Sinema Asistanın</p>", unsafe_allow_html=True)

# Değişkenleri başlat
secilen_tur = ""
secilen_detay = ""
tetikleyici = False
mod_adi = "Manuel Arama"

with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    ad = st.text_input("Adın:", placeholder="İsminiz...", key="user_name")
    
    # 1. MANUEL FORM
    with st.form("manuel_form"):
        st.caption("Kendi kriterlerini belirle:")
        form_tur = st.selectbox("Tür:", ["Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"])
        form_detay = st.text_area("Detay:", placeholder="Örn: Sürpriz sonlu...")
        btn_manuel = st.form_submit_button("🚀 Ara")
    
    if btn_manuel:
        secilen_tur = form_tur
        secilen_detay = form_detay
        tetikleyici = True
        mod_adi = "Manuel"

    # 2. HIZLI SEÇİMLER (Form dışında)
    st.markdown("---")
    st.markdown("### ⚡ Hızlı Modlar")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💑 Sevgili", use_container_width=True):
            secilen_tur = "Romantik Komedi / Dram"
            secilen_detay = "Sevgiliyle izlenecek, ne çok vıcık vıcık ne de çok sıkıcı. Akıcı, ilişkiler üzerine, keyifli ve kaliteli bir film olsun."
            tetikleyici = True
            mod_adi = "Sevgili Modu"

        if st.button("🎲 Rastgele", use_container_width=True):
            konular = ["Zamanda Yolculuk", "Zihin Oyunları", "Post-Apokaliptik", "90'lar Nostaljisi", "Tek Mekan Gerilimi", "Gerçek Hayat Hikayesi", "Soygun Filmi"]
            sansli_konu = random.choice(konular)
            secilen_tur = "Sürpriz"
            secilen_detay = f"Konusu '{sansli_konu}' olsun. Çok bilinmeyen ama kült bir film olsun."
            tetikleyici = True
            mod_adi = f"Rastgele ({sansli_konu})"

    with col2:
        if st.button("👨‍👩‍👧‍👦 Aile", use_container_width=True):
            secilen_tur = "Aile / Animasyon / Macera"
            secilen_detay = "Ailece izlenecek. Cinsellik ve aşırı şiddet içermeyen, çocukların da anlayabileceği ama yetişkinleri de sıkmayan sıcak bir film."
            tetikleyici = True
            mod_adi = "Aile Modu"
    
    # GEÇMİŞ
    st.markdown("---")
    if st.button("Geçmişi Göster"):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                for satir in data.data:
                    st.info(f"{satir['favorite_genre']}")
            except:
                st.error("Hata.")

# --- SONUÇ EKRANI ---
if tetikleyici and ad:
    with st.spinner(f"🎬 {mod_adi} çalışıyor... En yüksek puanlılar seçiliyor..."):
        
        # Loglama
        try:
            supabase.table("users").insert({"username": ad, "favorite_genre": f"[{mod_adi}] {secilen_tur} - {secilen_detay}"}).execute()
        except:
            pass

        prompt = f"""
        Kullanıcı: {ad}
        Tür: {secilen_tur}
        Detay: {secilen_detay}
        
        Bana bu kriterlere uyan tam 6 ADET film öner.
        ÖNEMLİ: IMDb puanlarını gerçekçi yaz.
        
        Cevabı SADECE şu JSON formatında ver:
        [
            {{
                "film_adi": "Original Name",
                "turkce_ad": "Türkçe Adı",
                "yil": "2023",
                "puan": "8.8",
                "neden": "Kısa ve vurucu neden."
            }}, ...
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            filmler_ham = json.loads(text_response)
            
            # SIRALAMA İŞLEMİ (Burada yapılıyor)
            filmler = puana_gore_sirala(filmler_ham)
            
            st.success(f"İşte senin için seçtiklerim! (IMDb Puanına Göre Sıralı 📉)")
            st.markdown("---")
            
            for i in range(0, len(filmler), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(filmler):
                        film = filmler[i+j]
                        with cols[j]:
                            poster_url = get_movie_poster(film['film_adi'])
                            st.image(poster_url, use_container_width=True)
                            
                            # Puanı Renkli Gösterme
                            try:
                                puan_float = float(film['puan'])
                                renk = "🟢" if puan_float >= 8.0 else "🟡" if puan_float >= 6.5 else "🔴"
                            except:
                                renk = "⭐"

                            st.markdown(f"### {film['turkce_ad']}")
                            st.caption(f"{renk} **{film['puan']}** | 📅 {film['yil']}")
                            st.markdown(f"_{film['neden']}_")
                st.markdown("<br>", unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Hata: {e}")

elif tetikleyici and not ad:
    st.warning("Lütfen önce sol menüden adını yaz.")