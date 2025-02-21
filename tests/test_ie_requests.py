import unittest
from ie_requests import IERequests

class TestIERequests(unittest.TestCase):
    def test_get_ie(self):
        scraper = IERequests()
        data = scraper.get_ie('084083166')
        self.assertIsInstance(data, list)

    def test_get_cnpj(self):
        scraper = IERequests()
        data = scraper.get_cnpj('05551608000390')
        self.assertIsInstance(data, list)

if __name__ == "__main__":
    unittest.main()
