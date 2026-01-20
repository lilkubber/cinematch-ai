import streamlit as st
import google.generativeai as genai
import requests
from supabase import create_client, Client

# --- 1. AYARLAR & TASARIM ---
st.set_page_config(page_title="CineMatch AI", page_icon="🍿", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e0e0e; color: #e5e5e5; }
.movie-card { background: #1a1a1a; padding: 15px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; }
.stButton>button { background: linear-gradient(90deg, #E50914 0%, #B20710 100%); color: white; border: none; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 2. BAĞLANTILAR (Kritik Kontrol) ---
# Supabase Kontrolü
supabase = None
try:
    if "supabase" in st.secrets:
        supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    else:
        st.warning("⚠️ Supabase Secrets bulunamadı. Giriş yapılamaz.")
except Exception as e:
    st.error(f"Veritabanı Hatası: {e}")

# Gemini Kontrolü
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("🚨 Gemini API Key Secrets kısmında eksik!")

# --- 3. ANA EKRAN ---
st.title("🎬 CineMatch")

tur = st.selectbox("Tür", ["Aksiyon", "Bilim Kurgu", "Dram", "Komedi", "Korku"])
detay = st.text_input("Detay", placeholder="Örn: Christopher Nolan tarzı...")

if st.button("FİLM BUL 🚀"):
    with st.status("🔍 İşlem yapılıyor...", expanded=True) as status:
        try:
            # Gemini 1.5 Flash - Hızlı ve stabil
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. SADECE film isimlerini 'Film1, Film2, Film3' şeklinde virgülle ayırarak yaz."
            
            response = model.generate_content(prompt)
            
            # Eğer yanıt boşsa hata fırlat
            if not response or not response.text:
                raise Exception("Gemini boş yanıt döndü.")
                
            film_isimleri = [f.strip() for f in response.text.split(',') if len(f.strip()) > 1][:3]
            status.update(label="✅ Başarılı!", state="complete", expanded=False)
            
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    st.markdown(f'<div class="movie-card"><h3>{isim}</h3></div>', unsafe_allow_html=True)
                    # Buraya poster fonksiyonunu daha sonra ekleyebilirsin
                    
        except Exception as e:
            status.update(label="❌ Hata!", state="error")
            st.error(f"Teknik Hata: {str(e)}")
            st.info("İpucu: API Key'in geçerli olduğundan ve faturanıza/kotanıza takılmadığınızdan emin olun.")
