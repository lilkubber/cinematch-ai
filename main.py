import streamlit as st
import requests
import json
import traceback # Hatanın kökünü bulmak için

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Test", page_icon="🧪")

st.title("🧪 CineMatch Dedektif Modu")
st.info("Bu modda resimler kapalıdır. Amaç hatayı bulmaktır.")

# --- 2. FONKSİYONLAR ---
def get_groq_text(prompt_text):
    # Adım Adım Loglama
    st.write("1️⃣ Fonksiyona girildi.")
    
    if "groq" not in st.secrets:
        st.error("❌ Secrets ayarlarında [groq] yok!")
        return None
    
    st.write("2️⃣ Anahtar okundu, bağlantı kuruluyor...")
    
    api_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        # JSON yerine normal text istiyoruz ki JSON hatası olmasın
    }
    
    try:
        res = requests.post(url, headers=headers, json=data, timeout=20)
        st.write(f"3️⃣ API Yanıt Kodu: {res.status_code}")
        
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            st.error(f"❌ API Hatası: {res.text}")
            return None
    except Exception as e:
        st.error(f"❌ Bağlantı Koptu: {e}")
        return None

# --- 3. ARAYÜZ ---
tur = st.selectbox("Tür", ["Bilim Kurgu", "Aksiyon", "Komedi"])

if st.button("FİLM BUL (TEST) 🚀"):
    st.write("🏁 Butona basıldı, işlem başlıyor...")
    
    try:
        # Hata olabilecek her adımı try-catch içine aldık
        prompt = f"Bana {tur} türünde 3 tane film öner. Sadece film isimlerini alt alta yaz. Başka bir şey yazma."
        
        cevap = get_groq_text(prompt)
        
        if cevap:
            st.success("✅ İŞLEM BAŞARILI!")
            st.write("Yapay Zekadan Gelen Cevap:")
            st.code(cevap)
        else:
            st.warning("⚠️ Cevap boş geldi.")
            
    except Exception:
        # İşte burası o beyaz ekranı engelleyen yer!
        st.error("🚨 SİSTEM ÇÖKTÜ! İşte hatanın sebebi:")
        st.code(traceback.format_exc()) # Hatayı ekrana basar
