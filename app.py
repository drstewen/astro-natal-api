import os

# --- Ephemeris env ve dosya kontrolleri (en başta) ---
os.environ['SWEPHEPATH'] = "/usr/share/swisseph:/usr/local/share/swisseph"
print("SWEPHEPATH:", os.environ.get("SWEPHEPATH"))

try:
    print("[DEBUG] /usr/share/swisseph içeriği:", os.listdir("/usr/share/swisseph"))
except Exception as e:
    print("[DEBUG] /usr/share/swisseph erişilemedi:", e)

try:
    print("[DEBUG] /usr/local/share/swisseph içeriği:", os.listdir("/usr/local/share/swisseph"))
except Exception as e:
    print("[DEBUG] /usr/local/share/swisseph erişilemedi:", e)

import swisseph as swe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

LOCAL_PATH = r"C:\Users\mertd\OneDrive\Masaüstü\astro_backend\ephe"
DOCKER_PATH = '/app/ephe/'

if os.path.exists(DOCKER_PATH):
    swe.set_ephe_path(DOCKER_PATH)
    print(f"[INFO] Ephemeris yol (docker): {DOCKER_PATH}")
    try:
        print(f"[INFO] Klasördeki dosyalar: {os.listdir(DOCKER_PATH)}")
    except Exception as e:
        print(f"[ERROR] Ephemeris klasörü okunamadı: {e}")
else:
    swe.set_ephe_path(LOCAL_PATH)
    print(f"[INFO] Ephemeris yol (local): {LOCAL_PATH}")
    try:
        print(f"[INFO] Klasördeki dosyalar: {os.listdir(LOCAL_PATH)}")
    except Exception as e:
        print(f"[ERROR] Ephemeris klasörü okunamadı: {e}")

ZODIAC_SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık"
]

