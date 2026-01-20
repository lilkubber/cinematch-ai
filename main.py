import streamlit as st
import http.client
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="CineMatch Atomic", page_icon="🐜", layout="wide")

st.title("🐜 CineMatch: Atom Karınca Modu")
st.info("Bu mod, harici hiçbir kütüphane kullanmaz. Beyaz ekran vermesi imkansızdır.")

# --- 2. FONKSİYONLAR (SAF PYTHON) ---
def get_groq_atomic(prompt_text):
    if "groq" not in st.secrets:
        st.error("Secrets ayarı eksik!")
        return None
        
    api_key = st.secrets["groq"]["api_key"]
    
    # 1. Bağlantı Kur (Saf HTTP)
    conn = http.client.HTTPSConnection("api.groq.com")
    
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": f"Sen bir film asistanısın. Türkçe cevap ver. Şu özelliklerde 3 film öner: {prompt_text}. Sadece film isimlerini ve yıllarını madde madde yaz."
            }
        ],
        "max_tokens": 300
    })
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 2. İsteği Gönder
        conn.request("POST", "/openai/v1/chat/completions", payload, headers)
        
        # 3. Cevabı Al
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            return json.loads(data.decode("utf-8"))['choices'][0]['message']['content']
        else:
            st.error(f"Sunucu Hatası: {res.status}")
            st.text(data.decode("utf-8"))
            return None
            
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None
    finally:
        conn.close()

# --- 3. ARAYÜZ ---
tur = st.selectbox("Tür Seç", ["Bilim Kurgu", "Aksiyon", "Komedi"])
detay = st.text_input("Detay Gir", "2024 yapımı...")

if st.button("FİLM BUL (SAF MOD) 🚀"):
    with st.spinner("Atom karınca çalışıyor..."):
        prompt = f"Tür: {tur}, Detay: {detay}"
        sonuc = get_groq_atomic(prompt)
        
        if sonuc:
            st.success("✅ BAŞARILI!")
            st.markdown(sonuc)
