# debug_coords.py
from tools.knowledge_tool import get_destination_info

dest_info = get_destination_info("Skardu")
attractions = dest_info.get("attractions", [])
print(f"Total attractions: {len(attractions)}")
for a in attractions[:5]:
    print(f"  {a['name']}: lat={a.get('lat')}, lon={a.get('lon')}")