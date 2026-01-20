if st.button("FİLM BUL 🚀"):
    with st.status("🔍 İşlem yapılıyor...", expanded=True) as status:
        try:
            # Model ismini 'gemini-1.5-flash-latest' olarak güncelledik
            # Bu isim v1beta ve v1 sürümlerinin ikisinde de çalışır.
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            prompt = f"Bana {tur} türünde, {detay} özelliklerinde 3 film öner. SADECE film isimlerini 'Film1, Film2, Film3' şeklinde virgülle ayırarak yaz."
            
            # Yanıtı alırken güvenlik ayarlarını da esnetelim ki engelleme olmasın
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                raise Exception("Gemini boş yanıt döndü veya içerik filtrelendi.")
                
            film_isimleri = [f.strip() for f in response.text.split(',') if len(f.strip()) > 1][:3]
            status.update(label="✅ Başarılı!", state="complete", expanded=False)
            
            # Film kartlarını göster
            cols = st.columns(3)
            for i, isim in enumerate(film_isimleri):
                with cols[i]:
                    st.markdown(f'<div class="movie-card"><h3>{isim}</h3></div>', unsafe_allow_html=True)

        except Exception as e:
            status.update(label="❌ Hata!", state="error")
            # Eğer hala 404 verirse 'gemini-pro' deniyoruz
            st.warning("Flash modeli bulunamadı, Pro modeli deneniyor...")
            try:
                model_alt = genai.GenerativeModel('gemini-pro')
                response_alt = model_alt.generate_content(prompt)
                st.write(response_alt.text)
            except:
                st.error(f"Teknik Hata: {str(e)}")
