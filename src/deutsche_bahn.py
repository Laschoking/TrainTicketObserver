### Provide handling for the vendo endpoint to query Deutsche Bahn
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from enum import Enum
import requests
from http import HTTPStatus

## Define a profile for deutsche bahn

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
    def __init__(self, origin, dest, dates : [], age = "adult", tickets = True, results = 100, loyaltyCard = LoyaltyCards, endpoint = "dbnav"):
        self.origin = origin
        self.from_id = None
        self.dest = dest
        self.to_id = None
        self.dates = dates
        self.tickets = tickets
        self.results = results
        self.firstClass = False
        self.age = age
        self.loyaltyCard = loyaltyCard
        self.endpoint  = endpoint

    
    def set_from_id(self, from_id):
        self.from_id = from_id
    
    def set_to_id(self, to_id):
            self.to_id = to_id

    def finalize(self, date):
        assert self.from_id is not None and self.to_id is not None

        return {
        'from' : self.from_id,
        'to' : self.to_id,
        'departure' : date,
        'tickets' : self.tickets,
        'results' : self.results,
        'firstClass' : self.firstClass,
        'loyaltyCard' : self.loyaltyCard,
        'age' : self.age,
        'profile' : self.endpoint
        }



BASE_URL = "http://localhost:8080/journeys"#"https://v6.db.transport.rest/journeys"

def date_to_timestamp(date):
    return datetime.strptime(date, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Berlin")).isoformat()


def new_request(params = {}, path = None):
    if path :
        enc_path = requests.utils.quote(path, safe="")
        url = f"{BASE_URL}/{enc_path}"
    else:
        url = BASE_URL
    req = requests.Request("GET", url, params=params)
    prepared = req.prepare()
    print("\n=== new request: Prepare  ===")
    print(prepared.url)
    

    # Inspect the prepared request
    with requests.Session() as s:
        r = s.send(prepared)
        print("\n=== new request: Response ===")
        print("Status:", r.status_code)
        date = r.headers.get("Date")
    time_stamp =  date_to_timestamp(date)
    cache_state = r.headers.get("X-Cache-Status", "Proxy not active")
    
    if r.status_code != HTTPStatus.OK:
        return {'http_status' : r.status_code, 'time_stamp' : time_stamp, 'data': None, 'cache_state' : None}
    else:
        return {'http_status' : r.status_code, 'time_stamp' : time_stamp, 'data': r.json(), 'cache_state' : cache_state}

def new_journey(db_profile, date):
    print(f"Looking up `{db_profile.origin}({db_profile.from_id})` to `{db_profile.dest} ({db_profile.to_id})` at `{date}`")
    return new_request(params=db_profile.finalize(date))

def refresh_db_journey(token):
    return new_request(path=token)
    

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
        "departure_date": None,
        "departure_time": None,
        "arrival_date": None,
        "arrival_time": None,
        "travelling_time": None,
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

        document["departure_date"] = tod.date().isoformat()
        document["departure_time"] = tod.time().replace(microsecond=0).isoformat()

        document["arrival_date"] = toa.date().isoformat()
        document["arrival_time"] = toa.time().replace(microsecond=0).isoformat()

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
