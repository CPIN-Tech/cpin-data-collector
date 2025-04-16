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
import version

from eth_account import Account
from peaq_sdk import Sdk
from peaq_sdk.types import ChainType, CustomDocumentFields, Verification, Service, Signature


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
def update_data(sdk, dcValue, acValue, year, month, day, hour):
    '''Updates data in the data base.'''
    try:
        key = f'cpin-production-{year}-{month}-{day}-{hour}'
        value = f'{{"outputAC": {acValue}, "outputDC": {dcValue}}}'
        result = sdk.storage.add_item(item_type=key, item=value)
        if result.receipt.is_success:
            logging.exception('Storage update success')
            for event in receipt.triggered_events:
                logging.exception(f'* {event.value}')
        else:
            logging.exception('Tx Failed: ', receipt.error_message)

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
    peaq_wss_url = config.config_data['peaq_storage_updater']['peaq_wss_url']
    peaq_evm_url = config.config_data['peaq_storage_updater']['peaq_evm_url']
    admin_address = config.config_data['peaq_storage_updater']['admin_address']
    facility_info_url = config.config_data['peaq_storage_updater']['facility_info_url']
    admin_signature = config.config_data['peaq_storage_updater']['admin_signature']
    private_key = config.config_data['peaq_storage_updater']['private_key']
    did_account = Account.from_key(private_key)
    did_name = 'did:peaq:' + did_account.address + '#cpin'

    sdk = Sdk.create_instance(
        base_url=peaq_evm_url,
        chain_type=ChainType.EVM,
        seed=private_key,
    )

    # Create did if not exists
    try:
        try:
            result = sdk.did.read(name=did_name, wss_base_url=peaq_wss_url)
        except:
            custom_fields = CustomDocumentFields(
                verifications=[
                    Verification(type='EcdsaSecp256k1RecoveryMethod2020')
                ],
                signature=Signature(
                    type='EcdsaSecp256k1RecoveryMethod2020',
                    issuer=admin_address, 
                    hash=admin_signature
                ),
                services=[
                    Service(id='#admin', type='admin', data=admin_address)
                    Service(id='#ipfs', type='facilityInfo', serviceEndpoint=facility_info_url)
                ]
            )
            result = sdk.did.create(name=did_name, custom_document_fields=custom_fields)
            if result.receipt.is_success:
                logging.exception('DID init success')
                for event in receipt.triggered_events:
                    logging.exception(f'* {event.value}')
            else:
                logging.exception('Tx Failed: ', result.message)

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
            update_data(sdk, data[-1]['output_dc'], data[-1]['output_ac'], data[-1]['date'].split('-')[0], data[-1]['date'].split('-')[1], data[-1]['date'].split('-')[2], data[-1]['date'].split('-')[3])
        except Exception:
            logging.exception("Peaq Storage Updater: failed")

        time.sleep(config.config_data['peaq_storage_updater']['interval_s'])

    # Exit
    logging.info("Peaq Storage Updater: Exiting main loop")
    logging.info("Peaq Storage Updater: Shutting down gracefully")


# Main entry point of the application
if __name__ == "__main__":
    main()
