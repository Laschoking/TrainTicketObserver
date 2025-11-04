# Train price Tracker

- Objective: specify Start & Target location
- then automatically find all connection btw. this destinations for all? days
- once per day: Update price of connections

## Instructions

- run `sudo docker compose up -d` to init docker file `-d` to keep it running if terminal is closed
- initalise python venv `source /home/kotname/Documents/fun_code/venv/bin/activate`
- find journeys under `localhost:270017`

if stations are not in MongoDB anymore:

```bash
mongoimport --type csv --file data/German_French_Trainstations.csv --uri "mongodb://root:example@localhost:27017/train_project?authSource=admin" --fields ID,Name,IBNR --db train_project   --collection stations
```

- to find the Train ID of your trainstation:
