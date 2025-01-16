import crcmod

# Define the custom CRC function with a 16-bit polynomial
def create_custom_crc():
    polynomial = 0x11021  # Correct 16-bit polynomial
    initial_value = 0x0000
    final_xor = 0x0000
    reflect = False

    crc_func = crcmod.mkCrcFun(polynomial, initCrc=initial_value, xorOut=final_xor, rev=reflect)
    return crc_func

def calculate_crc(data):
    crc_func = create_custom_crc()
    crc_value = crc_func(data)
    return crc_value

# Test the function with given values and their corresponding CRCs
test_values = {
    b'QPIGS': 0xB7A9,   # Example
    b'QDI': 0x711B,     # Example
    b'QPIRI': 0xF854,   # Example
    b'QMOD': 0x49c1,
    b'Q1': 0x1BFC,
    b'QPI': 0xbeac,
    b'QPIWS': 0xb4da,
    b'QID': 0x180B,
    b'QVFW': 0x673E,
    b'QVFW2': 0xA3D5,
    b'QFLAG': 0x2543,
    b'QPIGS': 0xB7A9,
    b'QDI': 0x711B,
    #0D""; b'(230.0 50.0 0030 21.0 27.0 28.2 23.0 60 0 0 2 0 0 0 0 0 1 1 1 0 1 0 27.0 0 1)F\r'
    b'QMCHGCR': 0xD855,
    b'QMUCHGCR': 0x2634,
    b'QBOOT': 0x0A88,
    b'QOPM': 0xA5C5,
    b'QPIRI': 0xF854,
    #0D""; b'(220.0 13.6 220.0 50.0 13.6 3000 3000 24.0 25.5 21.0 28.2 27.0 0 40 040 1 1 2 1 01 0 0 27.0 0 1\x8d\xd2\r'
    b'QPGS0': 0x3FDA,
    b'QBV': 0x3863,
    b'PF': 0x26BD,
    b'POP02': 0xE20A,
    b'POP01': 0xD269,
    b'POP00': 0xC248,
    b'PCP00': 0x8D7A,
    b'PCP01': 0x9D5B,
    b'PCP02': 0xAD38,
    b'MUCHGC002': 0xB5D1,
    b'MUCHGC010': 0xA6A2,
    b'MUCHGC020': 0xF3F1,
    b'MUCHGC030': 0xC0C0,
    b'PPCP000': 0xE6E1,
    b'PPCP001': 0xF6C0,
    b'PPCP002': 0xC6A3,
    b'QPIGS2': 0x682D,
    b'POP03': 0xF22B
}

for data, expected_crc in test_values.items():
    crc = calculate_crc(data)
    print(f"Data: {data} | Calculated CRC: {crc:04X} | Expected CRC: {expected_crc:04X} | Match: {crc == expected_crc}")
