from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http import HTTPStatus

import deutsche_bahn as bahn
import mongo_fn



def run_new_journeys(dbProfile):
    journeys = []

    for date in dbProfile.dates:
        result = bahn.new_journey(dbProfile, date)
        if result["http_status"] != HTTPStatus.OK:
            raise ConnectionError(f"Status Code: {result['http_status']} is not accepted")

        for data in result.get("data").get("journeys", []):
            journeys.append({"cache_state" : result['cache_state'], "journey" : bahn.data_preprocessing(data, result["time_stamp"])})
    return journeys

def update_journeys(journeys):
    update_journeys = []
    for journey in journeys:
        token = journey["refreshToken"]
        result = bahn.refresh_db_journey(token= token)
        if result["http_status"] != HTTPStatus.OK:
            raise ConnectionError(f"Status Code: {result['http_status']} is not accepted")

        for data in result.get("data").get("journeys", []):
            journeys.append({"cache_state" : result['cache_state'], "journey" : bahn.data_preprocessing(data, result["time_stamp"])})
    return journeys



if __name__ == "__main__":

    mongo_db = mongo_fn.connect_mongo_client()

    # Create test profile
    # TODO: Remove dates & query for all days, until no price is displayed
    bahn_profile = bahn.DbProfile(origin = "Frankfurt", dest="Dresden Neustadt", dates = [datetime(2026, 12, 8, 6, 0, tzinfo=ZoneInfo("Europe/Berlin"))], tickets= False, loyaltyCard= bahn.LoyaltyCards.C2BC25, age=27, results=1, endpoint = 'dbnav')
    # Query ibnr for origin and destination and update dbProfile
    bahn_profile.set_from_id(mongo_fn.ibnr_from_station_name(mongo_db.stations, bahn_profile.origin))
    bahn_profile.set_to_id(mongo_fn.ibnr_from_station_name(mongo_db.stations, bahn_profile.dest))

    mongo_fn.insert_profile(mongo_db.profiles, bahn_profile.finalize())


    for bahn_profile in mongo_db.profiles.find():
        comp_journeys = profile.get("journeys")




    new_journeys = run_new_journeys(bahn_profile)
    mongo_fn.insert_update_journeys(mongo_db.journeys, new_journeys)


    old_journeys = update_journeys(mongo_db["journeys"].find())
    mongo_fn.insert_update_journeys(mongo_db.journeys, old_journeys)
    # Update existing trips that are in future

# Next steps: 
# 2. Wie verhält sich eine Journey die zu weit in der Zukunft ist?
# 3. kleiner Server zum Spielen?