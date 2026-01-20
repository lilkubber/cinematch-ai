import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json
import random

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# --- OTURUM HAFIZASI (Session State) ---
# Kullanıcı sayfayı kapatmadığı sürece gördüğü filmleri burada tutuyoruz
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

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

def puana_gore_sirala(filmler_listesi):
    def puan_temizle(film):
        try:
            puan_str = str(film.get('puan', '0')).split('/')[0].strip()
            return float(puan_str)
        except:
            return 0.0
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

# Değişkenler
tetikleyici = False
final_prompt_tur = ""
final_prompt_detay = ""
mod_aciklamasi = ""

with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    ad = st.text_input("Adın:", placeholder="İsminiz...", key="user_name")
    
    st.caption("Önce tür seç, sonra modu belirle:")
    secilen_tur = st.selectbox("Tür:", ["Tümü", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"])
    secilen_detay = st.text_area("Ekstra Detay (Opsiyonel):", placeholder="Örn: 2020 sonrası olsun...")

    st.markdown("---")
    st.markdown("### ⚡ Nasıl İzleyeceksin?")
    
    # BUTONLAR (Form yerine direkt buton kullanıyoruz ki anında tepki versin)
    col1, col2 = st.columns(2)
    
    with col1:
        # SEVGİLİ MODU
        if st.button("💑 Sevgiliyle", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Sevgili Modu"
            # Tür "Tümü" ise Romantik yap, değilse seçilen türü koru ama "çiftlere uygun" yap
            if secilen_tur == "Tümü":
                final_prompt_tur = "Romantik / Dram / Komedi"
            else:
                final_prompt_tur = secilen_tur
            
            final_prompt_detay = f"{secilen_detay}. Bu filmi sevgiliyle izleyeceğiz. Çok ağır, aşırı şiddet içeren veya " \
                                 f"mod düşüren sahneler olmasın. İlişki dinamikleri, akıcılık veya ortak zevke hitap etmesi önemli."

        # RASTGELE MODU
        if st.button("🎲 Rastgele", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Rastgele Modu"
            konular = ["Plot Twist (Ters Köşe)", "Distopya", "Tek Mekan", "Psikolojik", "Suç/Gizem", "Underdog Hikayesi"]
            sansli_konu = random.choice(konular)
            
            if secilen_tur == "Tümü":
                final_prompt_tur = "Sürpriz bir tür olsun"
            else:
                final_prompt_tur = secilen_tur
            
            final_prompt_detay = f"{secilen_detay}. Konusu '{sansli_konu}' olsun. Çok bilinmeyen, gizli kalmış hazinelerden seç."

    with col2:
        # AİLE MODU
        if st.button("👨‍👩‍👧‍👦 Aileyle", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Aile Modu"
            if secilen_tur == "Tümü":
                final_prompt_tur = "Aile / Macera / Animasyon"
            else:
                final_prompt_tur = secilen_tur
            
            final_prompt_detay = f"{secilen_detay}. Ailece izlenecek. Kesinlikle +18 cinsellik veya aşırı rahatsız edici vahşet içermemeli. " \
                                 f"Her yaş grubunun (özellikle ebeveyn ve gençlerin) keyif alabileceği kaliteli yapımlar olsun."

        # MANUEL ARAMA (Normal Buton)
        if st.button("🚀 Normal Ara", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Manuel Arama"
            final_prompt_tur = secilen_tur
            final_prompt_detay = secilen_detay

    # GEÇMİŞ
    st.markdown("---")
    if st.button("Geçmiş Aramalarım"):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                for satir in data.data:
                    st.info(f"{satir['favorite_genre']}")
                    st.divider()
            except:
                st.error("Hata.")
    
    # Hafızayı Temizle Butonu
    if len(st.session_state.gosterilen_filmler) > 0:
        if st.button("🗑️ Tekrar Hafızasını Sil"):
            st.session_state.gosterilen_filmler = []
            st.success("Hafıza temizlendi, artık eski filmleri tekrar önerebilir.")

# --- SONUÇ EKRANI ---
if tetikleyici and ad:
    with st.spinner(f"🎬 {mod_aciklamasi} çalışıyor... ({final_prompt_tur})"):
        
        # 1. Veritabanı Kayıt (Sadece ne arandığını kaydet)
        try:
            log_text = f"[{mod_aciklamasi}] Tür: {final_prompt_tur} | Detay: {final_prompt_detay}"
            supabase.table("users").insert({"username": ad, "favorite_genre": log_text}).execute()
        except:
            pass

        # 2. Yasaklı Filmler Listesini Hazırla (Hafıza)
        yasakli_liste = ", ".join(st.session_state.gosterilen_filmler)
        
        # 3. Gemini Prompt
        prompt = f"""
        Rolün: Dünyanın en iyi film küratörüsün.
        Kullanıcı: {ad}
        İstenen Tür: {final_prompt_tur}
        Özel Bağlam/Detay: {final_prompt_detay}
        
        ÖNEMLİ KURAL 1: Şu filmleri daha önce önerdin, LÜTFEN BUNLARI TEKRAR ÖNERME: [{yasakli_liste}]
        ÖNEMLİ KURAL 2: Bana tam 6 ADET film öner.
        ÖNEMLİ KURAL 3: IMDb puanları gerçekçi olsun.
        
        Cevabı SADECE şu JSON formatında ver:
        [
            {{
                "film_adi": "Original Name",
                "turkce_ad": "Türkçe Adı",
                "yil": "2023",
                "puan": "8.8",
                "neden": "Kullanıcının kriterlerine (özellikle {mod_aciklamasi} moduna) neden tam uyuyor?"
            }}, ...
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            filmler_ham = json.loads(text_response)
            
            # Sıralama
            filmler = puana_gore_sirala(filmler_ham)
            
            # 4. Gösterilenleri Hafızaya Ekle
            for f in filmler:
                st.session_state.gosterilen_filmler.append(f['film_adi'])

            st.success(f"İşte öneriler! (Daha önce önerdiklerimi eledim)")
            st.markdown("---")
            
            for i in range(0, len(filmler), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(filmler):
                        film = filmler[i+j]
                        with cols[j]:
                            poster_url = get_movie_poster(film['film_adi'])
                            st.image(poster_url, use_container_width=True)
                            
                            try:
                                p = float(film['puan'])
                                renk = "🟢" if p >= 8.0 else "🟡" if p >= 6.5 else "🔴"
                            except:
                                renk = "⭐"

                            st.markdown(f"### {film['turkce_ad']}")
                            st.caption(f"{renk} **{film['puan']}** | 📅 {film['yil']}")
                            st.info(f"{film['neden']}")
                st.markdown("<br>", unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Hata: {e}")

elif tetikleyici and not ad:
    st.warning("Lütfen önce sol menüden adını yaz.")