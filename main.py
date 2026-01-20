import streamlit as st
import os

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; height: 3em; width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESMİ GROQ İSTEMCİSİ ---
# Burada 'requests' yerine 'groq' kütüphanesini kullanıyoruz.
try:
    from groq import Groq
except ImportError:
    st.error("🚨 HATA: 'groq' kütüphanesi yüklü değil! requirements.txt dosyasına 'groq' yazmalısın.")
    st.stop()

def get_movie_recommendation(tur, detay):
    # Secrets Kontrolü
    if "groq" not in st.secrets:
        st.error("❌ Groq API Key bulunamadı.")
        return None

    api_key = st.secrets["groq"]["api_key"]
    
    try:
        # İstemciyi başlat
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Sen bir film uzmanısın. Dil: Türkçe.
        Tür: {tur}. Detay: {detay}.
        Bana tam olarak 3 film öner.
        Sadece film isimlerini ve yıllarını şu formatta yaz:
        1. Film Adı (Yıl) - Kısa Açıklama
        2. Film Adı (Yıl) - Kısa Açıklama
        3. Film Adı (Yıl) - Kısa Açıklama
        Başka hiçbir giriş cümlesi veya not yazma.
        """
        
        # İstek Gönder (Resmi Yöntem)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=300, # Cevabı kısa tutuyoruz
        )
        
        return chat_completion.choices[0].message.content

    except Exception as e:
        st.error(f"⚠️ API Bağlantı Hatası: {str(e)}")
        return None

# --- 3. ARAYÜZ ---
st.title("🍿 CineMatch AI")
st.caption("Resmi Groq Kütüphanesi ile Güçlendirildi")

col1, col2 = st.columns([1, 2])
with col1:
    tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Korku", "Komedi", "Dram"])
with col2:
    detay = st.text_input("Detay", placeholder="Örn: 2024 yapımı...")

if st.button("FİLM BUL 🚀"):
    with st.spinner("Yapay zeka düşünüyor..."):
        sonuc = get_movie_recommendation(tur, detay)
        
        if sonuc:
            st.success("İşte Öneriler:")
            st.markdown(sonuc)
