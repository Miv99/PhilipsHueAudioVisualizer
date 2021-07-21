# PhilipsHueAudioVisualizer
This project listens to any audio device connected to your computer (including sound card) and allows audio frequencies and volumes to be visualized through Philips Hue smart lights. The lights change colors based on the top N strongest frequency bins, where N is the number of lights, and change brightness based on the current volume in relation to the weighted moving average of the last two minutes (by default; configurable) of audio's volume.

Most of the audio processing code is from [this](https://github.com/aiXander/Realtime_PyAudio_FFT) repo.

# Setup

All requirements are in requirements.txt. Run
```
pip install -r requirements.txt
```
to install them.

The first two variables in config.py must be configured to reflect your own Philips Hue Bridge's IP address and your lights' names. Everything else can be configured however you want, with recommended default values already set.
