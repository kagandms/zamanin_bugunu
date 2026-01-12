from main import get_smart_event
import os
from dotenv import load_dotenv

load_dotenv()

print("--- Final v3 Debug (Images) ---")

# 1. Full Flow Test
print("\n--- Testing Content & Image Gen ---")
# returns final_tweets, image_url, poll_options, raw_text
t_thread, i_url, polls, r_text = get_smart_event()

print(f"\nRaw Text: {r_text[:50]}...")
if t_thread:
    print(f"Tweet Count: {len(t_thread)}")
    print(f"Tweet 1: {t_thread[0][:50]}...")
else:
    print("No tweets generated.")

print(f"\nImage URL: {i_url}")
if "pollinations.ai" in str(i_url):
    print("✅ SUCCESS: AI generated image URL used.")
elif "wikipedia" in str(i_url):
    print("✅ SUCCESS: Wikipedia image URL used.")
else:
    print("⚠️ WARNING: No image URL found.")

if polls:
    print(f"Polls: {polls}")
