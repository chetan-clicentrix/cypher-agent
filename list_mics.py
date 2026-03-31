import sounddevice as sd
devices = sd.query_devices()
print("\nAvailable Input Microphones:")
print("-" * 50)
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        print(f"[{i}] {d['name']}")
print("-" * 50)
print(f"\nDefault input device: [{sd.default.device[0]}]")
