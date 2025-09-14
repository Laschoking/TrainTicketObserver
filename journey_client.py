import requests
from datetime import datetime
from pymongo import MongoClient
from datetime import datetime

BASE_URL = "http://localhost:8080/journeys"
 
def request_db_journeys(from_id: int, to_id: int, date: datetime) -> None:
    """
    Calls Docker API for db-vendo-client 
    from https://github.com/public-transport/db-vendo-client/tree/main
    """
    params = {
        # TODO: Add more optional params (bahncard ...)
        "from": from_id,
        "to": to_id,
        #"date": date                          
    }

    r = requests.get(BASE_URL, params=params)
    r.raise_for_status()
    return r.json()

def filter_journey(journey) -> dict:
    """Finds relevant information for a journey 
    Parameters:
    data - friendly public transport format

    Current fields:
    refreshToken, origin, destination, departure, arrival, (train) line, price 
    """

    # Do some preprocessing and validation

    document = {
        "origin" : None,
        "destination": None,
        "departure_date": None,
        "travelling_time": None,
        "departure_time": None,
        "price": journey["price"]["amount"],
        "currency" : journey["price"]["currency"],
        "legs": [],
        "refreshToken": journey["refreshToken"],
        }

    # Use first leg for time of departure & origin

    # Use last leg for time of arrival & destination
    if journey["legs"]:
        document["origin"] = journey["legs"][0]["origin"]["name"]
        document["destination"] = journey["legs"][-1]["destination"]["name"]

        tod = datetime.fromisoformat(journey["legs"][0]["departure"])
        toa = datetime.fromisoformat(journey["legs"][-1]["arrival"])
        assert toa >= tod, "Time of Arrival should be after or equal the departure"
        time_delta = toa - tod
        hours = time_delta.days * 24 + time_delta.seconds//3600
        minutes = (time_delta.seconds//60)%60

        document["departure_date"] = toa.date().isoformat()
        document["departure_time"] = toa.time().isoformat()
        document["travelling_time"] = f"{hours:02}h:{minutes:02}m"
        
        document["toa"] = tod
        document["tod"] = tod

    for leg in journey.get("legs", []):
        origin = leg.get("origin", {}).get("name", "unknown")
        destination = leg.get("destination", {}).get("name", "unknown")
        departure = leg.get("departure", "n/a")
        arrival = leg.get("arrival", "n/a")
        train = leg.get("line", {}).get("id") or leg.get("line", {}).get("name", "unknown")
        price_amount = leg.get("price", {}).get("amount", "n/a")
        price_currency = leg.get("price", {}).get("currency", "")
        
        if origin != destination or departure != arrival:
            document["legs"].append(
                {"origin": origin,
                "destination": destination,
                "departure" : departure,
                "arrival" : arrival,
                "line" : train,})
    return document

def update_journey(refreshToken):
    """Update real-time information for an existing journey"""

    return

def mongo_db_client() -> object():
    """Connect to MongoDB on default host & port"""
    client = MongoClient("mongodb://root:example@localhost:27017/")
    mongo_db = client["foo"]
    return mongo_db



if __name__ == "__main__":
    # Example: Frankfurt (8000105) → Berlin (8011160)
    mongo_db = mongo_db_client()
    data = request_db_journeys("8000105", "8011160", datetime.now())
    for journey in data.get("journeys", []):
        print("new journey")
        filtered_journey = filter_journey(journey)
        print(filtered_journey)
        mongo_db.journeys.insert_one(filtered_journey)


