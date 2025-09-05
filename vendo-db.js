import { createClient } from 'db-vendo-client';
import { profile as dbnavProfile } from 'db-vendo-client/p/dbnav/index.js';
import NodeCache from 'node-cache';
import {inspect} from 'util'


const client = createClient(
  dbnavProfile,            // choose the profile (DB Navigator)
  'trash.mail94@gmx.net'     // user agent
);
const cache = new NodeCache({ stdTTL: 300 }); // cache entries for 5 minutes

async function getJourney() {
  const key = `journey-8000105-8011160-${new Date().toISOString().slice(0,10)}`;

  // Check cache first
  const cached = cache.get(key);
  if (cached) {
    console.log('Serving from cache 🚀');
    return cached;
  }

  try {
    const journeys = await client.journeys('8000105', '8011160',{results: 1,
      stopovers: true});

    console.log(inspect(journeys, { depth: null, colors: true }));
    console.dir(journeys[0].leg);
    console.log(journeys[0].price.amount);
  } catch (err) {
    console.error('Error fetching journeys:', err);
  }
}

getJourney();
