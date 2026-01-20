import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import requests
import json
import random

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

# Oturum Hafızası (Tekrarı Önlemek İçin)
if 'gosterilen_filmler' not in st.session_state:
    st.session_state.gosterilen_filmler = []

# CSS Yükleme
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

local_css("style.css")

# --- 2. DİL SÖZLÜĞÜ (Global Destek) ---
translations = {
    "TR": {
        "title": "CineMatch AI",
        "subtitle": "Yapay Zeka Destekli Kişisel Sinema Asistanın",
        "settings": "⚙️ Ayarlar",
        "name_label": "Adın:",
        "name_placeholder": "İsminiz...",
        "genre_label": "Tür:",
        "detail_label": "Ekstra Detay (Opsiyonel):",
        "detail_placeholder": "Örn: 2020 sonrası olsun...",
        "how_to_watch": "⚡ Nasıl İzleyeceksin?",
        "btn_love": "💑 Sevgiliyle",
        "btn_random": "🎲 Rastgele",
        "btn_family": "👨‍👩‍👧‍👦 Aileyle",
        "btn_normal": "🚀 Normal Ara",
        "btn_history": "Geçmiş Aramalarım",
        "btn_clear": "🗑️ Hafızayı Temizle",
        "msg_warning_name": "Lütfen önce sol menüden adını yaz.",
        "msg_success_history": "Hafıza temizlendi.",
        "msg_searching": "Film seçiliyor...",
        "res_platform": "Platform:",
        "res_trailer": "▶️ Fragman",
        "res_watch": "🍿 Hemen İzle",
        "prompt_lang": "Turkish",
        "genres": ["Tümü", "Anime", "Bilim Kurgu", "Aksiyon", "Gerilim", "Korku", "Romantik", "Komedi", "Suç", "Dram", "Animasyon"]
    },
    "EN": {
        "title": "CineMatch AI",
        "subtitle": "AI-Powered Personal Movie Assistant",
        "settings": "⚙️ Settings",
        "name_label": "Your Name:",
        "name_placeholder": "Name...",
        "genre_label": "Genre:",
        "detail_label": "Extra Details (Optional):",
        "detail_placeholder": "E.g., Released after 2020...",
        "how_to_watch": "⚡ Context / Mood",
        "btn_love": "💑 Date Night",
        "btn_random": "🎲 I'm Feeling Lucky",
        "btn_family": "👨‍👩‍👧‍👦 Family Time",
        "btn_normal": "🚀 Standard Search",
        "btn_history": "My History",
        "btn_clear": "🗑️ Clear Memory",
        "msg_warning_name": "Please enter your name in the sidebar first.",
        "msg_success_history": "Memory cleared.",
        "msg_searching": "Selecting movies...",
        "res_platform": "Platform:",
        "res_trailer": "▶️ Trailer",
        "res_watch": "🍿 Watch Now",
        "prompt_lang": "English",
        "genres": ["All", "Anime", "Sci-Fi", "Action", "Thriller", "Horror", "Romance", "Comedy", "Crime", "Drama", "Animation"]
    },
    "IT": {
        "title": "CineMatch AI",
        "subtitle": "Il Tuo Assistente Personale di Cinema con IA",
        "settings": "⚙️ Impostazioni",
        "name_label": "Il tuo nome:",
        "name_placeholder": "Nome...",
        "genre_label": "Genere:",
        "detail_label": "Dettagli Extra (Opzionale):",
        "detail_placeholder": "Es: Uscito dopo il 2020...",
        "how_to_watch": "⚡ Come guarderai?",
        "btn_love": "💑 Con Partner",
        "btn_random": "🎲 Mi sento fortunato",
        "btn_family": "👨‍👩‍👧‍👦 Con Famiglia",
        "btn_normal": "🚀 Ricerca Normale",
        "btn_history": "La mia cronologia",
        "btn_clear": "🗑️ Cancella Memoria",
        "msg_warning_name": "Per favore inserisci prima il tuo nome nella barra laterale.",
        "msg_success_history": "Memoria cancellata.",
        "msg_searching": "Selezione film in corso...",
        "res_platform": "Piattaforma:",
        "res_trailer": "▶️ Trailer",
        "res_watch": "🍿 Guarda Ora",
        "prompt_lang": "Italian",
        "genres": ["Tutti", "Anime", "Fantascienza", "Azione", "Thriller", "Horror", "Romantico", "Commedia", "Crimine", "Drammatico", "Animazione"]
    }
}

# --- 3. YARDIMCI FONKSİYONLAR ---
def get_movie_poster(movie_name):
    try:
        api_key = st.secrets["tmdb"]["api_key"]
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}"
        response = requests.get(url).json()
        if response['results']:
            poster_path = response['results'][0]['poster_path']
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
        else:
            return "https://via.placeholder.com/500x750?text=No+Img"
    except:
        return "https://via.placeholder.com/500x750?text=Error"

def puana_gore_sirala(filmler_listesi):
    def puan_temizle(film):
        try:
            puan_str = str(film.get('puan', '0')).split('/')[0].strip()
            return float(puan_str)
        except:
            return 0.0
    return sorted(filmler_listesi, key=puan_temizle, reverse=True)

