from django.test import Client
from django.urls import reverse
from unittest.mock import patch
from django.contrib.auth.models import User
from .views import get_weather
from django.test import TestCase
from django.utils import timezone
from .models import SearchHistory


class WeatherTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('index')  # Убедитесь, что у вас есть путь с именем 'index'
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_index_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'weather/index.html')

    @patch('weather.views.get_weather')
    def test_index_view_post_valid_city(self, mock_get_weather):
        mock_get_weather.return_value = (
            [{'time': '2023-07-26 12:00', 'temperature': 25.0}],
            None
        )
        response = self.client.post(self.url, {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2023-07-26 12:00')
        self.assertContains(response, '25.0')

        # Проверка сохранения истории
        self.assertTrue(SearchHistory.objects.filter(user=self.user, city='London').exists())

    @patch('weather.views.get_weather')
    def test_index_view_post_invalid_city(self, mock_get_weather):
        mock_get_weather.return_value = (None, 'Город не найден')
        response = self.client.post(self.url, {'city': 'InvalidCity'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Город не найден')

    def test_get_weather_valid_response(self):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'hourly': {
                    'time': ['2023-07-26T12:00:00Z'],
                    'temperature_2m': [25.0]
                }
            }
            weather_data, error = get_weather('London')
            self.assertIsNone(error)
            self.assertIsNotNone(weather_data)
            self.assertEqual(len(weather_data), 1)
            self.assertEqual(weather_data[0]['time'], '2023-07-26 12:00')
            self.assertEqual(weather_data[0]['temperature'], 25.0)

    def test_get_weather_invalid_response(self):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 404
            weather_data, error = get_weather('InvalidCity')
            self.assertIsNotNone(error)
            self.assertIsNone(weather_data)

    def test_search_history(self):
        SearchHistory.objects.create(user=self.user, city='London')
        response = self.client.get(reverse('search_history'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, [
            {
                'city': 'London',
                'timestamp': SearchHistory.objects.get(user=self.user, city='London').timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        ])

    def test_city_stats_api(self):
        SearchHistory.objects.create(user=self.user, city='London')
        response = self.client.get(reverse('city_stats'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'London': 1})


class SearchHistoryTests(TestCase):
    def setUp(self):
        self.client.cookies.load({})  # Обновление cookies для нового сеанса

    def test_save_search_history(self):
        response = self.client.post('/', {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SearchHistory.objects.filter(session_key=self.client.session.session_key, city='London').exists())

    def test_search_history_display(self):
        SearchHistory.objects.create(session_key=self.client.session.session_key, city='London', timestamp=timezone.now())
        response = self.client.get('/')
        self.assertContains(response, 'London')