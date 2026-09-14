A block-design fMRI experiment producing extensive and consistent brain activation 
using audiovisual stimuli of football clips, alongside an attention-based button-press
task, rewarded for timing accuracy and keeping still.

Developed by Sam Eccleston in PsychoPy v2024.1.5, with help from BUCNI's Professor Fred 
Dick and Dr David Haydock.

-------- Step 1: Stimuli Generation --------
This experiment uses football goals from Pitch International LLP's "500 Great Goals" 
Collection. After encrypting the first DVD disc as footballGoalsDVD.mp4 using MakeMKV and 
HandBrake, videoCutter.py (requires ffmpeg) will produce videos of goals based off
videoSpreadsheet.xlsx and extract audio.

applyFilter.py then filters audio for use with BUCNI's OMEMS devices. 
OMEMS filter repository link: https://github.com/BUCNI/omems-filters

-------- Step 2: Trial and Timing File Generation --------
The same spreadsheet of videos will be used by trialGeneration.py to produce
the pseudorandomly shuffled trial sequence of 40 football videos along with each run's
movie and feedback timing files. The randomised shuffle is unique for each participant,
based on a seed of the date.

-------- Step 3: Run Experiment --------
The correct trial sequence will be chosen by inputting your seed. Choose from the GUI 
pop-up which of four runs you want to proceed with.

The experiment is set up with scanner repetitions mapped to 't' and right-hand index 
finger button presses are mapped to '6'.

–––---–– Step 4: Generate Button-Press Timing Files ––––---–
Use buttonTimingGeneration.py to generate timing files for participants' button presses 
from the output/SEED/run?trials.csv files. With the movie, button-press, and feedback
timing files you can now run statistical analyses.