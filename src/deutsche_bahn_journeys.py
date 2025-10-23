### Provide handling for the vendo endpoint to query Deutsche Bahn
from datetime import datetime
import requests
from http import HTTPStatus

BASE_URL = "http://localhost:8080/journeys"#"https://v6.db.transport.rest/journeys"


def request_db_journeys(db_profile, date):
    print(f"Looking up `{db_profile.origin}({db_profile.from_id})` to `{db_profile.dest} ({db_profile.to_id})` at `{date}`")

    req = requests.Request("GET", BASE_URL, params=db_profile.finalize(date))
    prepared = req.prepare()

    # Inspect the prepared request
    print("=== Prepared Request ===")
    print("Method:", prepared.method)
    print("URL:", prepared.url)
    print("Headers:", prepared.headers)

    with requests.Session() as s:
        r = s.send(prepared)
        print("\n=== Response ===")
        print("Status:", r.status_code)
    
    if r.status_code != HTTPStatus.OK:
        return r.status_code, None

    # only works if nginx proxy is enabled
    print("Cache state: " + r.headers.get("X-Cache-Status"))
    r.raise_for_status()
    return r.status_code, r.json()


def data_preprocessing(raw_journey) -> dict:
    """Prepocess to find relevant information for a journey 
    Parameters:
    data - friendly public transport format

    Current fields:
    refreshToken, origin, destination, departure, arrival, (train) line, price 
    """

    document = {
        "origin" : None,
        "destination": None,
        "departure_date": None,
        "departure_time": None,
        "arrival_date": None,
        "arrival_time": None,
        "travelling_time": None,
        "price": {str(datetime.now().replace(microsecond=0).isoformat()): raw_journey.get("price", {}).get("amount", "n/a")},
        "currency" : raw_journey.get("price", {}).get("currency", "n/a"),
        "legs": [],
        "refreshToken": raw_journey["refreshToken"],
        }

    # Use first leg for time of departure & origin
    # Use last leg for time of arrival & destination
    if raw_journey["legs"]:
        document["origin"] = raw_journey["legs"][0]["origin"]["name"]
        document["destination"] = raw_journey["legs"][-1]["destination"]["name"]

        tod = datetime.fromisoformat(raw_journey["legs"][0]["departure"])
        toa = datetime.fromisoformat(raw_journey["legs"][-1]["arrival"])
        assert toa >= tod, "Time of Arrival should be after or equal the departure"
        time_delta = toa - tod
        hours = time_delta.days * 24 + time_delta.seconds//3600
        minutes = (time_delta.seconds//60)%60

        document["departure_date"] = tod.date().isoformat()
        document["departure_time"] = tod.time().replace(microsecond=0).isoformat()

        document["arrival_date"] = toa.date().isoformat()
        document["arrival_time"] = toa.time().replace(microsecond=0).isoformat()

        document["travelling_time"] = f"{hours:02}h:{minutes:02}m"
        
        document["toa"] = tod
        document["tod"] = tod

    for leg in raw_journey.get("legs", []):
        origin = leg["origin"]["name"]
        destination = leg["destination"]["name"]
        departure = leg["departure"]
        arrival = leg["arrival"]
        train = leg.get("line", {}).get("id") or leg.get("line", {}).get("name", "n/a")
        #price_amount = leg.get("price", {}).get("amount", "n/a")
        #price_currency = leg.get("price", {}).get("currency", "n/a")
        
        if origin != destination or departure != arrival:
            document["legs"].append(
                {"origin": origin,
                "destination": destination,
                "departure" : departure,
                "arrival" : arrival,
                "line" : train,})
    return document