def zodiac_name(longitude):
    idx = int(longitude // 30)
    return ZODIAC_SIGNS[idx % 12]

@app.route('/natal_chart', methods=['POST'])
def natal_chart():
    try:
        data = request.json
        year = data['year']
        month = data['month']
        day = data['day']
        hour = data['hour']
        minute = data['minute']
        lat = data['lat']
        lon = data['lon']
        tz_offset = data['tz_offset']

        ut_hour = hour + (minute / 60.0) - tz_offset
        jd = swe.julday(year, month, day, ut_hour, swe.GREG_CAL)

        asc_mc = swe.houses(jd, lat, lon)
        houses_raw = asc_mc[0]
        asc_deg = houses_raw[0]  # ASC (Ascendant) derecesi
        asc_sign = zodiac_name(asc_deg)
        rising_sign = asc_sign

        planet_codes = {
            'Güneş': swe.SUN,
            'Ay': swe.MOON,
            'Merkür': swe.MERCURY,
            'Venüs': swe.VENUS,
            'Mars': swe.MARS,
            'Jüpiter': swe.JUPITER,
            'Satürn': swe.SATURN,
            'Uranüs': swe.URANUS,
            'Neptün': swe.NEPTUNE,
            'Plüto': swe.PLUTO,
            'Şiron': swe.CHIRON,
            'Kuzey Ay Düğümü': swe.TRUE_NODE,
            'Lilith (Kara Ay)': swe.MEAN_APOG,
            'Ceres': swe.CERES,
            'Pallas': swe.PALLAS,
            'Juno': swe.JUNO,
            'Vesta': swe.VESTA
        }

        planets = []
        for name, code in planet_codes.items():
            try:
                result, _ = swe.calc_ut(jd, code)
                if result and len(result) >= 4:
                    lon_val = result[0]
                    velocity = result[3]
                    is_retro = velocity < 0
                    planet_obj = {
                        'name': name,
                        'sign': zodiac_name(lon_val),
                        'degree': round(lon_val % 30, 2),
                        'absolute_long': round(lon_val, 6),
                        'is_retro': is_retro
                    }
                elif result and len(result) >= 1:
                    lon_val = result[0]
                    planet_obj = {
                        'name': name,
                        'sign': zodiac_name(lon_val),
                        'degree': round(lon_val % 30, 2),
                        'absolute_long': round(lon_val, 6),
                        'is_retro': False
                    }
                else:
                    planet_obj = {
                        'name': name,
                        'sign': None,
                        'degree': None,
                        'absolute_long': None,
                        'is_retro': None
                    }
            except Exception as e:
                print(f"[WARN] {name} gezegeni hesaplanamadı! Hata: {e}")
                planet_obj = {
                    'name': name,
                    'sign': None,
                    'degree': None,
                    'absolute_long': None,
                    'is_retro': None
                }
            if planet_obj['degree'] is None:
                print(f"[DEBUG] {name} için degree None döndü!")
            planets.append(planet_obj)

        # Güney Ay Düğümü ekleniyor
        try:
            node_result, _ = swe.calc_ut(jd, swe.TRUE_NODE)
            if node_result and len(node_result) >= 1:
                true_node = node_result[0]
                south_node = (true_node + 180) % 360
                planets.append({
                    'name': 'Güney Ay Düğümü',
                    'sign': zodiac_name(south_node),
                    'degree': round(south_node % 30, 2),
                    'absolute_long': round(south_node, 6),
                    'is_retro': False
                })
        except Exception as e:
            print(f"[WARN] Güney Ay Düğümü eklenemedi: {e}")
            planets.append({
                'name': 'Güney Ay Düğümü',
                'sign': None,
                'degree': None,
                'absolute_long': None,
                'is_retro': None
            })

        # ASC'yi gezegenler listesine gezegen gibi ekle
        asc_obj = {
            'name': 'ASC',
            'sign': asc_sign,
            'degree': round(asc_deg % 30, 2),
            'absolute_long': round(asc_deg, 6),
            'is_retro': None
        }
        planets_with_asc = [asc_obj] + planets

        # Evlerin başlangıç dereceleri ve burçları
        houses = []
        for i, deg in enumerate(houses_raw[:12]):
            houses.append({
                'number': i + 1,
                'sign': zodiac_name(deg),
                'degree': round(deg % 30, 2),
                'absolute_long': round(deg, 6)
            })

        # Aspect hesaplama
        def get_aspect_type(diff):
            aspects_def = [
                ('conjunction', 0, 8),
                ('opposition', 180, 8),
                ('square', 90, 6),
                ('trine', 120, 6),
                ('sextile', 60, 4),
            ]
            for name, degree, orb in aspects_def:
                if abs(diff - degree) <= orb:
                    return name
            return None

        aspects = []
        for i in range(len(planets_with_asc)):
            for j in range(i + 1, len(planets_with_asc)):
                p1 = planets_with_asc[i]
                p2 = planets_with_asc[j]
                long1 = p1['absolute_long']
                long2 = p2['absolute_long']
                if long1 is None or long2 is None:
                    continue
                diff = abs(long1 - long2)
                if diff > 180:
                    diff = 360 - diff
                aspect_type = get_aspect_type(diff)
                if aspect_type:
                    aspects.append({
                        'planet1': p1['name'],
                        'planet2': p2['name'],
                        'type': aspect_type,
                        'angle': round(diff, 2)
                    })

        print(f"[INFO] Hesaplanan gezegenler (ASC dahil): {[p['name'] for p in planets_with_asc]}")
        print(f"[INFO] Ev dereceleri: {houses_raw[:12]}")
        print(f"[INFO] Toplam açı: {len(aspects)}")

        return jsonify({
            'sun_sign': next((p['sign'] for p in planets if p['name'] == 'Güneş'), ''),
            'moon_sign': next((p['sign'] for p in planets if p['name'] == 'Ay'), ''),
            'rising_sign': rising_sign,
            'asc_deg': round(asc_deg, 6),
            'asc_sign': asc_sign,
            'planets': planets,
            'houses': houses,
            'aspects': aspects
        })

    except Exception as err:
        print(f"[ERROR] natal_chart endpoint hatası: {err}")
        return jsonify({'error': str(err)}), 500

# ---- AY TAKVİMİ ENDPOINT ve Yardımcı Fonksiyonlar ----

# Ay fazlarını tanımla
MOON_PHASES = [
    ("New Moon", 0),
    ("Waxing Crescent", 45),
    ("First Quarter", 90),
    ("Waxing Gibbous", 135),
    ("Full Moon", 180),
    ("Waning Gibbous", 225),
    ("Last Quarter", 270),
    ("Waning Crescent", 315),
    ("New Moon", 360),
]
MOON_PHASE_ICONS = {
    "New Moon": "🌑",
    "Waxing Crescent": "🌒",
    "First Quarter": "🌓",
    "Waxing Gibbous": "🌔",
    "Full Moon": "🌕",
    "Waning Gibbous": "🌖",
    "Last Quarter": "🌗",
    "Waning Crescent": "🌘"
}
def get_moon_phase(angle):
    for phase, deg in MOON_PHASES:
        if angle <= deg:
            return phase
    return "New Moon"

@app.route('/moon_calendar', methods=['GET'])
def moon_calendar():
    try:
        from calendar import monthrange
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        tz_offset = float(request.args.get('tz_offset', 3))  # Default Türkiye
        lat = float(request.args.get('lat', 41.0082))        # Default İstanbul
        lon = float(request.args.get('lon', 28.9784))

        days_in_month = monthrange(year, month)[1]

        calendar_data = []
        for day in range(1, days_in_month + 1):
            ut_hour = 12 - tz_offset  # Gündüzün ortası
            jd = swe.julday(year, month, day, ut_hour, swe.GREG_CAL)
            moon_pos, _ = swe.calc_ut(jd, swe.MOON)
            moon_long = moon_pos[0]
            moon_sign = zodiac_name(moon_long)
            moon_deg = round(moon_long % 30, 2)

            sun_pos, _ = swe.calc_ut(jd, swe.SUN)
            sun_long = sun_pos[0]
            phase_angle = (moon_long - sun_long) % 360

            phase = get_moon_phase(phase_angle)
            phase_icon = MOON_PHASE_ICONS.get(phase, "")

            calendar_data.append({
                "date": f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}",
                "moon_sign": moon_sign,
                "moon_degree": moon_deg,
                "phase": phase,
                "phase_icon": phase_icon,
                "phase_angle": round(phase_angle, 2)
            })

        return jsonify({
            "year": year,
            "month": month,
            "days": calendar_data
        })
    except Exception as e:
        print(f"[ERROR] moon_calendar endpoint hatası: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
