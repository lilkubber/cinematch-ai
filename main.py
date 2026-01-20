import streamlit as st
import requests

st.set_page_config(page_title="Teşhis Aracı", page_icon="🔧")

st.title("🔧 CineMatch Sistem Kontrolü")
st.write("Bu araç sistemin neden çöktüğünü bulacak.")

if st.button("SİSTEMİ TEST ET 🚀"):
    # 1. TEST: İnternet Bağlantısı
    st.write("📡 1. İnternet bağlantısı kontrol ediliyor...")
    try:
        requests.get("https://www.google.com", timeout=5)
        st.success("✅ İnternet Bağlantısı: BAŞARILI")
    except Exception as e:
        st.error(f"❌ İnternet Bağlantısı YOK: {e}")
        st.stop()

    # 2. TEST: Secrets Dosyası Okuma
    st.write("🔑 2. Secrets dosyası kontrol ediliyor...")
    try:
        if "groq" in st.secrets:
            key = st.secrets["groq"]["api_key"]
            st.success(f"✅ Anahtar Bulundu: {key[:5]}... (Format Doğru)")
        else:
            st.error("❌ Secrets dosyasında [groq] başlığı EKSİK!")
            st.stop()
    except Exception as e:
        st.error(f"❌ Secrets Dosyası BOZUK: {e}")
        st.stop()

    # 3. TEST: Groq API Bağlantısı (Basit)
    st.write("🤖 3. Yapay Zeka (Groq) testi yapılıyor...")
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "Hello, are you working?"}]
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        
        if resp.status_code == 200:
            st.success("✅ SONUÇ: Yapay Zeka Sorunsuz Çalışıyor!")
            st.balloons()
            st.write("Cevap:", resp.json()['choices'][0]['message']['content'])
        else:
            st.error(f"❌ API Hatası Verdi: Kodu {resp.status_code}")
            st.write(resp.text)
            
    except Exception as e:
        st.error(f"❌ API Bağlantısında Çökme: {e}")
