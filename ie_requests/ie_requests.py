import requests
from bs4 import BeautifulSoup
import re

class IERequests:
    BASE_URL = 'http://hnfe.sefaz.ba.gov.br/servicos/nfenc/Modulos/Geral/NFENC_consulta_cadastro_ccc.aspx'
    FIELDS = ['cnpj', 'ie', 'razao_social', 'uf', 'situacao']

    def __init__(self):
        self.session = requests.Session()
        self.payload = {}
        self.record_count = 0
        self.pages = {'current': 0, 'total': 0}
        self._initialize()

    def _initialize(self):
        response = self._request('GET', self.BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        self._extract_payload(soup)

    def _request(self, method, url, **kwargs):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        kwargs.setdefault('headers', headers)
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _extract_payload(self, soup):
        input_fields = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        for field in input_fields:
            self.payload[field] = soup.find('input', {'name': field})['value']
        self.payload.update({
            '__VIEWSTATEENCRYPTED': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'txtCNPJ': '',
            'txtie': '',
            'CmdUF': '',
            'CmdSituacao': '99',
            'AplicarFiltro': 'Aplicar+Filtro'
        })

    def get_ie(self, ie):
        self.payload['txtie'] = ie
        return self._fetch_all_data()

    def get_cnpj(self, cnpj):
        self.payload['txtCNPJ'] = cnpj
        return self._fetch_all_data()

    def _fetch_all_data(self):
        results = []
        while True:
            response = self._request('POST', self.BASE_URL, data=self.payload)
            results.extend(self._extract_data(response.text))
            if self.pages['current'] >= self.pages['total']:
                break
            self._prepare_next_page(response.text)
        return results

    def _extract_data(self, html):
        soup = BeautifulSoup(html, "html.parser")
        data_list = []
        table = soup.find('table', {'id': 'Grid'})
        if not table:
            return data_list
        rows = table.find_all('tr')[1:]
        for row in rows:
            if row.find_all('a'):
                self._handle_pagination(row)
            else:
                cols = row.find_all('td')
                data = {field: col.text.strip() for field, col in zip(self.FIELDS, cols)}
                data['cnpj'] = re.sub(r'\D', '', data['cnpj'])
                data_list.append(data)
        return data_list

    def _handle_pagination(self, row):
        self.pages['current'] = int(row.find('span').text.strip())
        last_page_link = row.find_all('a')[-1]['href']
        self.pages['total'] = int(last_page_link.split('Page$')[-1].rstrip("')"))

    def _prepare_next_page(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            self.payload[field] = soup.find('input', {'name': field})['value']
        self.payload['__EVENTTARGET'] = 'Grid'
        self.payload['__EVENTARGUMENT'] = f'Page${self.pages["current"] + 1}'
        self.payload.pop('AplicarFiltro', None)
