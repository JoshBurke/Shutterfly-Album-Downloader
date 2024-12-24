import base64
import pyamf
from pyamf.remoting import decode

def decode_moments_string(moments_str):
    try:
        # First try direct AMF decoding
        decoder = pyamf.get_decoder(pyamf.AMF3)
        decoder.stream = moments_str.encode('utf-8')
        result = decoder.readElement()
        return result
    except Exception as e:
        print(f"Direct AMF3 decode failed: {e}")
        
        # Try with base64 decode first
        try:
            decoded = base64.b64decode(moments_str)
            decoder = pyamf.get_decoder(pyamf.AMF3)
            decoder.stream = decoded
            result = decoder.readElement()
            return result
        except Exception as e:
            print(f"Base64 + AMF3 decode failed: {e}")
            
            # Try hex decode
            try:
                decoded = bytes.fromhex(moments_str)
                decoder = pyamf.get_decoder(pyamf.AMF3)
                decoder.stream = decoded
                result = decoder.readElement()
                return result
            except Exception as e:
                print(f"Hex + AMF3 decode failed: {e}")
                
        return None

# Test with your moments string
moments = "5f8d1819300945854649676a514d0215030f00676a514d027056538841676a514dcb8ff779bd7777912d2d2d2d2d2d30302d6e335734386f443932764c66796a544e524a4f786b414e4970564d78566a484252576556376c7542523476666d6a6f507934357030687a57357a46434a6f4d56565a56353174344d686a624577524e794773634f6767"

result = decode_moments_string(moments)
print("Decoded result:", result)