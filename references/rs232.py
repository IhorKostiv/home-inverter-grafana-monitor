import serial
import binascii
import crcmod
import platform

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

def main():

    print("Type your message and press Enter. Type '' to quit.")

    while True:
        # Get input from the keyboard
        user_input = input("Enter message: ")

        if user_input.lower() == '':
            break

        b = user_input.encode("utf-8")

        if b[:2].lower() != b'0x':
            # Calculate CRC and append to the message
            crc = axiomaCRC(b)
            message_with_crc = b + crc + 0x0D.to_bytes(1)
        else:
            message_with_crc = bytes.fromhex(b[2:].decode('utf-8'))
        # Convert message to hex format
        hex_message = binascii.hexlify(message_with_crc).decode('utf-8')

        print(f"Sending to RS232 (hex): {hex_message}")
        # Open the RS232 port
        if platform.system() == "Linux":
            ser = serial.Serial('/dev/ttyUSB0', baudrate=2400, timeout=1)
            # Send the hex message to the RS232 port
            ser.write(bytes.fromhex(hex_message))

            # Read and print the response from the RS232 port
            ser.flush()
            response = ser.readline()
            hex_response = binascii.hexlify(response).decode('utf-8')
            print(f"Response from RS232: {response}\nHex : {hex_response}")

            # Close the RS232 port
            ser.close()
            print("RS232 port closed.")

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