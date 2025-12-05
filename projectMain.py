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
        self.geometry("1300x850")
        self.minsize(1100, 700)

        self.current_page = 0
        self.current_results = []
        self.is_loading = False

        self._build_ui()
        threading.Thread(target=self.load_all_anime, daemon=True).start()

    def _build_ui(self):
        self._build_header()
        self._build_search()
        self._build_cards_area()
        self._build_pagination()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=80, fg_color="transparent")
        header.pack(fill="x", pady=(12, 0))
        title = ctk.CTkLabel(header, text="Anime Explorer", font=ctk.CTkFont(size=36, weight="bold"),
                             text_color=PALETTE[0])
        title.pack(pady=15)

    def _build_search(self):
        frame = ctk.CTkFrame(self)
        frame.pack(pady=18, padx=30, fill="x")

        # Variables
        self.search_var = ctk.StringVar()
        self.genre_var = ctk.StringVar(value="(Any)")
        self.year_from_var = ctk.StringVar()
        self.year_to_var = ctk.StringVar()
        self.remove_genre_var = ctk.StringVar(value="Remove genre...")

        # Title Search
        ctk.CTkEntry(frame, width=380, height=44,
                     placeholder_text="Search by title...",
                     textvariable=self.search_var,
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 12))

        # Genre filter
        self.genre_option = ctk.CTkOptionMenu(frame, values=["(Any)"], variable=self.genre_var, width=160)
        self.genre_option.pack(side="left", padx=(0, 12))

        # Year range
        ctk.CTkLabel(frame, text="Year:", font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkEntry(frame, width=90, height=44, placeholder_text="From",
                     textvariable=self.year_from_var).pack(side="left", padx=(8, 4))
        ctk.CTkLabel(frame, text="→").pack(side="left", padx=4)
        ctk.CTkEntry(frame, width=90, height=44, placeholder_text="To",
                     textvariable=self.year_to_var).pack(side="left", padx=(4, 20))

        # Search button
        ctk.CTkButton(frame, text="Search", width=130, height=44,
                      command=self.on_search_click, fg_color="#0066FF", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=8)

        #Remove Genre Dropdown
        self.remove_genre_menu = ctk.CTkOptionMenu(
            frame,
            values=["Remove genre..."],
            variable=self.remove_genre_var,
            width=200,
            fg_color="#FF4444",
            button_color="#CC0000",
            button_hover_color="#AA0000",
            command=self.on_remove_genre_selected
        )
        self.remove_genre_menu.pack(side="left", padx=8)

        # Show All
        ctk.CTkButton(frame, text="Show All", width=130, height=44,
                      command=self.on_show_all).pack(side="left", padx=8)


        self.after(800, self.load_genres_into_dropdowns)

    def load_genres_into_dropdowns(self):
        try:
            genres = sorted(redis_db.get_distinct_genres())
            self.genre_option.configure(values=["(Any)"] + genres)
            self.remove_genre_menu.configure(values=["Remove genre..."] + genres)
        except:
            self.after(1000, self.load_genres_into_dropdowns)  # retry

    def _build_cards_area(self):
        self.cards_frame = ctk.CTkScrollableFrame(self)
        self.cards_frame.pack(fill="both", expand=True, padx=30, pady=12)

    def _build_pagination(self):
        pag = ctk.CTkFrame(self)
        pag.pack(pady=18)

        self.prev_btn = ctk.CTkButton(pag, text="Previous", width=140, command=self.prev_page)
        self.page_label = ctk.CTkLabel(pag, text="Page 1 / 1", width=180, font=ctk.CTkFont(size=14))
        self.next_btn = ctk.CTkButton(pag, text="Next", width=140, command=self.next_page)

        self.prev_btn.pack(side="left", padx=20)
        self.page_label.pack(side="left", padx=20)
        self.next_btn.pack(side="left", padx=20)

    # ----------------- Data & Search -----------------
    def load_all_anime(self):
        if self.is_loading: return
        self.is_loading = True
        try:
            anime_list = redis_db.get_all_anime()
            anime_list.sort(key=lambda x: x.get("title", "").lower())
            self.current_results = anime_list
            self.current_page = 0
        except Exception as e:
            msgbox.showerror("Error", f"Failed to load data:\n{e}")
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
            msgbox.showerror("Error", f"Search failed:\n{e}")
        finally:
            self.is_loading = False

    def on_show_all(self):
        self.search_var.set("")
        self.genre_var.set("(Any)")
        self.year_from_var.set("")
        self.year_to_var.set("")
        self.remove_genre_var.set("Remove genre...")
        threading.Thread(target=self.load_all_anime, daemon=True).start()

    def on_remove_genre_selected(self, selected_genre):
        if selected_genre == "Remove genre...":
            return

        if not msgbox.askyesno("Confirm Removal",
                               f"Are you sure you want to PERMANENTLY remove the genre:\n\n"
                               f"\"{selected_genre}\"\n\n"
                               f"from ALL anime in the database?\n"
                               f"This action cannot be undone.",
                               icon="warning"):
            self.remove_genre_var.set("Remove genre...")
            return

        # Perform removal
        count_removed_anime = redis_db.remove_genre(selected_genre)
        print(count_removed_anime)
        if count_removed_anime > 0:
            msgbox.showinfo("Success!",
                            f"Genre \"{selected_genre}\" has been removed from {count_removed_anime} anime!")
        else:
            msgbox.showwarning("Warning!",
                               f"the genre you selected (\"{selected_genre}\") was empty ")

        self.remove_genre_var.set("Remove genre...")
        threading.Thread(target=self.load_all_anime, daemon=True).start()


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

            card = ctk.CTkFrame(row, width=360, height=600, corner_radius=18, border_width=1, border_color="#333")
            card.pack(side="left", padx=15, pady=10)
            card.pack_propagate(False)

            img = cache_image(anime.get("image"))
            if img:
                ctk_img = make_ctk_image(img, size=(280, 400))
                lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                lbl.image = ctk_img
                lbl.pack(pady=(15, 8))
            else:
                ctk.CTkLabel(card, text="No Image", text_color="#666").pack(pady=120)

            ctk.CTkLabel(card, text=anime.get("title", "Unknown"),
                         font=ctk.CTkFont(size=17, weight="bold"),
                         wraplength=300, justify="center").pack(pady=(10, 5))

            meta = f"{anime.get('score', 'N/A')} • {anime.get('year', '????')} • {anime.get('episodes', '?')} eps"
            ctk.CTkLabel(card, text=meta, text_color="#BBBBBB").pack(pady=2)

            genres_txt = ", ".join(anime.get("genres", [])[:4])
            if len(anime.get("genres", [])) > 4: genres_txt += "..."
            ctk.CTkLabel(card, text=genres_txt, font=ctk.CTkFont(size=11), wraplength=300).pack(pady=8)

            ctk.CTkButton(card, text="More Details", width=240, height=40,
                          command=lambda a=anime: self.open_details(a)).pack(side="bottom", pady=18)

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
        ctk.CTkLabel(win, text="Genres: " + ", ".join(anime.get("genres", []))).pack(pady=5)

        btns = ctk.CTkFrame(win)
        btns.pack(pady=15)
        ctk.CTkButton(btns, text="Update", fg_color="#00A86B",
                      command=lambda: self.show_update_form(anime, win)).pack(side="left", padx=20)
        ctk.CTkButton(btns, text="Delete", fg_color="#FF3333",
                      command=lambda: self.confirm_delete(anime, win)).pack(side="left", padx=20)

        syn = ctk.CTkTextbox(win, width=720, height=180, wrap="word")
        syn.pack(padx=20, pady=10)
        syn.insert("0.0", anime.get("synopsis", "No synopsis available."))
        syn.configure(state="disabled")


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
