import argparse
from src.stream_analyzer import Stream_Analyzer
import time
import random
import numpy
import sys
import config as cfg

from phue import Bridge

numpy.set_printoptions(threshold=sys.maxsize)

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--device', type=int, default=None, dest='device',
						help='pyaudio (portaudio) device index')
	parser.add_argument('--height', type=int, default=400, dest='height',
						help='height, in pixels, of the visualizer window')
	parser.add_argument('--n_frequency_bins', type=int, default=50, dest='frequency_bins',
						help='The FFT features are grouped in bins')
	parser.add_argument('--verbose', action='store_true')
	parser.add_argument('--window_ratio', default='24/9', dest='window_ratio',
						help='float ratio of the visualizer window. e.g. 24/9')
	return parser.parse_args()

def convert_window_ratio(window_ratio):
	if '/' in window_ratio:
		dividend, divisor = window_ratio.split('/')
		try:
			float_ratio = float(dividend) / float(divisor)
		except:
			raise ValueError('window_ratio should be in the format: float/float')
		return float_ratio
	raise ValueError('window_ratio should be in the format: float/float')

def init_lights(light_names=[]):
	bridge = Bridge(cfg.bridge_ip)
	bridge.connect()
	
	for light in bridge.lights:
		light.on = True
		light.transitiontime = 1
		
	if len(light_names) == 0:
		num_lights = len(bridge.lights)
		lights = bridge.lights
	else:
		num_lights = len(light_names)
		
		lights = []
		for k, v in bridge.get_light_objects('name').items():
			if k in light_names:
				lights.append(v)
	light_gradients = randomize_lights_gradients(num_lights)
		
	return lights, num_lights, light_gradients
	
def randomize_lights_gradients(num_lights):
	'''
	Returns a list of gradients, one for each light.
	Each gradient is a list of the min x, max x, min y, and max y of each light in the CIE color space.
	'''

	x_min = 0.2
	x_max = 0.8
	y_min = 0
	y_max = 0.6
	
	# Choose gradients such that the initial color is somewhere in the first third
	# and the final color is somewhere in the last third

	gradients = []

	for i in range(num_lights):
		'''
		gradients.append([
			[x_min + ((x_max - x_min)/num_lights * i), x_min + ((x_max - x_min)/num_lights * (i + 1))], 
			[y_min + ((y_max - y_min)/num_lights * i), y_min + ((y_max - y_min)/num_lights * (i + 1))]
			])
		'''
		if random.random() > 0.5:
			gradients.append([
				[random.uniform(0.6, 0.8), random.uniform(0.2, 0.4)],
				[random.uniform(0.4, 0.6), random.uniform(0.0, 0.2)]
				])
		else:
			gradients.append([
				[random.uniform(0.2, 0.4), random.uniform(0.6, 0.8)],
				[random.uniform(0, 0.2), random.uniform(0.4, 0.6)]
				])
			
	return gradients

