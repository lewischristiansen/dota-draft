from dota2api import API, Database, ReplayDownloader

import asyncio
import logging
import signal
import sys
import time
import os
import queue

STATUS_LEVEL = 35


class log_message_count( object ):
    def __init__( self, method ):
        self.method = method
        self.counter = 0

    def __call__( self, *args, **kwargs ):
        self.counter += 1
        return self.method( *args, **kwargs )


def status_log( message, *args, **kwargs ):
    logging.log( STATUS_LEVEL, message, *args, **kwargs )


def init_logging():
    logging.basicConfig( filename = "scraper.log", filemode = "a", format = "%(asctime)s : %(levelname)s : %(message)s", level = logging.WARNING )
    logging.error = log_message_count( logging.error )
    logging.warning = log_message_count( logging.warning )

    logging.addLevelName( STATUS_LEVEL, "STATUS" )
    setattr( logging, "STATUS", STATUS_LEVEL )
    setattr( logging, "status", status_log )


def read_key():
    with open( "key", "r" ) as k:
        key = k.readlines()[0].strip()

    return key


def exit_gracefully( sig, frame ):
    api.close()
    # replay.close()
    loop.stop()

    logging.status( "--- Caught {}, Exiting ---".format( signal.Signals(sig).name ) )
    sys.exit(0)

if __name__ == "__main__":
    init_logging()
    logging.status( "--- Starting API Poller ---" )

    key = read_key()
    loop = asyncio.get_event_loop()

    api = API( key = key )
    # replay_dir = "/data/scripts/dota/draft/data/"
    # replay = ReplayDownloader( replay_dir )

    api_future = loop.run_in_executor( None, api.run )
    # replay_future = loop.run_in_executor( None, replay.run )

    signal.signal( signal.SIGINT, exit_gracefully )
    signal.signal( signal.SIGTERM, exit_gracefully )

    num_matches = 0
    start = time.time()
    with Database( os.path.abspath( "database" ) ) as db:
        while True:
            game = api.get_match()
            if not db.commit_game( game ):
                continue

            logging.info( "Found a valid game, committing match_id {} the database".format( game["match_id"] ) )
            num_matches += 1

            error_count = logging.error.counter
            warning_count = logging.warning.counter

            if num_matches % 100 == 0:
                t_since_start = time.time() - start
                logging.status( "There have been {} errors and {} warnings since start ({} non-messages) at a rate of {}s/{}s or {}/{} per successful request".format( error_count, warning_count, num_matches, round( error_count / t_since_start, 3 ), round( warning_count / t_since_start, 3 ), round( error_count / num_matches, 3 ), round( error_count / num_matches, 3 ) ) )

            # if game["replay"] is not None:
            #    logging.info( "Found a match ({}) with replay data, passing to the downloader!".format( game["match_id"] ) )
            #    replay.add_game( ( game["match_id"], game["replay"] ) )
