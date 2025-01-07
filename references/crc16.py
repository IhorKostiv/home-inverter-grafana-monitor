from crcmod import predefined
data = b'QPIGS'
crc_ccitt_16 = crcmod.predefined.Crc('crc-ccitt-false').new(data)
crc_ccitt_16.update(data)
crc_hex = format(crc_ccitt_16.crcValue, '04X')
print(f"CRC-CCITT (16-bit) of '{data}' is: 0x{crc_hex}")

data = b''
crc_ccitt_16 = crc_ccitt_16(data)
 
print(f"CRC-CCITT (16-bit) of '{data}' is: 0x{crc_ccitt_16:04X}") # 5150494753 B7A9 0D