def update_lights(lights, num_lights, lights_gradients, max_wma_len, prev_fft_sums, binned_fft, prev_bri, rolling_counter):
	'''
	lights - a list of lights
	num_lights - the number of lights
	lights_gradients - from randomize_lights_gradients()
	max_wma_len - the maximum number of ffts to consider in the weighted moving average
	prev_fft_sums - a list of the sum of previous binned ffts; this will be modified
	binned_fft - the current fft
	prev_bri - previous light brightness
	rolling_counter - rolling counter used for individual light priority switching
	
	Returns the new fft sums (the modified prev_fft_sums)
	'''

	# Calculate weighted moving average of previous ffts
	# where farther values (temporally) have higher weights
	s1 = 0
	s2 = 0
	for i, s in enumerate(prev_fft_sums):
		s1 += s * (i + 1)
		s2 += i + 1
	if s2 == 0:
		wma = 0
	else:
		wma = s1/s2
		
	fft_sum = sum(binned_fft)
	# Threshold for what constitutes actual sound
	if fft_sum > cfg.energy_threshold_for_lights_update:
	
		# Change lights' colors depending on binned_fft maxes
		# e.g. if num_lights is 3, then the first light will be a linear interpolation between its min/max x/y
		# depending on the index of the max bin in the first third of binned_fft
		num_bins = len(binned_fft)
		argsorted = binned_fft.argsort()
		for i in range(num_lights):
			interpolation_amount = argsorted[(i + rolling_counter) % num_lights]/num_bins
			x = lights_gradients[i][0][0] + (lights_gradients[i][0][1] - lights_gradients[i][0][0]) * interpolation_amount
			y = lights_gradients[i][1][0] + (lights_gradients[i][1][1] - lights_gradients[i][1][0]) * interpolation_amount
					
			lights[i].xy = [x, y]
			
		# Compare the sum of this fft to the WMA to calculate lights' brightnesses
		if wma == 0:
			bri = 1 # If the first update, use min brightness
		else:
			bri = min(254, 1 + (fft_sum/(wma * 1.6)) * 253) # bri is in range [1, 254]
		bri = int(bri)
		# Set lights' brightnesses
		if bri/prev_bri < 1 - cfg.min_brightness_change_threshold or bri/prev_bri > 1 + cfg.min_brightness_change_threshold \
			or (prev_bri != 1 and bri == 1) or (prev_bri != 254 and bri == 254):
			for light in lights:
				light.brightness = bri
			prev_bri = bri
		
	# Append the latest fft, removing the oldest if necessary
	prev_fft_sums.append(fft_sum)
	if len(prev_fft_sums) > max_wma_len:
		prev_fft_sums = prev_fft_sums[1:]
	
	return prev_fft_sums, prev_bri

def run_FFT_analyzer():
	args = parse_args()
	window_ratio = convert_window_ratio(args.window_ratio)

	ear = Stream_Analyzer(
					device = args.device,		 # Pyaudio (portaudio) device index, defaults to first mic input
					rate   = None,				 # Audio samplerate, None uses the default source settings
					FFT_window_size_ms	= 50,	 # Window size used for the FFT transform
					updates_per_second	= 1000,	 # How often to read the audio stream for new data
					smoothing_length_ms = 100,	 # Apply some temporal smoothing to reduce noisy features
					n_frequency_bins = args.frequency_bins, # The FFT features are grouped in bins
					visualize = 1,				 # Visualize the FFT features with PyGame
					verbose	  = args.verbose,	 # Print running statistics (latency, fps, ...)
					height	  = args.height,	 # Height, in pixels, of the visualizer window,
					window_ratio = window_ratio	 # Float ratio of the visualizer window. e.g. 24/9
					)
					
	lights, num_lights, lights_gradients = init_lights(cfg.light_names)

	lights_update_freq = cfg.lights_update_freq 	# Minimum seconds between each lights update
	lights_color_change_freq = cfg.lights_color_change_freq		# Minimum seconds between each lights default colors change
	max_wma_len = cfg.max_wma_len					# Number of previous ffts to consider in the lights' brightnesses calculations; 
													# an fft is added only every lights_update_freq seconds
	skip_first_bins = int(cfg.skip_first_bins * args.frequency_bins)	# How many bins in the lower frequencies to be ignored, since
													# those tend to dominate sound
	lights_rolling_freq = cfg.lights_rolling_freq	# Minimum seconds between each lights priority switch
													# e.g. time before light 1 switches from showing the biggest frequency
													# to showing the 2nd biggest frequency
											
	prev_fft_sums = []
	prev_bri = 1
	rolling_counter = 0
											
	last_lights_update = time.time()
	last_color_change = time.time()
	last_roll = time.time()
	
	while True:
		t = time.time()

		raw_fftx, raw_fft, binned_fftx, binned_fft = ear.get_audio_features()
		
		delta_lights_time = t - last_lights_update
		delta_roll_time = t - last_roll
		delta_color_change_time = t - last_color_change
		
		if delta_color_change_time >= lights_color_change_freq:
			last_color_change = t
			lights_gradients = randomize_lights_gradients(num_lights)
			
		if cfg.roll_lights and delta_roll_time >= lights_rolling_freq:
			last_roll = t
			rolling_counter += 1
		
		if delta_lights_time >= lights_update_freq:
			last_lights_update = t
			prev_fft_sums, prev_bri = update_lights(lights, num_lights, lights_gradients, max_wma_len, prev_fft_sums, binned_fft[(skip_first_bins + 1):], prev_bri, rolling_counter)

if __name__ == '__main__':
	run_FFT_analyzer()
