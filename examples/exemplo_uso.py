from ie_requests import IERequests

scraper = IERequests()
resultado = scraper.get_cnpj('12345678000190')
print(resultado)
