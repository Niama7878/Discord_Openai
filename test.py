import pyaudio

p = pyaudio.PyAudio()
target_devices = {"CABLE-C Input (VB-Audio Cable C)", "CABLE-D Output (VB-Audio Cable D)"}

index = [
    f"{info['name']}: {i}" for i in range(p.get_device_count())
    if (info := p.get_device_info_by_index(i))['name'] in target_devices 
    and (info['maxInputChannels'] == 2 or info['maxOutputChannels'] == 2)
]

print(index)
p.terminate()