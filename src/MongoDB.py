### Connect to MongoDB local server and insert/update/delete documents from it

from pymongo import MongoClient
from rapidfuzz import process, fuzz, utils


def mongo_client() -> object():
    """Connect to MongoDB on default host & port"""
    client = MongoClient("mongodb://root:example@localhost:27017/?authSource=admin")
    dbs = client.list_database_names()
    print("Connect to MongoDb containing this databases:", dbs)
    ger_mongo = client["deutsche_bahn"]
    ger_mongo.journeys.create_index("refreshToken", unique=True)
    sta_mongo = client["transport"]
    return ger_mongo, sta_mongo

def insert_update_db(mongo, journey):
    """Insert a journey document in the MongoDB database
    Returns True if write process was successfull."""
    if mongo.journeys.find_one({"refreshToken": journey["refreshToken"]}):
        # Use time & price of the journey
        time, price = next(iter(journey["price"].items()))
        mongo.journeys.update_one(
            {"refreshToken" : journey["refreshToken"]},
            {"$set": {f"price.{time}": price}}
            )
    else:
        mongo.journeys.insert_one(journey)
    return True

def update_journey(refreshToken):
    """Update real-time information for an existing journey"""

    return
def ibnr_from_name(db, station_name):
    choices = {doc['IBNR'] : doc['Name'] for doc in db.stations.find({},{'_id': 0, 'Name' : 1, 'IBNR' : 1})}
    best_fit = process.extractOne(station_name, choices, scorer=fuzz.WRatio, processor=utils.default_process)
    ibnr = best_fit[2]
    if ibnr is None:
        raise ValueError(f"`{station_name}` location IBNR `{ibnr}` does not exist")
    return ibnr