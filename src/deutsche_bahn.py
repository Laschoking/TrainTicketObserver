### Provide handling for the vendo endpoint to query Deutsche Bahn
import datetime as dt
from zoneinfo import ZoneInfo
from enum import Enum
import requests
from http import HTTPStatus
from config import *

## Define a profile for deutsche bahn

BASE_URL = "http://localhost:8080/journeys"#"https://v6.db.transport.rest/journeys"

class LoyaltyCards(str, Enum): 
    NONE = 'None',
    C1BC25 = 'bahncard-1st-25'
    C2BC25 = 'bahncard-2nd-25',
    C1BC50 = 'bahncard-1st-50',
    C2BC50 = 'bahncard-2nd-50',
    C1BC100 = 'bahncard-1st-100'
    C2BC100 = 'bahncard-2nd-100',
    vorteilscard = 'vorteilscard',
    halbtaxabo_railplus = 'halbtaxabo-railplus',
    halbtaxabo = 'halbtaxabo',
    voordeelurenabo_railplus = 'voordeelurenabo-railplus',
    voordeelurenabo = 'voordeelurenabo,' 
    shcard = 'shcard',
    generalabonnemen_1st = 'generalabonnement-1st',
    generalabonnement_2nd = 'generalabonnement-2nd',
    generalabonnement = 'generalabonnement',
    nl_40 = 'nl-40',
    at_klimaticket = 'at-klimaticket'

class DbProfile:
    def __init__(self, origin, destination, origin_id= None, destination_id = None, mongo_id = None, age = "adult", computed_journeys = {}, tickets = True, results = 100, firstClass = False, loyaltyCard = LoyaltyCards.NONE, endpoint = "dbnav"):
        self.origin = origin
        self.origin_id = origin_id
        self.destination = destination
        self.destination_id = destination_id
        self.mongo_id = mongo_id # from MongoDB
        self.age = age
        self.computed_journeys = computed_journeys
        self.tickets = tickets
        self.results = results
        self.firstClass = firstClass
        self.loyaltyCard = loyaltyCard
        self.endpoint  = endpoint
    
    @classmethod
    def from_dict(cls, profile):
        assert profile["_id"] is not None
        return cls( origin = profile["origin"],
                    destination = profile["destination"],
                    origin_id = profile["origin_id"],
                    destination_id = profile["destination_id"],
                    mongo_id = profile["_id"],
                    age = profile["age"],
                    computed_journeys= profile.get("computed_journeys",{}),
                    tickets = profile["tickets"],
                    results= profile["results"],
                    firstClass= profile["firstClass"],
                    loyaltyCard= profile["loyaltyCard"], 
                    endpoint=profile["endpoint"])
    
    def set_origin_id(self, origin_id):
        self.origin_id = origin_id
    
    def set_destination_id(self, destination_id):
            self.destination_id = destination_id



    def finalize_for_db(self) -> dict:
        assert self.origin_id is not None and self.destination_id is not None

        return {
        'origin' : self.origin,
        'destination' : self.destination,
        'origin_id' : self.origin_id,
        'destination_id' : self.destination_id,
        'age' : self.age,
        'computed_journeys' : self.computed_journeys,
        'tickets' : self.tickets,
        'results' : self.results,
        'firstClass' : self.firstClass,
        'loyaltyCard' : self.loyaltyCard,
        'endpoint' : self.endpoint
        }

    def finalize_for_request(self, date: dt.datetime) -> dict:
        assert self.origin_id is not None and self.destination_id is not None

        return {
        'from' : self.origin_id,
        'to' : self.destination_id,
        'departure' : date, 
        'tickets' : self.tickets,
        'results' : self.results,
        'firstClass' : self.firstClass,
        'loyaltyCard' : self.loyaltyCard,
        'age' : self.age,
        'profile' : self.endpoint
        }


    def update_computed_journeys(self, journeys: list):
        """Inscribe refreshToken, and departure time of each journey in the corresponding profile"""
        for journey in journeys:
            if journey is None:
                print(f"journey = None detected: {journeys}")
                continue
            date = dt.datetime.fromisoformat(journey["departure"]).date()
            new_trip = {"departure" : journey["departure"], "arrival" : journey["arrival"] , "refreshToken": journey["refreshToken"]}
            self.computed_journeys.setdefault(date.isoformat(), []).append(new_trip)

