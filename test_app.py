import unittest
from app import app

class RideRequestTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_valid_ride_request(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 1,
            "pickup_lon": 46.6753,
            "pickup_lat": 24.7136,
            "dropoff_lon": 46.6588,
            "dropoff_lat": 24.7275,
            "category_name": "economy"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("ride_id", data)
        self.assertIn("estimated_duration", data)
        self.assertIn("estimated_fare", data)
        self.assertIn("estimated_arrival", data)

    def test_missing_field(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 1,
            "pickup_lon": 46.6753
            # missing other required fields
        })
        self.assertEqual(response.status_code, 500)

    def test_invalid_category(self):
        response = self.client.post('/ride-request', json={
            "rider_id": 1,
            "pickup_lon": 46.6753,
            "pickup_lat": 24.7136,
            "dropoff_lon": 46.6588,
            "dropoff_lat": 24.7275,
            "category_name": "spaceship"  # Invalid category
        })
        self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    unittest.main()