# --- 4. BAĞLANTILAR (SUPABASE & GEMINI 2.0) ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    genai.configure(api_key=st.secrets["google"]["api_key"])
    
    # KOTA SORUNU ÇÖZÜLDÜ: 'gemini-2.0-flash' kullanıyoruz 👇
    model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# --- 5. ARAYÜZ MANTIK ---
with st.sidebar:
    # Dil Seçimi En Üstte
    selected_lang = st.selectbox("Language / Dil / Lingua", ["TR", "EN", "IT"])
    t = translations[selected_lang]

st.markdown(f"<h1>🍿 {t['title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #bbb; font-size: 1.2rem;'>{t['subtitle']}</p>", unsafe_allow_html=True)

tetikleyici = False
final_prompt_tur = ""
final_prompt_detay = ""
mod_aciklamasi = ""

with st.sidebar:
    st.markdown(f"### {t['settings']}")
    ad = st.text_input(t['name_label'], placeholder=t['name_placeholder'], key="user_name")
    
    secilen_tur = st.selectbox(t['genre_label'], t['genres'])
    secilen_detay = st.text_area(t['detail_label'], placeholder=t['detail_placeholder'])

    st.markdown("---")
    st.markdown(f"### {t['how_to_watch']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(t['btn_love'], use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Couple/Date Mode"
            final_prompt_tur = secilen_tur
            final_prompt_detay = f"{secilen_detay}. Context: Watching with partner. Good flow, no extreme gore unless requested."

        if st.button(t['btn_random'], use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Random Mode"
            konular = ["Plot Twist", "Dystopia", "One Room Thriller", "Psychological", "Crime/Mystery", "Mind-Bending"]
            sansli_konu = random.choice(konular)
            final_prompt_tur = secilen_tur
            final_prompt_detay = f"{secilen_detay}. Theme: '{sansli_konu}'. Hidden gem."

    with col2:
        if st.button(t['btn_family'], use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Family Mode"
            final_prompt_tur = secilen_tur
            final_prompt_detay = f"{secilen_detay}. Context: Family night. NO explicit content/violence."

        if st.button(t['btn_normal'], use_container_width=True):
            tetikleyici = True
            mod_aciklamasi = "Manual Search"
            final_prompt_tur = secilen_tur
            final_prompt_detay = secilen_detay

    st.markdown("---")
    if st.button(t['btn_history']):
        if ad:
            try:
                data = supabase.table("users").select("*").eq("username", ad).order("created_at", desc=True).limit(5).execute()
                if data.data:
                    for satir in data.data:
                        st.info(f"{satir['favorite_genre']}")
                        st.divider()
                else:
                    st.warning("...")
            except:
                pass
    
    if len(st.session_state.gosterilen_filmler) > 0:
        if st.button(t['btn_clear']):
            st.session_state.gosterilen_filmler = []
            st.success(t['msg_success_history'])

# --- 6. İŞLEM ---
if tetikleyici and ad:
    with st.spinner(f"🎬 {t['msg_searching']}"):
        
        try:
            log_text = f"[{selected_lang}] {final_prompt_tur} - {final_prompt_detay}"
            supabase.table("users").insert({"username": ad, "favorite_genre": log_text}).execute()
        except:
            pass

        yasakli_liste = ", ".join(st.session_state.gosterilen_filmler)
        
        prompt = f"""
        Role: Movie curator.
        Target Language: {t['prompt_lang']} (ANSWER IN THIS LANGUAGE)
        Genre: {final_prompt_tur}
        Details: {final_prompt_detay}
        
        Rule 1: Ignore these movies: [{yasakli_liste}]
        Rule 2: Recommend exactly 6 movies.
        Rule 3: Real IMDb scores.
        
        JSON Format ONLY:
        [
            {{
                "film_adi": "Original Name",
                "turkce_ad": "Translated Name",
                "yil": "2023",
                "puan": "8.8",
                "platform": "Netflix, Disney+ etc.",
                "neden": "Reason in {t['prompt_lang']}"
            }}, ...
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            filmler_ham = json.loads(text_response)
            filmler = puana_gore_sirala(filmler_ham)
            
            for f in filmler:
                st.session_state.gosterilen_filmler.append(f['film_adi'])

            st.success("✨")
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
                            st.markdown(f"📺 **{t['res_platform']}** {film.get('platform', '-')}")
                            st.info(f"{film['neden']}")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                lnk = f"https://www.youtube.com/results?search_query={film['film_adi'].replace(' ', '+')}+trailer"
                                st.link_button(t['res_trailer'], lnk, use_container_width=True)
                            with col_btn2:
                                lnk2 = f"https://www.google.com/search?q={film['film_adi'].replace(' ', '+')}+watch"
                                st.link_button(t['res_watch'], lnk2, use_container_width=True)
                            
                st.markdown("<br>", unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error: {e}")

elif tetikleyici and not ad:
    st.warning(t['msg_warning_name'])