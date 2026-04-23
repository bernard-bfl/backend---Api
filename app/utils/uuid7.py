import os 
import time 

def generate_uuid7() -> str:
    timestamp_ms = int(time.time() * 1000)

    # 48-bit timestamp 
    ts_hex = format(timestamp_ms, "012x")

    # 12 random bits for rand_a (version nibble = 7)
    rand_bytes = os.urandom(10)
    rand_a = int.from_bytes(rand_bytes[:2], "big") & 0x0FFF

    #62 random bits for rand_b (variant bits = 10)
    rand_b_raw = int.from_bytes(rand_bytes[2:], "big")
    rand_b = (rand_b_raw & 0x3FFFFFFFFFFFFFFF) | 0x8000000000000000

    #Assemble 
    part1 = ts_hex[:8]
    part2 = ts_hex[8:12]
    part3 = format(0x7000 | rand_a, "04x")
    part4 = format(rand_b >> 48, "04x")
    part5 = format(rand_b & 0xFFFFFFFFFFFF, "012x")

    return f"{part1}-{part2}-{part3}-{part4}-{part5}"