import re
from dataclasses import dataclass
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

@dataclass
class CadastroIE:
    cnpj: str
    ie: str
    razao_social: str
    uf: str
    situacao: str

class IERequests:
    BASE_URL = "http://hnfe.sefaz.ba.gov.br/servicos/nfenc/Modulos/Geral/NFENC_consulta_cadastro_ccc.aspx"
    FIELDS = ["cnpj", "ie", "razao_social", "uf", "situacao"]

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.timeout = timeout
        self.payload: Dict[str, str] = {}
        self.pages = {"current": 0, "total": 0}

        retry = Retry(
            total=5,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET", "POST"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._initialize()

    def _initialize(self):
        resp = self._request("GET", self.BASE_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        self._extract_payload(soup)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        kwargs.setdefault("headers", headers)
        kwargs.setdefault("timeout", self.timeout)
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        return resp

    def _extract_payload(self, soup: BeautifulSoup):
        def val(name: str) -> str:
            el = soup.find("input", {"name": name})
            return el.get("value", "") if el else ""

        self.payload = {
            "__VIEWSTATE": val("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": val("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": val("__EVENTVALIDATION"),
            "__VIEWSTATEENCRYPTED": "",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "txtCNPJ": "",
            "txtie": "",
            "CmdUF": "",           # opcional: "BA", "SP", etc.
            "CmdSituacao": "99",   # 99 = todas (ajuste conforme necessário)
            "AplicarFiltro": "Aplicar+Filtro",
        }

    def get_ie(self, ie: str) -> List[CadastroIE]:
        self._reset_filters()
        self.payload["txtie"] = _only_digits(ie)
        return self._fetch_all_data()

    def get_cnpj(self, cnpj: str) -> List[CadastroIE]:
        self._reset_filters()
        self.payload["txtCNPJ"] = _only_digits(cnpj)
        return self._fetch_all_data()

    def search(self, *, cnpj: Optional[str] = None, ie: Optional[str] = None,
               uf: str = "", situacao: str = "99") -> List[CadastroIE]:
        self._reset_filters()
        if cnpj:
            self.payload["txtCNPJ"] = _only_digits(cnpj)
        if ie:
            self.payload["txtie"] = _only_digits(ie)
        self.payload["CmdUF"] = uf or ""
        self.payload["CmdSituacao"] = situacao or "99"
        return self._fetch_all_data()

    def _reset_filters(self):
        for k in ("txtCNPJ", "txtie", "CmdUF", "CmdSituacao"):
            self.payload[k] = "" if k != "CmdSituacao" else "99"
        self.payload["AplicarFiltro"] = "Aplicar+Filtro"
        self.pages = {"current": 0, "total": 0}

    def _fetch_all_data(self) -> List[CadastroIE]:
        results: List[CadastroIE] = []
        first = True
        while True:
            resp = self._request("POST", self.BASE_URL, data=self.payload)
            page_items, pager = self._extract_data(resp.text)
            results.extend(page_items)

            if pager["current"] >= pager["total"]:
                break
            self._prepare_next_page(resp.text, pager["current"] + 1)

            if first:
                self.payload.pop("AplicarFiltro", None)
                first = False

        return results

    def _extract_data(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        data: List[CadastroIE] = []

        table = soup.find("table", {"id": "Grid"})
        if not table:
            return data, {"current": 1, "total": 1}

        rows = table.find_all("tr")
        if len(rows) <= 1:
            return data, {"current": 1, "total": 1}

        pager_tr = rows[-1]
        body_rows = rows[1:-1] if pager_tr.find("a") or pager_tr.find("span") else rows[1:]

        for row in body_rows:
            cols = row.find_all("td")
            if len(cols) < len(self.FIELDS):
                continue
            record = {f: cols[i].get_text(strip=True) for i, f in enumerate(self.FIELDS)}
            record["cnpj"] = _only_digits(record["cnpj"])
            data.append(CadastroIE(**record))

        current, total = 1, 1
        if pager_tr:
            last_link = pager_tr.find_all("a")[-1] if pager_tr.find_all("a") else None
            span_current = pager_tr.find("span")
            m_total = re.search(r"Page\$(\d+)", last_link.get("href", "")) if last_link else None
            try:
                current = int(span_current.get_text(strip=True)) if span_current else 1
                total = int(m_total.group(1)) if m_total else current
            except ValueError:
                current, total = 1, 1

        return data, {"current": current, "total": total}

    def _prepare_next_page(self, html: str, next_page: int):
        soup = BeautifulSoup(html, "html.parser")
        def val(name: str) -> str:
            el = soup.find("input", {"name": name})
            return el.get("value", "") if el else ""

        self.payload["__VIEWSTATE"] = val("__VIEWSTATE")
        self.payload["__VIEWSTATEGENERATOR"] = val("__VIEWSTATEGENERATOR")
        self.payload["__EVENTVALIDATION"] = val("__EVENTVALIDATION")
        self.payload["__EVENTTARGET"] = "Grid"
        self.payload["__EVENTARGUMENT"] = f"Page${next_page}"

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")
