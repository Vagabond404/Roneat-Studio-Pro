current_lang = "en"

translations = {}

def tr(text):
    if current_lang in translations and text in translations[current_lang]:
        return translations[current_lang][text]
    return text

def set_lang(lang_code: str):
    global current_lang
    current_lang = lang_code
