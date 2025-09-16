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
        "travelling_time": None,
        "departure_time": None,
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

        document["departure_date"] = toa.date().isoformat()
        document["departure_time"] = toa.time().replace(microsecond=0).isoformat()
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

def insert_update_db(mongo_db, journey):
    """Insert a journey document in the MongoDB database
    Returns True if write process was successfull."""
    if mongo_db.journeys.find_one({"refreshToken": journey["refreshToken"]}):
        # Use time & price of the journey
        time, price = next(iter(journey["price"].items()))
        mongo_db.journeys.update_one(
            {"refreshToken" : journey["refreshToken"]},
            {"$set": {f"price.{time}": price}}
            )
    else:
        mongo_db.journeys.insert_one(journey)
    return True

def update_journey(refreshToken):
    """Update real-time information for an existing journey"""

    return

def mongo_db_client() -> object():
    """Connect to MongoDB on default host & port"""
    client = MongoClient("mongodb://root:example@localhost:27017/")
    mongo_db = client["deutsche_bahn"]
    mongo_db.journeys.create_index("refreshToken", unique=True)#
    return mongo_db



if __name__ == "__main__":
    # Example: Frankfurt (8000105) → Berlin (8011160)
    mongo_db = mongo_db_client()
    data = request_db_journeys("8000105", "8011160", datetime.now())
    for raw_journey in data.get("journeys", []):
        journey = data_preprocessing(raw_journey)
        assert insert_update_db(mongo_db, journey), "Error in Database Writing"


# TODO: Check the nginx connection bc. without Internet connection is refused
