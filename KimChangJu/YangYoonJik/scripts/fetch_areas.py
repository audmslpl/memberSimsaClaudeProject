from scripts.seoul_api import SeoulApiClient
SERVICE="TbgisTrdarRelm"
def fetch(client:SeoulApiClient)->list[dict]: return client.fetch_all(SERVICE)
