from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import deutsche_bahn_journeys as bahn
from db_profile import *
import MongoDB as mongo
from http import HTTPStatus




if __name__ == "__main__":

    mongo_ger, mongo_sta = mongo.mongo_client()
    

    # For testing
    db_profile = DB_Profile(origin = "Frankfurt", dest= "Dresden Neustadt", dates = [datetime(2025, 10, 24, 6, 0, tzinfo=ZoneInfo("Europe/Berlin"))], tickets= True, loyaltyCard= LoyaltyCards.C2BC25, age=27, db_profile = 'dbnav')
    
    
    # Query ibnr for origin and destination and update db_profile
    db_profile.set_from_id(mongo.ibnr_from_name(mongo_sta, db_profile.origin))
    db_profile.set_to_id(mongo.ibnr_from_name(mongo_sta, db_profile.dest))

    #for i in range(15): 
    #dated += timedelta(days=1)
    
    for date in db_profile.dates:
        status, data = bahn.request_db_journeys(db_profile, date)
        if status != HTTPStatus.OK:
            print(f"Status Code: {status}")
            continue
            #raise ConnectionError(f"Status Code: {status}")

        for raw_journey in data.get("journeys", []):
            journey = bahn.data_preprocessing(raw_journey)
            assert mongo.insert_update_db(mongo_ger, journey), "Error in Database Writing"


# Next steps: 
# 1. Benutzen des Update-Tokens um Journey zu aktualisieren
# 2. Wie verhält sich eine Journey die zu weit in der Zukunft ist?
# 3. kleiner Server zum Spielen?