# IP address of the Philips Hue Bridge
bridge_ip = 'YOUR PHILIPS HUE BRIDGE IP ADDRESS HERE'
# The names of the lights to be used as defined in the Philips Hue Bridge app
# No limit on the amount of lights (except by the Bridge itself)
light_names = ['YOUR LIGHT NAME 1', 'YOUR LIGHT NAME 2']


# Whether to have lights periodically switch which max frequency is being shown
# (see below comment for more explanation)
roll_lights = False
# Minimum seconds between each lights priority switch
# Only used when roll_lights is True
# e.g. time before light 1 switches from showing the biggest frequency
# to showing the 2nd biggest frequency
lights_rolling_freq = 1

# Ratio of sum of bins' energies needed over weighted moving average of the last max_wma_len
# sums of bins' energies for lights to be max brightness
volume_threshold_for_max_brightness = 1.6

# Minimum energy sum required for any lights update
energy_threshold_for_lights_update = 2000

# Minimum change in percentage (i.e. 0.2 is 20%) in brightness
# compared to the lights' previous brightnesses for an actual update
# to the lights' brightnesses. Too many light brightnesses updates
# will cause lag and occasional freezes.
min_brightness_change_threshold = 0.2

# Seconds between each lights color/brightness update
lights_update_freq = 0.08

# Seconds between each lights gradient colors change
lights_color_change_freq = 10

# Number of previous lights updates to consider in the current lights' brightnesses' calculations.
# Default is 120/lights_update_freq, i.e. 120 seconds' worth of updates
max_wma_len = 120/lights_update_freq

# Percentage of the first bins in the lower frequencies to be ignored, since those tend to dominate sound
skip_first_bins = 0.06