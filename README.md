# CPIN Data Collector

CPIN Data Collector is a free, open source and vendor independent solar monitoring system. It collects relevant data from your inverter/smart meter and stores them safely in its local database and 
sends the data to the Peaq blockchain by using the Peaq DID.

When you configure you should enter the inverter connection information and a mnemonic for the Peaq DID. Data will be sent to Peaq storage system by using the Peaq DID.

CPIN Data Collector has a UI too for monitoring.

CPIN Data Collector can easily be self hosted on a Raspberry Pi or a NAS by using Docker.

![Screenshot](doc/screenshot.png)

## Main Features

- Easy to set up and configure (e.g. on a Raspberry Pi or a NAS).
- Data is stored in the local database and sent to the Peaq blockchain.
- Hardware vendor independent.
- It has a UI for monitoring.
- Detailled information and statistics with lots of useful information.

## Supported Devices

CPIN Data Collector provides integrations for the following device types (inverters/smart meters):
* Fronius (Symo/Gen24)
* Generic Modbus Protocol (inverters that support modbus protocol)

Contributions for the support of additional devices are welcome. Please feel free to reach out to me or submit a pull request directly.


## Installation instructions

CPIN Data Collector comes as a self contained and easy to set up Docker container. Thus it can be run on various different platforms.

### General Instructions

1. Create a peaq wallet and get a mnemonic. Fund the wallet with some PEAQ tokens.
2. Create a configuration YAML file in this data folder. Use [this template](templates/config.yml)] as a starting point. A detailled description of the configuration elements can be found below.
3. Create a folder called *data* on your host system. This will contain the configuration file and the data base.
4. Create a container based on this image.
  * The container exposes port 5000. Map this to a port on your host system.
  * The container exposes a volume called *data*. Map this to the *data* folder on your host system created in step 1.
5. Make sure your data folder is regularily backed up as it contains the data base!
6. Start the container. Done!

### Using Docker Compose

If you are using Docker Compose, create and run a *docker-compose.yml* file like this:

```yaml
services:
  cpin-data-collector:
    container_name: cpin-data-collector
    image: cpin-tech/cpin-data-collector:latest
    restart: always
    ports:
      - "8020:5000"
    volumes:
      - /volume1/docker/cpin-data-collector/data:/data
```

## Configuration

CPIN Data Collector is configured via a YAML file called *config.yml*. This file has to be placed in the data folder before the container is started. An example configuration file can be found [here](templates/config.yml)].

### Configuration Settings Overview

| Setting                       | Description                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------- |
| logging                       | Can be 'normal' (only basic logging) or 'verbose' (verbose logging for debug purposes).             |
| time_zone                     | The time zone that will be used to generate time stamps for logged data. E.g. "Europe/Berlin".      |
| device:type                   | Name of the device plugin to use. Currently "Fronius" and "Dummy" are supported.                    |
| device:start_date             | The date on which the inverter first started production (YYYY-MM-DD).                               |
| prices:price_per_grid_kwh     | Price for 1 kWh consumed from the grid (e.g. in €).                                                 |
| prices:revenue_per_fed_in_kwh | Revenue for 1 fed in kWh (e.g. in €).                                                               |
| server:ip                     | IP address of the web server. Should be set to 0.0.0.0.                                             |
| server:port                   | Port of the web server. Should be set to 5000.                                                      |
| grabber:interval_s            | Interval in seconds that the grabber will use to query the inverter/smart meter. Default is 3s.     |

Additional settings are required depending on the selected device plugin:

#### Fronius

| Setting                       | Description                                                   |
| ----------------------------- | ------------------------------------------------------------- |
| fronius::host_name            | IP address or host name of your fronius inverter.             |
| fronius::has_meter            | True/False - Is there a Fronius smart meter present?          |

#### Modbus

| Setting                       | Description                                                   |
| ----------------------------- | ------------------------------------------------------------- |
| modbus::connection_type       | 'tcp' or 'rtu'                                                |
| modbus::host                  | IP address or host name of your modbus inverter.              |
| modbus::port                  | Port of the modbus inverter.                                  |
| modbus::port_name             | Port name of the modbus inverter.                             |
| modbus::baudrate              | Baud rate of the modbus inverter.                             |
| modbus::parity                | Parity of the modbus inverter.                                |
| modbus::stopbits              | Stop bits of the modbus inverter.                             |
| modbus::bytesize              | Byte size of the modbus inverter.                             |
| modbus::unit_id               | Unit ID of the modbus inverter.                               |
| modbus::timeout               | Timeout of the modbus inverter.                               |
| modbus::word_order            | Word order of the modbus inverter.                            |
| modbus::byte_order            | Byte order of the modbus inverter.                            |
| modbus::register_map          | Register map of the modbus inverter.                          |


