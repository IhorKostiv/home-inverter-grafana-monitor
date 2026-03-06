import serial
import crcmod
import platform
import sys
import time
from datetime import datetime

# Define the custom CRC function with a 16-bit polynomial
def axiomaCustomCRC():
    polynomial = 0x11021
    initial_value = 0x0000
    final_xor = 0x0000
    reflect = False
    crc_func = crcmod.mkCrcFun(polynomial, initCrc=initial_value, xorOut=final_xor, rev=reflect)
    return crc_func

def incrementSpecialChar(crc):
    # Define the set of special characters to check against
    specialChars = {0x28, 0x0d, 0x0a}
    # Extract the high and low bytes
    hb = (crc >> 8) & 0xFF
    lb = crc & 0xFF
    # Increment bytes if they are special ones
    hb = (hb + 1) & 0xFF if hb in specialChars else hb
    lb = (lb + 1) & 0xFF if lb in specialChars else lb
    # Combine the high and low bytes back into a two-byte value
    return (hb << 8) | lb

def axiomaCRC(data):
    crc_func = axiomaCustomCRC()
    crc_value = incrementSpecialChar(crc_func(data))
    return crc_value.to_bytes(2, byteorder='big')

def sendMessage(msg: str):
        b = msg.encode("utf-8")
        if b[:2].lower() != b'0x':
            # Calculate CRC and append to the message
            crc = axiomaCRC(b)
            message_with_crc = b + crc + b'\r'
        else:
            message_with_crc = bytes.fromhex(b[2:].decode('utf-8'))
        # Convert message to hex format
        hex_message = message_with_crc.hex() # binascii.hexlify(message_with_crc).decode('utf-8')

        # Wait until the current second is greater than 30
        # there might be interference with other RS232 scheduled tasks
        s = 35 - datetime.now().second
        if s > 0:
            print(f"Wait {s}s...")
            time.sleep(s)

        print(f"{datetime.now()}\tSending to RS232 {bytes.fromhex(hex_message[:-6]).decode('utf-8')} 0x{hex_message}")
        if platform.system() == "Linux":
            # Open the RS232 port
            ser = serial.Serial('/dev/ttyUSB0', baudrate=2400, timeout=1)
            # Send the hex message to the RS232 port
            ser.write(bytes.fromhex(hex_message))
            # Read and print the response from the RS232 port
            ser.flush()
            response = ser.readline()
            hex_response = response.hex() # binascii.hexlify(response).decode('utf-8')
            print(f"{datetime.now()}\tResponse from RS232: {response}\nHex : {hex_response}")
            # Close the RS232 port
            ser.close()
            print("RS232 port closed.")

def translateComand(cmd: str):
    commands = {
        "UTI"  : "POP00", "SUB"  : "POP01", "SBU"  : "POP02", 
        "CSO"  : "PCP01", "SNU"  : "PCP02", "OSO"  : "PCP03",
          "0A" : "MUCHGC000", "2A" : "MUCHGC002", "10A" : "MUCHGC010", "20A" : "MUCHGC020", "30A" : "MUCHGC030", "40A" : "MUCHGC040",
        "10AA" : "MNCHGC010", "20AA" : "MNCHGC020", "30AA" : "MNCHGC030", "40AA" : "MNCHGC040",
        "26.6V": "PBFT26.6", "27.8V": "PBFT27.8", "27.9V": "PBFT27.9",
    }
    if cmd.upper() in commands:
        return commands[cmd.upper()]
    else:
        return cmd

def main():
    if len(sys.argv) > 1:
        for cmd in sys.argv[1:]:
           sendMessage(translateComand(cmd))
    else:
        print("Type your message and press Enter. Type exit to quit.")
        while True:
            # Get input from the keyboard
            user_input = input("Enter message: ")
            if user_input.lower() in ['', 'exit']:
                break
            sendMessage(translateComand(user_input))

def hex_to_string(hex_string):
    try:
        # Split hex string by spaces to ensure proper formatting
        hex_pairs = [hex_string[i:i+2] for i in range(0, len(hex_string), 2)] 
        # Convert each pair of hex characters to its corresponding ASCII character 
        chars = [chr(int(hex_pair, 16)) for hex_pair in hex_pairs]       
        # Join the list of characters into a single string
        result = ''.join(chars)
        return result
    except ValueError as e:
        return f"Invalid hex string: {e}"

def main2():
    while True:
        s = input("Enter Mesage: ")
        if s.lower() == "exit":
            break
        #hex_input = "283232322e322034392e39203232322e322034392e392030313939203031353720303036203436302032372e3030203030302031303020303033392030302e30203135312e312030302e3030203030303030203031303130313130203030203031203030303030203131302030203031203030303029d30d"
        output = hex_to_string(s)
        print("Character string:", output)

if __name__ == "__main__":
    main()