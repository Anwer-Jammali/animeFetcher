# projectMain.py
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
import requests
from io import BytesIO
import os
import threading
import tkinter.messagebox as msgbox
import redis_db 

# ----------------- Config -----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ITEMS_PER_PAGE = 6
IMAGE_CACHE_DIR = "images_cache"
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

PALETTE = [
    "#2D00F7", "#6A00F4", "#8900F2", "#A100F2",
    "#B100E8", "#BC00DD", "#D100D1", "#DB00B6",
    "#E500A4", "#F20089"
]

# ----------------- Helpers -----------------
def cache_image(url):
    if not url:
        return None
    fname = url.split("/")[-1].split("?")[0]
    path = os.path.join(IMAGE_CACHE_DIR, fname)
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGB")
        except:
            pass
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.content
        with open(path, "wb") as f:
            f.write(data)
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception as e:
        print(f"Image download failed: {e}")
        return None

def make_ctk_image(pil_img, size=(220, 300)):
    try:
        return CTkImage(light_image=pil_img.resize(size), dark_image=pil_img.resize(size), size=size)
    except:
        return None

# ----------------- Main App -----------------
class AnimeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Anime Explorer")
        self.geometry("1200x800")
        self.minsize(1000, 650)

        self.current_page = 0
        self.current_results = []
        self.is_loading = False

        self._build_ui()
        threading.Thread(target=self.load_all_anime, daemon=True).start()

    def _build_ui(self):
        self._build_header()
        self._build_search()        # Now with Year inputs!
        self._build_cards_area()
        self._build_pagination()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=80, fg_color="transparent")
        header.pack(fill="x", pady=(12, 0))
        title = ctk.CTkLabel(header, text="Anime Explorer", font=ctk.CTkFont(size=34, weight="bold"),
                             text_color=PALETTE[0])
        title.pack(pady=12)

    def _build_search(self):
        frame = ctk.CTkFrame(self)
        frame.pack(pady=15, padx=25, fill="x")

        # Variables
        self.search_var = ctk.StringVar()
        self.genre_var = ctk.StringVar(value="(Any)")
        self.year_from_var = ctk.StringVar()
        self.year_to_var = ctk.StringVar()

        # Title Search
        ctk.CTkEntry(frame, width=400, height=42,
                     placeholder_text="Search by title...",
                     textvariable=self.search_var,
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 10))

        # Genre Dropdown
        self.genre_option = ctk.CTkOptionMenu(frame, values=["(Any)"], variable=self.genre_var, width=160)
        self.genre_option.pack(side="left", padx=(0, 10))

        # Year From
        ctk.CTkLabel(frame, text="Year:", font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkEntry(frame, width=90, height=42, placeholder_text="From",
                     textvariable=self.year_from_var).pack(side="left", padx=(5, 3))

        ctk.CTkLabel(frame, text="→").pack(side="left")

        ctk.CTkEntry(frame, width=90, height=42, placeholder_text="To",
                     textvariable=self.year_to_var).pack(side="left", padx=(3, 15))

        # Buttons
        ctk.CTkButton(frame, text="Search", width=120, height=42,
                      command=self.on_search_click, fg_color="#0066FF").pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Show All", width=120, height=42,
                      command=self.on_show_all).pack(side="left")

    def _build_cards_area(self):
        self.cards_frame = ctk.CTkScrollableFrame(self)
        self.cards_frame.pack(fill="both", expand=True, padx=25, pady=10)

    def _build_pagination(self):
        pag = ctk.CTkFrame(self)
        pag.pack(pady=15)

        self.prev_btn = ctk.CTkButton(pag, text="Previous", width=120, command=self.prev_page)
        self.page_label = ctk.CTkLabel(pag, text="Page 1 / 1", width=150)
        self.next_btn = ctk.CTkButton(pag, text="Next", width=120, command=self.next_page)

        self.prev_btn.pack(side="left", padx=15)
        self.page_label.pack(side="left", padx=15)
        self.next_btn.pack(side="left", padx=15)

    # ----------------- Data & Search -----------------
    def load_all_anime(self):
        if self.is_loading: return
        self.is_loading = True
        try:
            anime_list = redis_db.get_all_anime()
            anime_list.sort(key=lambda x: x.get("title", "").lower())
            self.current_results = anime_list

            genres = ["(Any)"] + sorted(redis_db.get_distinct_genres())
            self.genre_option.configure(values=genres)

            self.current_page = 0
        except Exception as e:
            msgbox.showerror("Database Error", f"Failed to load data:\n{e}")
        finally:
            self.is_loading = False
            self.after(0, self.render_page)

    def on_search_click(self):
        if self.is_loading: return

        query = self.search_var.get().strip()
        genre = self.genre_var.get()
        genre = "" if genre == "(Any)" else genre

        year_from_str = self.year_from_var.get().strip()
        year_to_str = self.year_to_var.get().strip()

        year_from = int(year_from_str) if year_from_str.isdigit() else None
        year_to = int(year_to_str) if year_to_str.isdigit() else None

        if (year_from_str and not year_from_str.isdigit()) or (year_to_str and not year_to_str.isdigit()):
            msgbox.showwarning("Invalid Year", "Please enter valid numbers for years.")
            return

        self.is_loading = True
        try:
            results = redis_db.search_anime(
                query=query,
                genre=genre,
                year_from=year_from,
                year_to=year_to
            )
            self.current_results = results
            self.current_page = 0
            self.render_page()
        except Exception as e:
            msgbox.showerror("Search Error", f"Search failed:\n{e}")
        finally:
            self.is_loading = False

    def on_show_all(self):
        self.search_var.set("")
        self.genre_var.set("(Any)")
        self.year_from_var.set("")
        self.year_to_var.set("")
        threading.Thread(target=self.load_all_anime, daemon=True).start()

    # ----------------- Rendering & Details (unchanged, just cleaned) -----------------
    def render_page(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        total = len(self.current_results)
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.page_label.configure(text=f"Page {self.current_page + 1} / {total_pages}")

        start = self.current_page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = self.current_results[start:end]

        cols = 3
        row = None
        for i, anime in enumerate(page_items):
            if i % cols == 0:
                row = ctk.CTkFrame(self.cards_frame, fg_color="transparent")
                row.pack(fill="x", pady=10, padx=10)

            card = ctk.CTkFrame(row, width=320, height=540, corner_radius=16)
            card.pack(side="left", padx=12, pady=8)
            card.pack_propagate(False)

            # Image
            img = cache_image(anime.get("image"))
            if img:
                ctk_img = make_ctk_image(img, size=(260, 360))
                lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                lbl.image = ctk_img
                lbl.pack(pady=(15, 8))
            else:
                ctk.CTkLabel(card, text="No Image", text_color="gray").pack(pady=100)

            # Title & Meta
            ctk.CTkLabel(card, text=anime.get("title", "Unknown"),
                         font=ctk.CTkFont(size=16, weight="bold"),
                         wraplength=280, justify="center").pack(pady=(8, 4))

            meta = f"{anime.get('score', 'N/A')} • {anime.get('year', '????')} • {anime.get('episodes', '?')} eps"
            ctk.CTkLabel(card, text=meta, text_color="#CCCCCC").pack()

            genres_txt = ", ".join(anime.get("genres", [])[:4])
            if len(anime.get("genres", [])) > 4: genres_txt += "..."
            ctk.CTkLabel(card, text=genres_txt, font=ctk.CTkFont(size=11), wraplength=280).pack(pady=6)

            ctk.CTkButton(card, text="More Details", width=220, height=38,
                          command=lambda a=anime: self.open_details(a)).pack(side="bottom", pady=15)

        # Pagination state
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if end < total else "disabled")

    def open_details(self, anime):
        win = ctk.CTkToplevel(self)
        win.title(anime.get("title", "Details"))
        win.geometry("800x950")

        # Build content first
        img = cache_image(anime.get("image"))
        if img:
            ctk_img = make_ctk_image(img, size=(440, 620))
            ctk.CTkLabel(win, image=ctk_img, text="").pack(pady=15)
        else:
            ctk.CTkLabel(win, text="No Image", font=ctk.CTkFont(size=16)).pack(pady=50)

        ctk.CTkLabel(win, text=anime.get("title", ""), font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=PALETTE[3]).pack(pady=(0, 12))

        info = f"Score: {anime.get('score','—')}  |  Year: {anime.get('year','—')}  |  Episodes: {anime.get('episodes','—')}\n" \
               f"Rating: {anime.get('rating','—')}  |  Studio: {anime.get('studios','—')}"
        ctk.CTkLabel(win, text=info, font=ctk.CTkFont(size=14)).pack(pady=10)

        syn = ctk.CTkTextbox(win, width=720, height=180, wrap="word")
        syn.pack(padx=20, pady=10)
        syn.insert("0.0", anime.get("synopsis", "No synopsis available."))
        syn.configure(state="disabled")

        ctk.CTkLabel(win, text="Genres: " + ", ".join(anime.get("genres", []))).pack(pady=5)

        btns = ctk.CTkFrame(win)
        btns.pack(pady=15)
        ctk.CTkButton(btns, text="Update", fg_color="#00A86B",
                      command=lambda: self.show_update_form(anime, win)).pack(side="left", padx=20)
        ctk.CTkButton(btns, text="Delete", fg_color="#FF3333",
                      command=lambda: self.confirm_delete(anime, win)).pack(side="left", padx=20)

        # Make modal only after everything is built
        win.transient(self)
        win.grab_set()

    def show_update_form(self, anime, details_win):
        details_win.destroy()
        win = ctk.CTkToplevel(self)
        win.title(f"Update – {anime.get('title')}")
        win.geometry("860x1000")

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=30, pady=30)

        entries = {}
        def add(label, key, default="", multi=False):
            f = ctk.CTkFrame(scroll)
            f.pack(fill="x", pady=6)
            ctk.CTkLabel(f, text=label, width=180, anchor="w").pack(side="left")
            if multi:
                w = ctk.CTkTextbox(f, height=130, wrap="word")
                w.insert("0.0", str(default or ""))
            else:
                w = ctk.CTkEntry(f, height=38)
                w.insert(0, str(default or ""))
            w.pack(side="left", fill="x", expand=True, padx=(12, 0))
            entries[key] = w

        add("Title", "title", anime.get("title"))
        add("English Title", "title_english", anime.get("title_english"))
        add("Japanese Title", "title_japanese", anime.get("title_japanese"))
        add("Image URL", "image", anime.get("image"))
        add("Score", "score", anime.get("score"))
        add("Year", "year", anime.get("year"))
        add("Episodes", "episodes", anime.get("episodes"))
        add("Rating", "rating", anime.get("rating"))
        add("Studios", "studios", anime.get("studios"))

        # Genres
        gframe = ctk.CTkFrame(scroll)
        gframe.pack(fill="x", pady=6)
        ctk.CTkLabel(gframe, text="Genres", width=180, anchor="w").pack(side="left")
        gentry = ctk.CTkEntry(gframe)
        gentry.insert(0, ", ".join(anime.get("genres", [])))
        gentry.pack(side="left", fill="x", expand=True, padx=(12, 0))
        entries["genres"] = gentry

        add("Synopsis", "synopsis", anime.get("synopsis"), multi=True)

        # Save/Cancel
        btns = ctk.CTkFrame(win)
        btns.pack(pady=25)
        def save():
            new_data = {
                "title": entries["title"].get().strip(),
                "title_english": entries["title_english"].get().strip() or None,
                "title_japanese": entries["title_japanese"].get().strip() or None,
                "image": entries["image"].get().strip() or None,
                "score": entries["score"].get().strip() or None,
                "year": entries["year"].get().strip() or None,
                "episodes": entries["episodes"].get().strip() or None,
                "rating": entries["rating"].get().strip() or None,
                "studios": entries["studios"].get().strip() or None,
                "genres": [g.strip() for g in entries["genres"].get().split(",") if g.strip()],
                "synopsis": entries["synopsis"].get("0.0", "end").strip() or None,
            }
            if redis_db.update_anime(anime.get("id"), new_data):
                msgbox.showinfo("Success", "Updated successfully!")
                win.destroy()
                threading.Thread(target=self.load_all_anime, daemon=True).start()
            else:
                msgbox.showerror("Error", "Update failed")

        ctk.CTkButton(btns, text="Save Changes", width=180, fg_color="#00A86B", command=save).pack(side="left", padx=25)
        ctk.CTkButton(btns, text="Cancel", width=180, command=win.destroy).pack(side="left", padx=25)

        win.transient(self)
        win.grab_set()

    def confirm_delete(self, anime, win):
        if msgbox.askyesno("Delete?", f"Delete {anime.get('title')}?"):
            if redis_db.delete_anime(anime.get("id")):
                msgbox.showinfo("Deleted", "Anime removed.")
            else:
                msgbox.showerror("Error", "Delete failed.")
            win.destroy()
            threading.Thread(target=self.load_all_anime, daemon=True).start()

    def next_page(self):
        if (self.current_page + 1) * ITEMS_PER_PAGE < len(self.current_results):
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()

# ----------------- Run -----------------
if __name__ == "__main__":
    app = AnimeApp()
    app.mainloop()
