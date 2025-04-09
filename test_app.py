import unittest
from app import app

class RideRequestTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_valid_ride_request(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 3,
            "pickup_lat": 24.7136,
            "pickup_lng": 46.6753,
            "dropoff_lat": 24.7275,
            "dropoff_lng": 46.6588,
            "category_name": "economy",
            "price_multiplier": 1.0,
            "surge_multiplier": 1.5,
            "surge_id": 2,
            "estimated_duration": 12,
            "estimated_arrival_time": 5,
            "base_fare": 10.0,
            "total_fare": 15.0
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("ride_id", response.get_json())

    def test_missing_field(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 3,
            "pickup_lat": 24.7136
            # missing the rest
        })
        self.assertEqual(response.status_code, 500)

    def test_invalid_category(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 3,
            "pickup_lat": 24.7136,
            "pickup_lng": 46.6753,
            "dropoff_lat": 24.7275,
            "dropoff_lng": 46.6588,
            "category_name": "spaceship",  # invalid category
            "price_multiplier": 1.0,
            "surge_multiplier": 1.5,
            "surge_id": 2,
            "estimated_duration": 12,
            "estimated_arrival_time": 5,
            "base_fare": 10.0,
            "total_fare": 15.0
        })
        self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    unittest.main()