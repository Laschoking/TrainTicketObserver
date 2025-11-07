import datetime as dt
#from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
from http import HTTPStatus
from collections import deque

import deutsche_bahn as bahn
import mongo_fn
from config import *


def new_trips(bahn_profile: bahn.DbProfile, date : dt.datetime) -> dict:
    """Request new trips from Vendo-API
    Parameters: bahn-profile - contains relevant information about the passenger
                date - date and time for this trip
    """
    parameters = bahn_profile.finalize_for_request(date)
    results = bahn.new_request(params=parameters)
    journeys = []
    if results["http_status"] == HTTPStatus.OK:
        for data in results.get("data").get("journeys", []):
            journey = bahn.data_preprocessing(journey=data, time_stamp=results["time_stamp"])
            journey.update({"cache_state" : results['cache_state']})
            journeys.append(journey)
    return journeys



def update_trip(bahn_profile : bahn.DbProfile, refreshToken : str) -> dict:
    """Request a price update from Vendo-API 
    Parameters: refreshToken - a unique ID of an already computed journey"""
    result = bahn.new_request(path=refreshToken, params=bahn_profile.finalize_for_request(date=None).pop("departure"))
    if result["http_status"] == HTTPStatus.OK:
        data = result.get("data").get("journey")
        journey = bahn.data_preprocessing(journey=data, time_stamp=result["time_stamp"])
        journey.update({"cache_state" : result['cache_state']})
        return journey
    else:
        return None


if __name__ == "__main__":

    mongo_db = mongo_fn.connect_mongo_client()

    # TODO: Remove dates & query for all days, until no price is displayed

    # Create test profile and insert it into MongoDB
    bahn_profile = bahn.DbProfile(origin = "Paris Est", destination="Dresden Neustadt", tickets= True, loyaltyCard= bahn.LoyaltyCards.C2BC25, age=27, firstClass=False, results=1, endpoint = 'dbnav')
    bahn_profile.set_origin_id(mongo_fn.ibnr_from_station_name(mongo_db.stations, bahn_profile.origin))
    bahn_profile.set_destination_id(mongo_fn.ibnr_from_station_name(mongo_db.stations, bahn_profile.destination))
    mongo_fn.insert_profile(mongo_db.profiles, bahn_profile)

    # Maybe requests should be asynchronous? or we just block 5 seconds after each request
    request_counter = 0
    update_wl = deque()
    new_wl = deque()



    for bahn_dict in mongo_db.profiles.find():

        profile = bahn.DbProfile.from_dict(bahn_dict)
        
        # Add existing journeys to worklist that can be updated
        computed_journeys = profile.computed_journeys
        for trips in computed_journeys.values():
            for journey in trips:
                datetime = dt.datetime.fromisoformat(journey["departure"])
                now = datetime.now(tz=ZoneInfo("Europe/Berlin"))
                if now < datetime:
                    last_updated = mongo_db.journeys.find_one({"refreshToken" : journey["refreshToken"]},{"last_updated": True, "_id": False})
                    # Verify that journey was not updated recently
                    if now - datetime.fromisoformat(last_updated["last_updated"]) > UPDATE_TIME_DELTA :
                        if DEBUG: 
                            print(f"Add journey to update {journey['refreshToken']}")
                        update_wl.append((profile,journey["departure"], journey["refreshToken"]))

        # Add new trip requests to worklist
        tomorrow = dt.date(year=2025, month=11, day=8)
        dates = [tomorrow + dt.timedelta(days=day) for day in range(2)]
        for date in dates:
            if date.isoformat() not in computed_journeys:
                if DEBUG:
                    print(f"Search new journey {profile.origin} to {profile.destination}")
                new_wl.append((profile, dt.datetime.combine(date, time= dt.time(hour=6, minute=0), tzinfo=ZoneInfo("Europe/Berlin"))))



    # Process one trip request for a certain origin, destination and date at a time
    while new_wl:
        request_counter += 1
        bahn_profile, date = new_wl.pop()

        # Finds & parses new trips
        new_journeys = new_trips(bahn_profile = bahn_profile, date = date)

        # Inscribe new trips in profile
        bahn_profile.update_computed_journeys(new_journeys)

        mongo_fn.update_profile(db_profiles=mongo_db.profiles, bahn_profile=bahn_profile)
        mongo_fn.insert_update_journeys(mongo_db.journeys, new_journeys)
    
    print(f"Made {request_counter} new trip requests to Vendo API")
    request_counter = 0

    # Update an existing journey based on its refreshToken
    while update_wl:
        request_counter += 1
        profile, departure, refreshToken = update_wl.pop()
        old_journey = update_trip(bahn_profile=profile, refreshToken=refreshToken) 
        mongo_fn.insert_update_journeys(mongo_db.journeys, [old_journey])

    print(f"Made {request_counter} update requests to Vendo API")

# Next steps: 
# 2. Wie verhält sich eine Journey die zu weit in der Zukunft ist?
# 3. kleiner Server zum Spielen?