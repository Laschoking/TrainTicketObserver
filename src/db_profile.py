## Define a profile for deutsche bahn
from enum import Enum

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

class DB_Profile:
    def __init__(self, origin, dest, dates : [], age : "adult", tickets : False, loyaltyCard : LoyaltyCards, db_profile: "dbnav"):
        self.origin = origin
        self.from_id = None
        self.dest = dest
        self.to_id = None
        self.dates = dates
        self.tickets = tickets
        self.age = age
        self.loyaltyCard = loyaltyCard
        self.db_profile  = db_profile
    
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
        'loyaltyCard' : self.loyaltyCard,
        'age' : self.age,
        'profile' : self.db_profile
        }