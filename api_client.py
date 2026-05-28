import io
import json
import time
import requests
import pandas as pd

from config import BASE_URL, LOGIN_URL, USERNAME, PASSWORD, ENDPOINTS


class AdtendeClient:
    def __init__(self):
        self.token = None
        self.session = requests.Session()

    def login(self, username=None, password=None):
        username = username or USERNAME
        password = password or PASSWORD
        if not username or not password:
            raise ValueError("Credenciales no configuradas. Revisa el archivo .env")

        resp = self.session.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": password}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        self.token = resp.json()["key"]
        return self.token

    def _headers(self):
        if not self.token:
            raise RuntimeError("No autenticado. Llama a login() primero.")
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Token {self.token}",
        }

    def query(self, endpoint_name, variables=None, filters=None, group_bys=None, aggregations=None):
        """
        Consulta un endpoint y devuelve un DataFrame.

        Args:
            endpoint_name: clave de ENDPOINTS o UUID directamente
            variables: lista de {"name": "campo"} — vacío = todas las columnas
            filters: lista de filtros (ver documentación)
            group_bys: lista de {"variable": ..., "transformations": []}
            aggregations: lista de {"variable": ..., "operation": ..., "transformations": []}
        """
        uuid = ENDPOINTS.get(endpoint_name, endpoint_name)
        url = f"{BASE_URL}/data-service/{uuid}/?format=csv"

        query_body = {
            "variables": variables or [],
            "filters": filters or [],
        }
        if group_bys:
            query_body["groupBys"] = group_bys
        if aggregations:
            query_body["aggregations"] = aggregations

        body = {"queries": [query_body]}
        for attempt in range(4):
            resp = self.session.post(
                url,
                headers=self._headers(),
                data=json.dumps(body).encode("utf-8"),
            )
            if resp.status_code in (502, 503, 504) and attempt < 3:
                wait = 8 * (attempt + 1)
                print(f"      ↻ API {resp.status_code} — reintent {attempt+1}/3 en {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        df = pd.read_csv(io.StringIO(resp.text), sep="\x1e")
        # La API retorna columnes amb prefix "anon_1_" — el treiem
        df.columns = [c.split("anon_1_", 1)[-1] if "anon_1_" in c else c for c in df.columns]
        # \x1f (ASCII 31) s'usa com a valor nul — el convertim a NaN
        df = df.replace("\x1f", pd.NA)
        # Convertim columnes numèriques que hagin quedat com object
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    converted = pd.to_numeric(df[col], errors="raise")
                    df[col] = converted
                except (ValueError, TypeError):
                    pass
        return df

    # Records above this threshold trigger a confirmation prompt before downloading
    SAFE_RECORD_LIMIT = 50_000

    def count_records(self, endpoint_name, filters=None):
        """Returns the approximate record count for a set of filters without downloading all data."""
        uuid = ENDPOINTS.get(endpoint_name, endpoint_name)
        url = f"{BASE_URL}/data-service/{uuid}/?format=csv"
        body = {"queries": [{
            "variables": [],
            "filters": filters or [],
            "aggregations": [{"variable": "des_status", "operation": "count", "transformations": []}],
        }]}
        resp = self.session.post(url, headers=self._headers(), data=json.dumps(body).encode("utf-8"))
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), sep="\x1e")
        if df.empty:
            return 0
        return int(df.iloc[0, 0])

    def _check_size(self, endpoint_name, filters, label):
        """Warns and asks confirmation if estimated record count exceeds SAFE_RECORD_LIMIT."""
        try:
            count = self.count_records(endpoint_name, filters)
        except Exception:
            return  # si falla el count, continuem igualment
        if count > self.SAFE_RECORD_LIMIT:
            print(f"\n⚠️  AVÍS: La consulta '{label}' retornaria ~{count:,} registres "
                  f"(límit recomanat: {self.SAFE_RECORD_LIMIT:,}).")
            resp = input("   Vols continuar igualment? [s/N] ").strip().lower()
            if resp not in ("s", "si", "sí", "y", "yes"):
                raise RuntimeError(f"Consulta cancel·lada per l'usuari ({count:,} registres).")

    def query_month(self, endpoint_name, year, month, date_field="td_created", project=None, **kwargs):
        """Filtra per mes. date_field: td_created o td_managed."""
        if month == 12:
            date_to = f"{year + 1}-01-01"
        else:
            date_to = f"{year}-{month + 1:02d}-01"
        date_from = f"{year}-{month:02d}-01"

        filters = [{"type": "date", "variable": date_field, "values": {"gte": date_from, "lt": date_to}}]
        filters += kwargs.pop("filters", [])
        self._check_size(endpoint_name, filters, f"{endpoint_name} {year}-{month:02d}")
        df = self.query(endpoint_name, filters=filters, **kwargs)
        if project and "des_project" in df.columns:
            df = df[df["des_project"] == project].reset_index(drop=True)
        return df

    def query_date(self, endpoint_name, year, month, day, date_field="td_created", project=None, **kwargs):
        """Filtra per un dia concret. date_field: td_created o td_managed."""
        from datetime import date, timedelta
        d = date(year, month, day)
        d_next = d + timedelta(days=1)

        filters = [{"type": "date", "variable": date_field, "values": {"gte": str(d), "lt": str(d_next)}}]
        filters += kwargs.pop("filters", [])
        self._check_size(endpoint_name, filters, f"{endpoint_name} {d}")
        df = self.query(endpoint_name, filters=filters, **kwargs)
        if project and "des_project" in df.columns:
            df = df[df["des_project"] == project].reset_index(drop=True)
        return df
