import os
import sys
from datetime import datetime

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.volume_profile import VolumeProfile, classify_profile_shape

def run_tests():
    print("Testing classify_profile_shape...")
    
    # Test 1: P-Shape (POC near top)
    vp_p = VolumeProfile(poc=100.0, va_high=105.0, va_low=90.0)
    # Range is 50 to 110 (size 60)
    # POC is at 100. (100 - 50) / 60 = 50 / 60 = 0.83 (Upper 35% -> >= 0.65)
    shape = classify_profile_shape(vp_p, 110.0, 50.0)
    print(f"Test 1 (Expected P): {shape}")
    
    # Test 2: B-Shape (POC near bottom)
    vp_b = VolumeProfile(poc=60.0, va_high=75.0, va_low=55.0)
    # POC is at 60. (60 - 50) / 60 = 10 / 60 = 0.16 (Lower 35% -> <= 0.35)
    shape = classify_profile_shape(vp_b, 110.0, 50.0)
    print(f"Test 2 (Expected B): {shape}")
    
    # Test 3: D-Shape (POC in middle)
    vp_d = VolumeProfile(poc=80.0, va_high=90.0, va_low=70.0)
    # POC is at 80. (80 - 50) / 60 = 30 / 60 = 0.5 (Middle)
    shape = classify_profile_shape(vp_d, 110.0, 50.0)
    print(f"Test 3 (Expected D): {shape}")
    
    print("Done.")

if __name__ == '__main__':
    run_tests()
