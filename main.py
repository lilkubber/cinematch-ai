import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="Sistem Kontrolü", page_icon="🛠️")

st.title("🛠️ Sunucu Teşhis Ekranı")

# 1. Kütüphane Sürümü Kontrolü
st.subheader("1. Kütüphane Sürümü")
try:
    import google.generativeai
    version = google.generativeai.__version__
    st.info(f"Yüklü Generative AI Sürümü: {version}")
    
    # Sürüm analizi
    if version < "0.7.0":
        st.error("🚨 Sürüm ÇOK ESKİ! requirements.txt güncellenmemiş.")
    else:
        st.success("✅ Sürüm Güncel.")
except Exception as e:
    st.error(f"Kütüphane hatası: {e}")

# 2. Model Listesi Kontrolü
st.subheader("2. Erişilebilir Modeller")
try:
    api_key = st.secrets["google"]["api_key"]
    genai.configure(api_key=api_key)
    
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            models.append(m.name)
            
    if models:
        st.success("Şu modelleri buldum:")
        st.code("\n".join(models))
    else:
        st.error("Hiçbir model bulunamadı! API Key veya Bölge sorunu olabilir.")

except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")