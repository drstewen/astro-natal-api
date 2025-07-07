from flask import Flask, request, jsonify
from flask_cors import CORS
import pyswisseph as swe
import datetime
import os

app = Flask(__name__)
CORS(app)

# Türkçe burç isimleri
ZODIAC_SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık"
]

def zodiac_name(longitude):
    idx = int(longitude // 30)
    return ZODIAC_SIGNS[idx % 12]

@app.route('/natal_chart', methods=['POST'])
def natal_chart():
    data = request.json
    year = data['year']
    month = data['month']
    day = data['day']
    hour = data['hour']
    minute = data['minute']
    lat = data['lat']
    lon = data['lon']
    tz_offset = data['tz_offset']

    # UTC saat
    ut_hour = hour + (minute / 60.0) - tz_offset
    jd = swe.julday(year, month, day, ut_hour, swe.GREG_CAL)

    # Evler ve yükselen burç
    asc_mc = swe.houses(jd, lat, lon, b'A')
    asc_deg = asc_mc[0][0]
    rising_sign = zodiac_name(asc_deg)


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
            if result and len(result) >= 1:
                lon_val = result[0]
                planets.append({
                    'name': name,
                    'sign': zodiac_name(lon_val),
                    'degree': round(lon_val % 30, 2)
                })
        except Exception as e:
            
            continue

    
    try:
        node_result, _ = swe.calc_ut(jd, swe.TRUE_NODE)
        if node_result and len(node_result) >= 1:
            true_node = node_result[0]
            south_node = (true_node + 180) % 360
            planets.append({
                'name': 'Güney Ay Düğümü',
                'sign': zodiac_name(south_node),
                'degree': round(south_node % 30, 2)
            })
    except Exception as e:
        pass

    
    houses_raw = asc_mc[0]
    houses = []
    for i, deg in enumerate(houses_raw[:12]):
        houses.append({
            'number': i + 1,
            'sign': zodiac_name(deg),
            'degree': round(deg % 30, 2)
        })

    aspects = []  

    return jsonify({
        'sun_sign': next((p['sign'] for p in planets if p['name'] == 'Güneş'), ''),
        'moon_sign': next((p['sign'] for p in planets if p['name'] == 'Ay'), ''),
        'rising_sign': rising_sign,
        'planets': planets,
        'houses': houses,
        'aspects': aspects,
    })

if __name__ == '__main__':
    
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
