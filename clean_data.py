import csv
import json
import os
import re
from collections import Counter, defaultdict

HONG_KONG_ISLAND = [
    "中環", "上環", "西營盤", "堅尼地城", "石塘咀", "西半山", "中半山",
    "山頂", "薄扶林", "香港仔", "黃竹坑", "鴨脷洲", "淺水灣", "跑馬地",
    "大坑", "銅鑼灣", "天后", "炮台山", "北角", "北角半山", "鰂魚涌",
    "西灣河", "筲箕灣", "柴灣", "小西灣", "金鐘", "灣仔",
]

KOWLOON = [
    "尖沙咀", "佐敦", "油麻地", "旺角", "太子", "深水埗", "長沙灣",
    "荔枝角", "美孚", "南昌", "九龍站", "奧運", "大角咀", "紅磡",
    "黃埔", "何文田", "九龍塘", "九龍城", "新蒲崗", "啟德", "觀塘",
    "牛頭角", "九龍灣", "藍田", "油塘", "鑽石山", "黃大仙", "樂富",
    "石硤尾", "又一村", "牛池灣",
]

NEW_TERRITORIES = [
    "葵涌", "葵芳", "荃灣", "深井(荃灣)", "大窩口", "青衣",
    "屯門", "屯門(青山公路)", "洪水橋", "天水圍", "元朗",
    "粉嶺", "上水", "大埔", "太和", "沙田", "大圍", "火炭",
    "馬鞍山", "白石角", "西貢", "清水灣", "將軍澳", "康城",
    "坑口", "寶琳", "調景嶺", "東涌", "馬灣", "南大嶼山", "坪洲",
]

def get_region(district):
    if district in HONG_KONG_ISLAND:
        return "Hong Kong Island"
    elif district in KOWLOON:
        return "Kowloon"
    elif district in NEW_TERRITORIES:
        return "New Territories"
    return "Unknown"

def clean_layout(layout):
    layout = layout.strip()
    if not layout:
        return "Unknown"
    if "開放式" in layout:
        return "Open Studio"
    m = re.search(r"(\d+)\s*房", layout)
    if m:
        rooms = int(m.group(1))
        if rooms <= 1:
            return "1 Bedroom"
        elif rooms == 2:
            return "2 Bedrooms"
        elif rooms == 3:
            return "3 Bedrooms"
        elif rooms == 4:
            return "4 Bedrooms"
        else:
            return "5+ Bedrooms"
    return "Unknown"

def clean_tags(tags_str):
    if not tags_str:
        return []
    tags = [t.strip() for t in tags_str.split(";") if t.strip()]
    return [t for t in tags if not ("房" in t and "浴室" in t)]

def process():
    base = os.path.dirname(__file__)
    raw_file = os.path.join(base, "..", "data", "raw", "hk_rental_listings.csv")
    out_dir = os.path.join(base, "..", "data", "processed")
    os.makedirs(out_dir, exist_ok=True)

    listings = []
    with open(raw_file, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            price = float(row.get("price_hkd", 0))
            size = float(row.get("size_sqft", 0))
            district = row.get("district", "").strip()
            if price <= 0 or not district:
                continue
            estate = row.get("estate", "").strip() or district
            listings.append({
                "district": district,
                "region": get_region(district),
                "estate": estate,
                "floor_level": row.get("floor_level", "").strip(),
                "size_sqft": size,
                "price_hkd": price,
                "price_per_sqft": round(price / size, 1) if size > 0 else 0,
                "layout": clean_layout(row.get("layout", "")),
                "tags": clean_tags(row.get("tags", "")),
                "url": row.get("url", ""),
            })

    print(f"Cleaned {len(listings)} valid records")\n
    # Region stats
    reg_d = defaultdict(lambda: {"prices": [], "sizes": [], "pps": []})
    for l in listings:
        r = l["region"]
        reg_d[r]["prices"].append(l["price_hkd"])
        reg_d[r]["sizes"].append(l["size_sqft"])
        reg_d[r]["pps"].append(l["price_per_sqft"])

    def st(arr):
        s = sorted(arr)
        n = len(s)
        return {"min": s[0], "max": s[-1], "median": s[n//2], "mean": round(sum(s)/n, 1), "count": n}

    reg_summary = {r: {"count": len(d["prices"]), "price": st(d["prices"]), "size": st(d["sizes"]), "price_per_sqft": st(d["pps"])} for r, d in reg_d.items()}

    # District stats
    dist_d = defaultdict(lambda: {"prices": [], "sizes": [], "pps": []})
    for l in listings:
        dist_d[l["district"]]["prices"].append(l["price_hkd"])
        dist_d[l["district"]]["sizes"].append(l["size_sqft"])
        dist_d[l["district"]]["pps"].append(l["price_per_sqft"])

    dist_summary = []
    for d, data in sorted(dist_d.items()):
        p = data["prices"]
        if len(p) < 3:
            continue
        dist_summary.append({
            "district": d, "region": get_region(d), "count": len(p),
            "price_mean": round(sum(p)/len(p), 1), "price_median": round(sorted(p)[len(p)//2], 1),
            "price_min": min(p), "price_max": max(p),
            "size_mean": round(sum(data["sizes"])/len(data["sizes"]), 1),
            "price_per_sqft_mean": round(sum(data["pps"])/len(data["pps"]), 1),
        })

    layout_dist = dict(Counter(l["layout"] for l in listings).most_common())
    floor_dist = dict(Counter(l["floor_level"] for l in listings if l["floor_level"]).most_common())

    output = {
        "meta": {"source": "28Hse.com", "scraped_at": "2026-06-20", "total_listings": len(listings), "districts_covered": len(dist_summary)},
        "region_summary": reg_summary,
        "district_summary": dist_summary,
        "layout_distribution": layout_dist,
        "floor_distribution": floor_dist,
        "listings": listings,
    }

    out_file = os.path.join(out_dir, "dashboard_data.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_file}")

    print("\nQuick Summary:")
    print(f"  Total: {len(listings)}")
    for r, s in sorted(reg_summary.items()):
        print(f"  {r}: {s['count']} listings, median ${s['price']['median']:,}/mo")
    print(f"  Layouts: {layout_dist}")

if __name__ == "__main__":
    process()