def date_to_timestamp(date : dt.datetime) -> dt.datetime:
    return dt.datetime.strptime(date, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=dt.timezone.utc).astimezone(ZoneInfo("Europe/Berlin")).isoformat()


def new_request(params = {}, path = None) -> dict:
    if path :
        print(f"Refreshing journey")
        enc_path = requests.utils.quote(path, safe="")
        url = f"{BASE_URL}/{enc_path}"
    else:
        url = BASE_URL
    req = requests.Request("GET", url, params=params)
    prepared = req.prepare()
    if DEBUG:
        print("\n=== new request: Prepare  ===")
        print(prepared.url)
    

    # Inspect the prepared request
    with requests.Session() as s:
        r = s.send(prepared)
        if DEBUG:
            print("\n=== new request: Response ===")
            print("Status:", r.status_code)
        date = r.headers.get("Date")
    time_stamp =  date_to_timestamp(date)
    cache_state = r.headers.get("X-Cache-Status", "Proxy not active")
    
    if r.status_code != HTTPStatus.OK:
        print(f"Status Code: {r.status_code} is not accepted")
        print(prepared.url)
        return {'http_status' : r.status_code, 'time_stamp' : time_stamp, 'data': None, 'cache_state' : None}
    else:
        return {'http_status' : r.status_code, 'time_stamp' : time_stamp, 'data': r.json(), 'cache_state' : cache_state}



    

def data_preprocessing(journey, time_stamp) -> dict:
    """Prepocess to find relevant information for a journey 
    Parameters:
    data - friendly public transport format

    Current fields:
    token, origin, destination, departure, arrival, (train) line, price 
    """

    # timestamp
    document = {
        "origin" : None,
        "destination": None,
        "departure": None,
        "arrival": None,
        "travelling_time": None,
        "last_updated" : dt.datetime.now(tz=ZoneInfo("Europe/Berlin")).isoformat(),
        "legs": [],
        "refreshToken": journey["refreshToken"],
        }

    # Use first leg for time of departure & origin
    # Use last leg for time of arrival & destination
    if journey["legs"]:
        document["origin"] = journey["legs"][0]["origin"]["name"]
        document["origin_id"] = journey["legs"][0]["origin"]["id"]
        document["destination"] = journey["legs"][-1]["destination"]["name"]
        document["destination_id"] = journey["legs"][0]["destination"]["id"]

        tod = dt.datetime.fromisoformat(journey["legs"][0]["departure"])
        toa = dt.datetime.fromisoformat(journey["legs"][-1]["arrival"])
        assert toa >= tod, "Time of Arrival should be after or equal the departure"
        time_delta = toa - tod
        hours = time_delta.days * 24 + time_delta.seconds//3600
        minutes = (time_delta.seconds//60)%60

        document["departure"] = tod.isoformat()

        document["arrival"] = toa.isoformat()

        document["travelling_time"] = f"{hours:02}h:{minutes:02}m"

    for leg in journey.get("legs", []):
        origin = leg["origin"]["name"]
        destination = leg["destination"]["name"]
        departure = leg["departure"]
        arrival = leg["arrival"]
        train = leg.get("line", {}).get("id") or leg.get("line", {}).get("name", "n/a")

        
        if origin != destination or departure != arrival:
            document["legs"].append(
                {"origin": origin,
                "destination": destination,
                "departure" : departure,
                "arrival" : arrival,
                "line" : train,
                })
            
    # Verify if price is available for this trip
    document["ticket"] = {time_stamp : journey.get("price", {}).get("amount", "n/a")}
    document["currency"] = journey.get("price",{}).get("currency", "n/a")

    # Theoretically we could also log infos on tickets (Sparpreis, Flexpreis etc.) but this is not transmitted correctly by vendo
    #for ticket in journey.get("tickets", {}):
    #    print(ticket)
    #    name = ticket.get("name", "n/a")
    #    if bool(ticket.get("firstClass", False)) == False:
    #        #print(name, time_stamp, ticket.get("priceObj", {}).get("amount", "n/a"))
    #        document["tickets"][name] = {time_stamp: ticket.get("priceObj", {}).get("amount", 9999999999999)/100}

    return document
