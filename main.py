import streamlit as st
import os
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Ultra", page_icon="💎", layout="wide")

# Tasarım
st.markdown("""
<style>
.stApp { background-color: #000; color: #fff; }
.stButton>button { background-color: #E50914; color: white; border-radius: 4px; font-weight: bold; width: 100%; height: 50px; }
.movie-box { background: #111; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }
h3 { color: #E50914; }
</style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİ KÜTÜPHANE YÜKLEME ---
try:
    from openai import OpenAI
except ImportError:
    st.error("🚨 HATA: 'openai' kütüphanesi eksik! requirements.txt dosyasına 'openai' eklemelisin.")
    st.stop()

# --- 3. FONKSİYONLAR ---
def get_recommendations_safe(prompt_text):
    if "groq" not in st.secrets:
        st.error("Secrets ayarı eksik.")
        return None
        
    api_key = st.secrets["groq"]["api_key"]
    
    # OpenAI İstemcisi ile Groq'a bağlanıyoruz (En sağlam yöntem)
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key
    )
    
    system_msg = """
    Sen bir film uzmanısın. Türkçe cevap ver.
    Cevabın SADECE geçerli bir JSON objesi olsun.
    Format: { "movies": [ {"isim": "Film Adı", "yil": "2023", "puan": "8.5", "ozet": "Kısa özet."} ] }
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_text}
            ],
            response_format={"type": "json_object"},
            timeout=20 # 20 saniye bekle, cevap gelmezse hata ver (beyaz ekran verme)
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"⚠️ Bağlantı Hatası: {str(e)}")
        return None

# --- 4. ARAYÜZ ---
st.title("🍿 CineMatch Ultra")
st.info("Bu sürüm OpenAI motoru kullanarak çökme riskini en aza indirir.")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with col2:
    detay = st.text_input("Detay", placeholder="Örn: Sürpriz sonlu...")

if st.button("FİLM BUL 🚀"):
    # Spinner bazen kilitlenmeye sebep olabilir, status kullanalım
    status_box = st.status("Yapay zeka çalışıyor...", expanded=True)
    
    json_str = get_recommendations_safe(f"Tür: {tur}, Detay: {detay}. Bana 3 film öner.")
    
    if json_str:
        status_box.update(label="✅ Tamamlandı!", state="complete", expanded=False)
        
        try:
            data = json.loads(json_str)
            filmler = data.get("movies", [])
            
            if filmler:
                cols = st.columns(3)
                for i, film in enumerate(filmler):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="movie-box">
                            <h3>{film['isim']}</h3>
                            <p>📅 {film['yil']} | ⭐ {film['puan']}</p>
                            <p style="color:#aaa; font-size:14px;">{film['ozet']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("Film bulunamadı.")
        except:
            st.error("Veri işleme hatası.")
            st.code(json_str)
    else:
        status_box.update(label="❌ Hata Oluştu", state="error")
