import streamlit as st
import requests
import simplejson as json

# 1. Sayfa Ayarı (En başa yazılmalı)
st.set_page_config(page_title="CineMatch", page_icon="🍿")

# 2. Fonksiyonlar
def get_recommendation(prompt_text):
    # Secrets kontrolü
    if "groq" not in st.secrets:
        return "HATA: Groq API Key bulunamadı."
        
    api_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 500  # Cevabı kısa tutup belleği koruyoruz
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"API Hatası: {response.status_code}"
    except Exception as e:
        return f"Bağlantı Hatası: {e}"

# 3. Arayüz
st.title("🍿 CineMatch - Lite")
st.write("Veritabanı olmadan, saf yapay zeka testi.")

tur = st.selectbox("Film Türü", ["Bilim Kurgu", "Korku", "Aksiyon", "Komedi"])

if st.button("FİLM ÖNER"):
    with st.spinner("Yapay zeka düşünüyor..."):
        prompt = f"Bana {tur} türünde, Türkiye'de izlenebilecek popüler 3 film öner. Sadece film isimlerini ve yıllarını liste maddesi olarak yaz."
        
        sonuc = get_recommendation(prompt)
        
        if "HATA" in sonuc or "API Hatası" in sonuc:
            st.error(sonuc)
        else:
            st.success("Öneri Hazır!")
            st.write(sonuc)