from django.test import TestCase
from django.test import Client


class BaseTestCase(TestCase):

    def test_get_index_page_success(self):
        c = Client()
        response = c.get('/')
        self.assertEqual(response.status_code, 200)
