import requests

BASE_URL = "http://localhost:3000/journeys"

 
def request_db_journeys(from_id, to_id, date=None):
    """
    Calls Docker API for db-vendo-client 
    from https://github.com/public-transport/db-vendo-client/tree/main
    """
    params = {
        "from": from_id,
        "to": to_id,
    }
    if date:
        params["date"] = date

    r = requests.get(BASE_URL, params=params)
    r.raise_for_status()
    return r.json()

def print_journeys(data):
    journeys = data.get("journeys", [])
    for journey in journeys:
        for leg in journey.get("legs", []):
            origin = leg.get("origin", {}).get("name", "unknown")
            dest = leg.get("destination", {}).get("name", "unknown")
            dep = leg.get("departure", "n/a")
            arr = leg.get("arrival", "n/a")
            train = leg.get("line", {}).get("id") or leg.get("line", {}).get("name", "unknown")
            price_amount = leg.get("price", {}).get("amount", "n/a")
            price_currency = leg.get("price", {}).get("currency", "")

            print(f"{origin} → {dest} | {dep} → {arr} | {train} | {price_amount} {price_currency}")

if __name__ == "__main__":
    # Example: Frankfurt (8000105) → Berlin (8011160)
    data = request_db_journeys("8000105", "8011160")
    print_journeys(data)
