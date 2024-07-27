from django.conf import settings
from django.shortcuts import render
import requests
from datetime import datetime, timedelta
from django.http import HttpResponseBadRequest
from .models import SearchHistory

GEOCODING_API_URL = 'https://nominatim.openstreetmap.org/search'


def get_weather(city):
    base_url = "https://api.open-meteo.com/v1/forecast"
    now = datetime.utcnow()
    start_time = now.isoformat()
    end_time = (now + timedelta(days=1)).isoformat()

    params = {
        'latitude': 0,  # Placeholder, будет заменен реальными данными
        'longitude': 0,  # Placeholder, будет заменен реальными данными
        'hourly': 'temperature_2m',
        'start': start_time,
        'end': end_time
    }

    # Получение координат города
    geo_url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; MyWeatherApp/1.0; +http://myweatherapp.example.com)'
    }
    try:
        geo_response = requests.get(geo_url, headers=headers)
        geo_response.raise_for_status()  # Проверка на ошибки HTTP
        geo_data = geo_response.json()
    except requests.exceptions.RequestException as e:
        return None, f"Ошибка при запросе координат: {e}"
    except ValueError:
        return None, "Ошибка декодирования ответа от API координат"

    if not geo_data:
        return None, "Город не найден"

    params['latitude'] = geo_data[0]['lat']
    params['longitude'] = geo_data[0]['lon']

    # Запрос к Open-Meteo API
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        weather_json = response.json()
    except requests.exceptions.RequestException as e:
        return None, f"Ошибка при запросе прогноза погоды: {e}"
    except ValueError:
        return None, "Ошибка декодирования ответа от API погоды"

    if 'hourly' not in weather_json:
        return None, "Ошибка при получении прогноза погоды"

    temperatures = weather_json['hourly']['temperature_2m']
    times = weather_json['hourly']['time']

    weather_data = []
    for time, temp in zip(times, temperatures):
        weather_data.append({
            'time': datetime.fromisoformat(time).strftime('%Y-%m-%d %H:%M'),
            'temperature': temp
        })

    return weather_data, None



# ----------------  Валидация города -------------------------

def validate_city(city):
    params = {
        'q': city,  # Поиск по введенному тексту
        'format': 'json',  # Формат ответа
        'addressdetails': 1,  # Включение подробностей адреса
        # 'limit': 1   Ограничение числа результатов (можно изменить)
    }

    response = requests.get(settings.GEOCODING_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        # Проверка наличия хотя бы одного результата
        if data:
            # Проверка, что результат соответствует ожидаемому городу
            result = data[0]  # Используем первый результат
            return result['display_name'].lower().startswith(city.lower())
    return False


def index(request):
    weather_data = None
    error = None
    city = None

    if request.method == 'POST':
        city = request.POST.get('city')
        if city:
            # Получение ключа сессии
            session_key = request.session.session_key
            if not session_key:
                request.session.create()  # Создание нового ключа сессии, если его нет

            # Сохранение истории поиска
            try:
                SearchHistory.objects.create(session_key=request.session.session_key, city=city)
            except Exception as e:
                return HttpResponseBadRequest(f"Error saving search history: {e}")

            # Получение прогноза погоды
            weather_data, error = get_weather(city)

    return render(request, 'weather/index.html', {
        'weather_data': weather_data,
        'error': error,
        'city': city  # Передаем город в шаблон
    })

