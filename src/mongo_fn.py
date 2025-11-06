### Connect to MongoDB local server and insert/update/delete documents from it

from pymongo import MongoClient
from rapidfuzz import process, fuzz, utils
from deutsche_bahn import DbProfile

#def create_mongo_client() -> object():
#    ger_mongo.journeys.create_index("refreshToken", unique=True)
#    

def connect_mongo_client() -> object():
    """Connect to MongoDB on default host & port"""
    client = MongoClient("mongodb://root:example@localhost:27017/?authSource=admin")
    dbs = client.list_database_names()
    mongo_db = client["train_project"]
    mongo_db.journeys.create_index("refreshToken", unique=True)
    return mongo_db

def insert_update_journeys(db_journeys, journeys: list):
    """Insert a journey document in the MongoDB database
    Returns True if write process was successfull."""
    for new_journey in journeys:
        # Verify if journey exists already
        old_journey = db_journeys.find_one({"refreshToken": new_journey["refreshToken"]})
        if old_journey:
            # Only update price if updates comes from server and not from proxy
            # The cache_state is identical for all journeys from the same request
            # Thus it is not part of each individual journey, but of the batch

            if new_journey["cache_state"] == 'MISS':
                print(f"Updated journey {new_journey['origin']} -> {new_journey['destination']} with price {new_journey['price']}")
                old_journey["ticket"][new_journey["time_stamp"]] = new_journey["price"]

        else:
            db_journeys.insert_one(new_journey)

def ibnr_from_station_name(db_stations, station_name):

    choices = {doc['IBNR'] : doc['Name'] for doc in db_stations.find({},{'_id': 0, 'Name' : 1, 'IBNR' : 1})}
    best_fit = process.extractOne(station_name, choices, scorer=fuzz.WRatio, processor=utils.default_process)
    ibnr = best_fit[2]
    if ibnr is None:
        raise ValueError(f"`{station_name}` location IBNR `{ibnr}` does not exist")
    return ibnr

def insert_profile(db_profiles, bahn_profile: DbProfile):
    if db_profiles.find_one({"origin_id" : bahn_profile.origin_id, "destination_id" : bahn_profile.destination_id}) is None:
        db_profiles.insert_one(bahn_profile.finalize_for_db())

    return


def update_profile(db_profiles, bahn_profile : DbProfile):
    """Inscribe refreshToken, and departure time of each journey in the corresponding profile and push changes to MongoDb"""
    db_profiles.update_one({"_id" : bahn_profile.mongo_id}, {"$set" : {"computed_journeys" : bahn_profile.computed_journeys}})