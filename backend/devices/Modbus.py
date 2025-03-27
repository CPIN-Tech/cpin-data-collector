import logging
import time
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder


class Modbus:
    def __init__(self, config):
        # Get configuration from config file
        modbus_config = config.config_data['modbus']
        self.connection_type = modbus_config.get('connection_type', 'tcp')  # 'tcp' or 'rtu'
        
        # TCP connection parameters
        self.host = modbus_config.get('host', '192.168.1.100')
        self.port = modbus_config.get('port', 502)
        
        # RTU connection parameters
        self.port_name = modbus_config.get('port_name', '/dev/ttyUSB0')
        self.baudrate = modbus_config.get('baudrate', 9600)
        self.parity = modbus_config.get('parity', 'N')
        self.stopbits = modbus_config.get('stopbits', 1)
        self.bytesize = modbus_config.get('bytesize', 8)
        
        # Common Modbus parameters
        self.unit_id = modbus_config.get('unit_id', 1)
        self.timeout = modbus_config.get('timeout', 3)
        
        # Register mapping - these will vary by inverter model
        self.register_map = modbus_config.get('register_map', {
            'total_energy_produced': {'address': 3000, 'length': 2, 'type': 'uint32', 'scale': 0.001},
            'total_energy_consumed': {'address': 3004, 'length': 2, 'type': 'uint32', 'scale': 0.001},
            'total_energy_fed_in': {'address': 3008, 'length': 2, 'type': 'uint32', 'scale': 0.001},
            'current_power_produced': {'address': 3012, 'length': 1, 'type': 'uint16', 'scale': 0.001},
            'current_power_consumed_grid': {'address': 3014, 'length': 1, 'type': 'int16', 'scale': 0.001},
            'current_power_fed_in': {'address': 3016, 'length': 1, 'type': 'uint16', 'scale': 0.001},
        })
        
        # Endianness configuration
        self.word_order = modbus_config.get('word_order', 'big')
        self.byte_order = modbus_config.get('byte_order', 'big')
        
        # Initialize data values
        self.total_energy_produced_kwh = 0.0
        self.total_energy_consumed_kwh = 0.0
        self.total_energy_fed_in_kwh = 0.0
        self.current_power_produced_kw = 0.0
        self.current_power_consumed_from_grid_kw = 0.0
        self.current_power_consumed_from_pv_kw = 0.0
        self.current_power_consumed_total_kw = 0.0
        self.current_power_fed_in_kw = 0.0
        
        # Initialize client
        self.client = self._create_client()
        
        # Test connection by doing an initial update
        try:
            self.update()
            logging.info("Modbus device: Successfully connected to the inverter")
        except Exception as e:
            logging.error(f"Modbus device: Error connecting to the device: {str(e)}")
            raise
    
    def _create_client(self):
        """Create and return the appropriate Modbus client based on connection type."""
        if self.connection_type.lower() == 'tcp':
            logging.info(f"Modbus device: Creating TCP client for {self.host}:{self.port}")
            return ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
        elif self.connection_type.lower() == 'rtu':
            logging.info(f"Modbus device: Creating RTU client for {self.port_name}")
            return ModbusSerialClient(
                method='rtu',
                port=self.port_name,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout
            )
        else:
            raise ValueError(f"Unsupported Modbus connection type: {self.connection_type}")
    
    def _get_endian(self, order):
        """Convert string endian specification to Endian enum."""
        if order.lower() == 'big':
            return Endian.BIG
        elif order.lower() == 'little':
            return Endian.LITTLE
        else:
            raise ValueError(f"Invalid endian order: {order}")
    
    def _read_register(self, register_config):
        """Read a register based on its configuration."""
        address = register_config['address']
        length = register_config['length']
        data_type = register_config['type']
        scale = register_config.get('scale', 1.0)
        
        # Read holding registers
        result = self.client.read_holding_registers(address, length, slave=self.unit_id)
        
        if result.isError():
            raise Exception(f"Error reading register at address {address}: {result}")
        
        # Decode the result based on data type
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers,
            byteorder=self._get_endian(self.byte_order),
            wordorder=self._get_endian(self.word_order)
        )
        
        # Extract value based on data type
        if data_type == 'uint16':
            value = decoder.decode_16bit_uint()
        elif data_type == 'int16':
            value = decoder.decode_16bit_int()
        elif data_type == 'uint32':
            value = decoder.decode_32bit_uint()
        elif data_type == 'int32':
            value = decoder.decode_32bit_int()
        elif data_type == 'float32':
            value = decoder.decode_32bit_float()
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        # Apply scaling factor
        return value * scale
    
    def update(self):
        """Updates all device stats by reading from Modbus registers."""
        try:
            # Connect if not connected
            if not self.client.connected:
                self.client.connect()
                # Small delay to ensure connection is established
                time.sleep(0.1)
            
            # Read all configured registers
            register_map = self.register_map
            
            # Read total energy produced
            if 'total_energy_produced' in register_map:
                self.total_energy_produced_kwh = self._read_register(register_map['total_energy_produced'])
            
            # Read total energy consumed (if available)
            if 'total_energy_consumed' in register_map:
                self.total_energy_consumed_kwh = self._read_register(register_map['total_energy_consumed'])
            
            # Read total energy fed in (if available)
            if 'total_energy_fed_in' in register_map:
                self.total_energy_fed_in_kwh = self._read_register(register_map['total_energy_fed_in'])
            
            # Read current power produced
            if 'current_power_produced' in register_map:
                self.current_power_produced_kw = self._read_register(register_map['current_power_produced'])
            
            # Read current power consumed from grid (if available)
            if 'current_power_consumed_grid' in register_map:
                self.current_power_consumed_from_grid_kw = self._read_register(register_map['current_power_consumed_grid'])
                # Some inverters report negative values for power fed to grid
                if self.current_power_consumed_from_grid_kw < 0:
                    self.current_power_fed_in_kw = -self.current_power_consumed_from_grid_kw
                    self.current_power_consumed_from_grid_kw = 0
            
            # Read current power fed in (if available as separate register)
            if 'current_power_fed_in' in register_map and self.current_power_fed_in_kw == 0:
                self.current_power_fed_in_kw = self._read_register(register_map['current_power_fed_in'])
            
            # Calculate derived values
            # Power consumed from PV = Power produced - Power fed in
            self.current_power_consumed_from_pv_kw = max(0, self.current_power_produced_kw - self.current_power_fed_in_kw)
            
            # Total power consumption = Grid consumption + PV consumption
            self.current_power_consumed_total_kw = self.current_power_consumed_from_grid_kw + self.current_power_consumed_from_pv_kw
            
            # Log the values if debug is enabled
            if logging.getLogger().level == logging.DEBUG:
                logging.debug(f"Modbus device: Absolute values:\n"
                            f" - Total produced: {self.total_energy_produced_kwh} kWh\n"
                            f" - Total consumption: {self.total_energy_consumed_kwh} kWh\n"
                            f" - Total fed in: {self.total_energy_fed_in_kwh} kWh")
                
                logging.debug(f"Modbus device: Momentary values:\n"
                            f" - Current production: {self.current_power_produced_kw} kW\n"
                            f" - Current feed-in: {self.current_power_fed_in_kw} kW\n"
                            f" - Current consumption from grid: {self.current_power_consumed_from_grid_kw} kW\n"
                            f" - Current consumption from PV: {self.current_power_consumed_from_pv_kw} kW\n"
                            f" - Current total consumption: {self.current_power_consumed_total_kw} kW")
                
        except Exception as e:
            logging.error(f"Modbus device: Error updating data: {str(e)}")
            # Try to close the connection to clean up
            if self.client.connected:
                self.client.close()
            raise 