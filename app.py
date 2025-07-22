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
        rising_sign = asc_sign  # Eski kodda da vardı, koruyoruz

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
        for i in range(len(planets)):
            for j in range(i + 1, len(planets)):
                p1 = planets[i]
                p2 = planets[j]
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

        print(f"[INFO] Hesaplanan gezegenler: {[p['name'] for p in planets]}")
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
