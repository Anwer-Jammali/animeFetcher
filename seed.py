#!/usr/bin/env python3

import requests
import redis
import json
import time



def safe(value):
	if value is None:
		return ""

	if isinstance(value, list):
		return ", ".join([safe(i) for i in value])

	# Convert non-strings to string
	value = str(value)

	value = value.encode("utf-8", "ignore").decode("utf-8")

	value = value.replace("\\n", "\n")
	value = value.replace('\\"', '"')

	return value
    
def getDuration(value):
	return value[:value.find(" ")]


def seed_anime(done_flag):
		
	# -----------------------------------------------------------
	# CONNECT TO REDIS
	# -----------------------------------------------------------
	r = redis.Redis(
		host="127.0.0.1",
		port=6379,
		password="",
		decode_responses=True
	)

	print("🚀 Connected to Redis!")
	
	# -----------------------------------------------------------
	# DELETE OLD ENTRIES
	# -----------------------------------------------------------
	print("🧹 Deleting old anime:* keys...")
	old_keys = r.keys("anime:*")
	if old_keys:
		r.delete(*old_keys)
		print(f"✔️ Deleted {len(old_keys)} previous anime entries.\n")

	# -----------------------------------------------------------
	# FETCH FROM API
	# -----------------------------------------------------------
	BASE_URL = "https://api.jikan.moe/v4/anime?page={}"

	page = 1
	anime_id = 1

	print("📡 Starting infinite anime download...\n")

	while True:
		print(f"➡️ Fetching page {page}...")
		try:
			response = requests.get(BASE_URL.format(page))
			if response.status_code != 200:
				print(f"❌ API Error {response.status_code}, retrying...")
				time.sleep(5)
				continue
			data = response.json()
		except Exception as e:
			print(f"⚠️ Request error: {e}, retrying...")
			time.sleep(5)
			continue

		anime_list = data.get("data", [])

		# STOP if the API has no more pages
		if (not anime_list or page == 10):
			print("\n🎉 FINISHED — API has no more anime.")
			break

		# -----------------------------------------------------------
		# SAVE ANIME
		# -----------------------------------------------------------
		for anime in anime_list:

				entry = {
			"title": safe(anime.get("title")),
			"title_english": safe(anime.get("title_english")),
			"title_japanese": safe(anime.get("title_japanese")),
			"synopsis": safe(anime.get("synopsis")),
			"year": safe(anime.get("year")),
			"episodes": safe(anime.get("episodes")),
			"duration": safe(getDuration(anime.get("duration"))),
			"score": safe(anime.get("score")),
			"rating": safe(anime.get("rating")),  # age rating
			"genres": safe([g["name"] for g in anime.get("genres", [])]),
			"themes": safe([t["name"] for t in anime.get("themes", [])]),
			"studios": safe([s["name"] for s in anime.get("studios", [])]),
			"image": safe(anime.get("images", {}).get("jpg", {}).get("image_url"))
				}

				r.hset(f"anime:{anime_id}", mapping=entry)
				print(f"✔️ Saved anime:{anime_id} → {entry['title'][:40]}")

				anime_id += 1
				#time.sleep(0.15)

		page += 1
		#time.sleep(0.5)
	
	#r.close()
	print("\n🔥 All anime saved successfully!")
	done_flag.set()
