import streamlit as st
import praw
from openai import OpenAI
import requests
import base64
from PIL import Image
import io

# --- SEITE KONFIGURATION ---
st.set_page_config(page_title="BatchIntel Pro", page_icon="👟", layout="wide")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ API Keys")
    openai_key = st.text_input("OpenAI API Key", type="password")
    reddit_id = st.text_input("Reddit Client ID")
    reddit_secret = st.text_input("Reddit Client Secret", type="password")
    discord_token = st.text_input("Discord Token (für Feed)", type="password")
    
    st.info("Diese Daten werden nur lokal für deine Session genutzt.")

# Clients initialisieren (nur wenn Keys vorhanden)
if openai_key and reddit_id and reddit_secret:
    client = OpenAI(api_key=openai_key)
    reddit = praw.Reddit(
        client_id=reddit_id,
        client_secret=reddit_secret,
        user_agent="BatchIntelPro v1.0"
    )
else:
    st.warning("Bitte trage alle API Keys in der Sidebar ein!")
    st.stop()

# --- FUNKTIONEN ---

import requests

def get_reddit_data_no_api(query):
    # Wir hängen einfach .json an die Suche an
    search_url = f"https://www.reddit.com/search.json?q={query}+review&limit=10"
    
    # WICHTIG: Ein spezieller User-Agent, sonst blockt Reddit
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) BatchIntel/1.0'}
    
    response = requests.get(search_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        all_text = ""
        for post in data['data']['children']:
            all_text += f"\nPost: {post['data']['title']}\n"
            all_text += post['data']['selftext']
        return all_text
    else:
        return "Reddit blockiert gerade die Anfrage (Status 429). Versuch es später nochmal."

def analyze_text(query, context):
    prompt = f"Analysiere die Batches für {query}. Ranking, Pros/Cons und Verdict als JSON."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"{prompt}\n\nDaten: {context}"}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)

def get_discord_feed(token):
    # Beispiel: Fetcht Nachrichten aus einem spezifischen Channel (Channel-ID einsetzen)
    # Nutzt die Discord API um die letzten 5 Nachrichten zu holen
    headers = {"Authorization": token}
    # Beispiel Channel-ID (musst du durch eine echte ersetzen, z.B. Restock-Channel)
    channel_id = "DEINE_CHANNEL_ID" 
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5"
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else []

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

# --- UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🔍 Batch Finder", "📸 AI QC Check", "📢 Discord Feed"])

# --- TAB 1: BATCH FINDER ---
with tab1:
    st.title("Batch Search & Ranking")
    query = st.text_input("Schuhmodell eingeben", placeholder="z.B. Jordan 4 SB Pine Green")
    
    if st.button("Analysieren"):
        with st.spinner("Reddit wird gescannt..."):
            context = get_reddit_data(query)
            analysis = analyze_text(query, context)
            
            st.subheader(f"Ergebnisse für {query}")
            for b in analysis.get('batches', []):
                with st.expander(f"{b['batch']} - Score: {b['score']}"):
                    st.write(f"✅ {b['pros']}")
                    st.write(f"❌ {b['cons']}")
                    st.info(f"Fazit: {b['verdict']}")
            
            st.divider()
            st.subheader("🖼️ Visuelles QC Archiv")
            st.write("Suche diesen Batch in QC-Datenbanken:")
            qc_link = f"https://qc.photos/?search={query.replace(' ', '+')}"
            st.markdown(f"[👉 Klicke hier für echte QC Fotos von {query}]({qc_link})")

# --- TAB 2: AI QC CHECK (Vision) ---
with tab2:
    st.title("📸 AI Quality Check")
    st.write("Lade dein QC-Bild hoch. Die KI prüft es auf typische Fehler.")
    
    uploaded_file = st.file_uploader("Bild hochladen...", type=["jpg", "jpeg", "png"])
    target_batch = st.selectbox("Welcher Batch sollte das sein?", ["LJR", "GX", "PK 4.0", "VT", "FK", "Unbekannt"])

    if uploaded_file and st.button("Bild prüfen"):
        base64_image = encode_image(uploaded_file)
        with st.spinner("KI analysiert das Foto..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Das ist ein Foto eines {target_batch} Batch Sneakers. Prüfe die Details (Stitching, Form, Logo) auf typische Replika-Fehler. Gib ein ehrliches Rating (GL oder RL)."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ],
                    }
                ],
                max_tokens=500,
            )
            st.image(uploaded_file, caption="Dein Upload", width=400)
            st.markdown(f"### KI Analyse:\n{response.choices[0].message.content}")

# --- TAB 3: DISCORD FEED ---
with tab3:
    st.title("📢 Live Discord Updates")
    if discord_token:
        st.write("Hier siehst du die neuesten Nachrichten aus deinen überwachten Channels (z.B. Restocks).")
        if st.button("Feed aktualisieren"):
            messages = get_discord_feed(discord_token)
            for msg in messages:
                with st.chat_message("discord"):
                    st.write(f"**{msg['author']['username']}:** {msg['content']}")
    else:
        st.info("Bitte Discord Token in der Sidebar eingeben.")
