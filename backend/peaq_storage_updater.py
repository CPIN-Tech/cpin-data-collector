import os
import time
import logging
import importlib
import signal
from os.path import exists
from datetime import date, datetime

# Project imports
from config import Config
from database import Database
from did_document import create_did_doc
import version
from substrateinterface import SubstrateInterface, Keypair, KeypairType


# Real time (24h) data
NUM_REAL_TIME_VALUES = 24*60  # 24h * 60 Minutes
real_time_seconds_counter = 0
config = None
run = True


# Returns JSON response containing history details
def get_json_data_history_details(table, date_search_string):
    '''Returns JSON response containing history details.'''
    db = Database("data/db.sqlite")
    if len(date_search_string) > 0:
        rows = db.execute(
            f"SELECT * FROM {table} WHERE date LIKE '{date_search_string}%'")
    else:
        rows = db.execute(
            f"SELECT * FROM {table}")
    # Build results
    data = []
    for row in rows:
        produced = row[2] - row[1]
        consumed = row[4] - row[3]
        fed_in = row[6] - row[5]
        data.append({
            "date": row[0],
            "output_ac": fed_in,
            "output_dc": produced,
        })
    return json.dumps(data)


# Sets the time zone environment variable
def set_time_zone(tz):
    '''Sets the time zone environment variable.'''
    if tz is None:
        logging.warn("Peaq Storage Updater: Warning: No time zone set")
    else:
        logging.info(f"Peaq Storage Updater: Setting tme zone to {tz}")
        os.environ['TZ'] = tz
        time.tzset()
        logging.info(f"Peaq Storage Updater: Time is now {time.strftime('%X %x %Z')}")


# Updates data in the data base
def update_data(dcValue, acValue, year, month, day, hour):
    '''Updates data in the data base.'''
    try:
        nonce = substrate.get_account_nonce(keypair.ss58_address)
        logging.info(f"Peaq Storage Updater: Read Peaq and create DID ")
        call = substrate.compose_call(
        call_module='PeaqStorage',
        call_function='add_item',
        call_params={
            'item_type': f'cpin-production-{year}-{month}-{day}-{hour}',
            'item': f'{{"outputAC": {acValue}, "outputDC": {dcValue}}}'
            }
        )
        extrinsic = substrate.create_signed_extrinsic(
            call=call, 
            keypair=keypair,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        if receipt.is_success:
            logging.exception('Storage update success')
            for event in receipt.triggered_events:
                logging.exception(f'* {event.value}')
        else:
            logging.exception('Extrinsic Failed: ', receipt.error_message)

    except Exception:
        logging.exception("Storage update failed")
        exit()


# This is called when SIGTERM is received
def handler_stop_signals(signum, frame):
    global run
    logging.debug("Peaq Storage Updater: SIGTERM/SIGINT received")
    run = False


# Main loop
def main():
    '''Main loop.'''
    global config
    global run

    # Set up signal handlers
    signal.signal(signal.SIGINT, handler_stop_signals)
    signal.signal(signal.SIGTERM, handler_stop_signals)

    # Set up logging
    logging.basicConfig(
        filename='data/peaq_storage_updater.log', filemode='w',
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    # Print version
    logging.info(f"Starting Cpin Data Collector version {version.get_version()}")

    # Read the configuration from disk
    try:
        logging.info("Peaq Storage Updater: Reading backend configuration from config.yml")
        config = Config("data/config.yml")
    except Exception:
        exit()

    # Set log level
    logging.getLogger().setLevel(config.log_level)

    # Set time zone
    set_time_zone(config.config_data.get("time_zone"))

    # Connect to the peaq network
    peaq_network_url = config.config_data['peaq_storage_updater']['peaq_network_url']
    substrate = SubstrateInterface(
            url=peaq_network_url,
        )

    mnemonic = config.config_data['peaq_storage_updater']['mnemonic']
    keypair = Keypair.create_from_mnemonic(
        mnemonic,
        ss58_format=42,
        crypto_type=KeypairType.SR25519)

    # Dynamically load the device
    try:
        nonce = substrate.get_account_nonce(keypair.ss58_address)
        logging.info(f"Peaq Storage Updater: Read Peaq and create DID ")
        call = substrate.compose_call(
        call_module='PeaqDid',
        call_function='add_attribute',
        call_params={
            'did_account': keypair.ss58_address,
            'name': 'cpin-spp-facility',
            'value': create_did_doc(keypair.ss58_address),
            'valid_for': None
            }
        )
        extrinsic = substrate.create_signed_extrinsic(
            call=call, 
            keypair=keypair,
            era={'period': 64},
            nonce=nonce
        )

        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

        if receipt.is_success:
            logging.exception('DID init success')
            for event in receipt.triggered_events:
                logging.exception(f'* {event.value}')
        else:
            logging.exception('Extrinsic Failed: ', receipt.error_message)

    except Exception:
        logging.exception("DID init failed")
        exit()

    # Prepare the data base
    logging.info("Peaq Storage Updater: Checking if data base exists")
    if not exists("data/db.sqlite"):
        logging.exception("Peaq Storage Updater: Data base does not exist.")
        exit()

    # Peaq Storage Updater main loop
    logging.debug("Peaq Storage Updater: Entering main loop")
    while run:
        if logging.getLogger().level == logging.DEBUG:
            time_string = datetime.now().strftime("%H:%M")
            logging.debug(f"Peaq Storage Updater: {time_string}: Updating device data")

        try:
            data = get_json_data_history_details("hours", "")
            update_data(data[-1]['output_dc'], data[-1]['output_ac'], data[-1]['date'].split('-')[0], data[-1]['date'].split('-')[1], data[-1]['date'].split('-')[2], data[-1]['date'].split('-')[3])
        except Exception:
            logging.exception("Peaq Storage Updater: failed")

        time.sleep(config.config_data['peaq_storage_updater']['interval_s'])

    # Exit
    logging.info("Peaq Storage Updater: Exiting main loop")
    logging.info("Peaq Storage Updater: Shutting down gracefully")


# Main entry point of the application
if __name__ == "__main__":
    main()
