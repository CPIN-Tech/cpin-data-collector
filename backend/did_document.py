import json

def create_did_doc(address):
    document = {}
    document['id'] = f'did:peaq:{address}'
    document['controller'] = f'did:peaq:{address}'
    json_data = json.dumps(data)
    json_bytes = json_data.encode('utf-8')
    json_hex = json_bytes.hex()
    return '0x' + json_hex
