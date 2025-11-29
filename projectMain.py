import customtkinter as ctk
import redis
from PIL import Image
import requests
from io import BytesIO

# ----------------------
# Redis connection
# ----------------------
r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

# ----------------------
# Helper functions
# ----------------------
def get_all_anime_titles():
    keys = r.keys("anime:*")
    titles = []
    for key in keys:
        data = r.hgetall(key)
        titles.append(data.get("title", "Unknown"))
    return titles

def search_anime(query):
    keys = r.keys("anime:*")
    results = []
    for key in keys:
        data = r.hgetall(key)
        title = data.get("title", "").lower()
        if query.lower() in title:
            results.append(data)
    return results

# ----------------------
# App setup
# ----------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Anime Viewer")
app.geometry("900x600")

# ----------------------
# Frames
# ----------------------
left_frame = ctk.CTkFrame(app, width=300)
left_frame.pack(side="left", fill="y", padx=10, pady=10)

right_frame = ctk.CTkFrame(app)
right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

# ----------------------
# Search Entry
# ----------------------
search_var = ctk.StringVar()
search_entry = ctk.CTkEntry(left_frame, placeholder_text="Search anime...", textvariable=search_var)
search_entry.pack(pady=10, padx=10, fill="x")

# ----------------------
# Anime listbox (scrollable buttons)
# ----------------------
anime_listbox = ctk.CTkScrollableFrame(left_frame, width=280, height=500)
anime_listbox.pack(pady=10, padx=10, fill="y")

anime_buttons = []

def display_anime_list(anime_data_list):
    # Clear previous buttons
    for btn in anime_buttons:
        btn.destroy()
    anime_buttons.clear()
    
    for anime in anime_data_list:
        title = anime.get("title", "Unknown")
        btn = ctk.CTkButton(anime_listbox, text=title, width=250,
                            command=lambda a=anime: show_anime_details(a))
        btn.pack(pady=5)
        anime_buttons.append(btn)

def update_search(*args):
    query = search_var.get()
    if query == "":
        display_anime_list([r.hgetall(k) for k in r.keys("anime:*")])
    else:
        results = search_anime(query)
        display_anime_list(results)

search_var.trace_add("write", update_search)

# ----------------------
# Anime details
# ----------------------
title_label = ctk.CTkLabel(right_frame, text="", font=ctk.CTkFont(size=20, weight="bold"))
title_label.pack(pady=10)

image_label = ctk.CTkLabel(right_frame, text="")
image_label.pack(pady=10)

details_text = ctk.CTkTextbox(right_frame, width=500, height=400)
details_text.pack(pady=10)

def show_anime_details(anime):
    title_label.configure(text=anime.get("title", "Unknown"))
    
    # Load image with CTkImage
    img_url = anime.get("image")
    if img_url:
        try:
            response = requests.get(img_url, timeout=5)
            response.raise_for_status()
            pil_img = Image.open(BytesIO(response.content)).convert("RGB")  # ensure RGB
            pil_img = pil_img.resize((200, 300))
            ctk_img = ctk.CTkImage(pil_img, size=(200, 300))
            image_label.configure(image=ctk_img, text="")  # remove text
            image_label.image = ctk_img  # keep reference
        except Exception as e:
            print(f"Error loading image: {e}")
            image_label.configure(text="No Image", image=None)
    else:
        image_label.configure(text="No Image", image=None)
    
    # Details text
    details_text.delete("1.0", ctk.END)
    info = f"""
Title: {anime.get('title', '')}
English Title: {anime.get('title_english', '')}
Japanese Title: {anime.get('title_japanese', '')}
Year: {anime.get('year', '')}
Episodes: {anime.get('episodes', '')}
Duration: {anime.get('duration', '')}
Score: {anime.get('score', '')}
Rating: {anime.get('rating', '')}
Genres: {anime.get('genres', '')}
Themes: {anime.get('themes', '')}
Studios: {anime.get('studios', '')}

Synopsis:
{anime.get('synopsis', '')}
"""
    details_text.insert("1.0", info)

# ----------------------
# Initial load
# ----------------------
all_anime = [r.hgetall(k) for k in r.keys("anime:*")]
display_anime_list(all_anime)

app.mainloop()
