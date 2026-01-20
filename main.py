import streamlit as st
import requests
import json  # <-- simplejson yerine standart json kullanıyoruz, hata vermez.

# 1. Sayfa Ayarı
st.set_page_config(page_title="CineMatch", page_icon="🍿")

# 2. Fonksiyonlar
def get_recommendation(prompt_text):
    # Secrets kontrolü
    if "groq" not in st.secrets:
        return "HATA: Groq API Key bulunamadı. Lütfen Secrets ayarlarını kontrol et."
        
    api_key = st.secrets["groq"]["api_key"]
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Bellek dostu olması için token limitini düşük tuttum
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 400
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"API Hatası: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Bağlantı Hatası: {e}"

# 3. Arayüz
st.title("🍿 CineMatch - Lite")
st.success("Sistem Çalışıyor! (Veritabanısız Mod)")

tur = st.selectbox("Film Türü Seç", ["Bilim Kurgu", "Korku", "Aksiyon", "Komedi", "Dram"])

if st.button("FİLM ÖNER 🎬"):
    with st.spinner("Yapay zeka düşünüyor..."):
        prompt = f"Bana {tur} türünde, kesinlikle izlenmesi gereken 3 popüler film öner. Sadece film isimlerini ve yapım yıllarını madde madde yaz."
        
        sonuc = get_recommendation(prompt)
        
        if "HATA" in sonuc or "API Hatası" in sonuc:
            st.error(sonuc)
        else:
            st.info("İşte Önerilerim:")
            st.write(sonuc)
