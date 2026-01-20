import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json
import random

# --- 1. SAYFA VE AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Oturum Hafızası (Tekrarı Önlemek İçin)
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

# CSS Yükleme Fonksiyonu
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

# CSS'i Çağır
local_css("style.css")

# --- 2. YARDIMCI FONKSİYONLAR ---
def get_movie_poster(movie_name):
    """TMDB API kullanarak film posterini getirir."""
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
    """Filmleri IMDb puanına göre yüksekten düşüğe sıralar."""
    def puan_temizle(film):
        try:
            # "8.5/10" gibi gelirse sadece "8.5" kısmını al
            puan_str = str(film.get('puan', '0')).split('/')[0].strip()
            return float(puan_str)
        except:
            return 0.0
    return sorted(filmler_listesi, key=puan_temizle, reverse=True)

# --- 3. BAĞLANTILAR (SUPABASE & GEMINI) ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    genai.configure(api_key=st.secrets["google"]["api_key"])
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- 4. ARAYÜZ TASARIMI ---
st.markdown("<h1>🍿 CineMatch AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #bbb; font-size: 1.2rem;'>Yapay Zeka Destekli Kişisel Sinema Asistanın</p>", unsafe_allow_html=True)

# Değişkenleri Başlat
tetikleyici = False
final_prompt_tur = ""
final_prompt_detay = ""
mod_aciklamasi = ""

with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    ad = st.text_input("Adın:", placeholder="İsminiz...", key="user_name")
    
    st.caption("Önce tür seç, sonra modu belirle:")
    # Anime Seçeneği Eklendi
    secilen_tur = st.selectbox("Tür:", ["Tümü", "Anime", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"])
    secilen_detay = st.text_area("Ekstra Detay (Opsiyonel):", placeholder="Örn: 2020 sonrası olsun...")

    st.markdown("---")
    st.markdown("### ⚡ Nasıl İzleyeceksin?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # SEVGİLİ MODU
        if st.button("💑 Sevgiliyle", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Sevgili Modu"
            if secilen_tur == "Tümü":
                final_prompt_tur = "Romantik / Dram / Komedi"
            else:
                final_prompt_tur = secilen_tur
            
            final_prompt_detay = f"{secilen_detay}. Bu filmi sevgiliyle izleyeceğiz. Akıcı, ilişkiler üzerine veya keyifli bir film olsun. Ortamı bozacak aşırı vahşet olmasın."

        # RASTGELE MODU
        if st.button("🎲 Rastgele", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Rastgele Modu"
            konular = ["Plot Twist (Ters Köşe)", "Distopya", "Tek Mekan", "Psikolojik", "Suç/Gizem", "Underdog Hikayesi", "Mind-Bending"]
            sansli_konu = random.choice(konular)
            
            if secilen_tur == "Tümü":
                final_prompt_tur = "Sürpriz bir tür"
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
            
            final_prompt_detay = f"{secilen_detay}. Ailece izlenecek. Kesinlikle +18 cinsellik veya aşırı rahatsız edici vahşet içermemeli."

        # NORMAL ARAMA
        if st.button("🚀 Normal Ara", use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Manuel Arama"
            final_prompt_tur = secilen_tur
            final_prompt_detay = secilen_detay

    # GEÇMİŞ İŞLEMLERİ
    st.markdown("---")
    if st.button("Geçmiş Aramalarım"):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                if data.data:
                    for satir in data.data:
                        st.info(f"{satir['favorite_genre']}")
                        st.divider()
                else:
                    st.warning("Henüz kayıt yok.")
            except:
                st.error("Bağlantı hatası.")
    
    if len(st.session_state.gosterilen_filmler) > 0:
        if st.button("🗑️ Tekrar Hafızasını Sil"):
            st.session_state.gosterilen_filmler = []
            st.success("Hafıza temizlendi.")

# --- 5. SONUÇ EKRANI VE MANTIK ---
if tetikleyici and ad:
    with st.spinner(f"🎬 {mod_aciklamasi} çalışıyor... ({final_prompt_tur})"):
        
        # A. Veritabanına Logla
        try:
            log_text = f"[{mod_aciklamasi}] Tür: {final_prompt_tur} | Detay: {final_prompt_detay}"
            supabase.table("users").insert({"username": ad, "favorite_genre": log_text}).execute()
        except:
            pass

        # B. Yasaklı Listeyi (Hafıza) Hazırla
        yasakli_liste = ", ".join(st.session_state.gosterilen_filmler)
        
        # C. Gemini Prompt
        prompt = f"""
        Rolün: Dünyanın en iyi film küratörüsün.
        Kullanıcı: {ad}
        İstenen Tür: {final_prompt_tur}
        Detay/Bağlam: {final_prompt_detay}
        
        ÖNEMLİ KURAL 1: Daha önce önerdiğin şu filmleri ASLA önerme: [{yasakli_liste}]
        ÖNEMLİ KURAL 2: Bana tam 6 ADET film öner.
        ÖNEMLİ KURAL 3: IMDb puanları gerçekçi olsun.
        
        Cevabı SADECE şu JSON formatında ver:
        [
            {{
                "film_adi": "Original Name",
                "turkce_ad": "Türkçe Adı",
                "yil": "2023",
                "puan": "8.8",
                "platform": "Netflix, Disney+ veya Prime (Tahmini)",
                "neden": "Neden bu moda uygun?"
            }}, ...
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            # JSON Temizliği
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            filmler_ham = json.loads(text_response)
            
            # Puan Sıralaması
            filmler = puana_gore_sirala(filmler_ham)
            
            # Hafızaya Ekle
            for f in filmler:
                st.session_state.gosterilen_filmler.append(f['film_adi'])

            st.success(f"İşte öneriler! (Daha önce gördüklerini eledim)")
            st.markdown("---")
            
            # D. Gösterim Döngüsü (3 Kolonlu)
            for i in range(0, len(filmler), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(filmler):
                        film = filmler[i+j]
                        with cols[j]:
                            # Poster
                            poster_url = get_movie_poster(film['film_adi'])
                            st.image(poster_url, use_container_width=True)
                            
                            # Puan Rengi
                            try:
                                p = float(film['puan'])
                                renk = "🟢" if p >= 8.0 else "🟡" if p >= 6.5 else "🔴"
                            except:
                                renk = "⭐"

                            # Bilgiler
                            st.markdown(f"### {film['turkce_ad']}")
                            st.caption(f"{renk} **{film['puan']}** | 📅 {film['yil']}")
                            st.markdown(f"📺 **Platform:** {film.get('platform', 'Bilinmiyor')}")
                            st.info(f"{film['neden']}")
                            
                            # BUTONLAR (Fragman & İzle)
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                # Youtube Fragman Linki
                                fragman_linki = f"https://www.youtube.com/results?search_query={film['film_adi'].replace(' ', '+')}+trailer"
                                st.link_button("▶️ Fragman", fragman_linki, use_container_width=True)
                                
                            with col_btn2:
                                # Google İzle Linki
                                izle_linki = f"https://www.google.com/search?q={film['film_adi'].replace(' ', '+')}+izle"
                                st.link_button("🍿 İzle", izle_linki, use_container_width=True)
                            
                st.markdown("<br>", unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")

elif tetikleyici and not ad:
    st.warning("Lütfen önce sol menüden adını yaz.")