"""
Generate a pseudorandom trial sequence and timing files for the football
fMRI task.

This script:
- reads setup/videoSpreadsheet.xlsx;
- shuffles the 40 video rows using a reproducible NumPy seed;
- prompts the user to select the MATLAB .mat filter file;
- creates an output trial-sequence CSV;
- creates output onset-duration-weight timing files for movies and feedback,
  per run.

Audio paths are relative to the filter name, e.g.:

    audio/filter/eqfilter-omems/clip1.wav
"""

from psychopy import core, data
from datetime import time
import numpy as np
import csv
import os
import tkinter as tk
from tkinter import filedialog

### SELECT FILTER PATH ###
filterPath = "4001-20260814-105108---4002-20260814-110142-flat.mat"

def timeToSeconds(value):
    """Convert Excel time or numeric value to seconds."""
    if isinstance(value, time):
        return (
            value.hour * 3600
            + value.minute * 60
            + value.second
            + value.microsecond / 1_000_000
        )

    return float(value)


#def selectFilterFile():
#    """
#    Open a GUI file selector and return the chosen .mat filter path.
#    """
#
#    root = tk.Tk()
#    root.withdraw()
#
#    filter_path = filedialog.askopenfilename(
#        title="Select the MATLAB .mat filter file",
#        filetypes=[
#            ("MATLAB filter files", "*.mat"),
#            ("All files", "*.*"),
#        ],
#    )
#
#    if not filter_path:
#        raise SystemExit(
#            "No filter file selected. Exiting."
#        )
#
#    return os.path.abspath(filter_path)

# ----- Seed and timing settings -----

expInfo = {}
expInfo["dateStr"] = data.getDateStr(format="%y%m%d%H%M")
expInfo["trialNumber"] = 40

# Replace this with a fixed integer to reproduce a previous sequence.
seed_int = int(expInfo["dateStr"])
# seed_int = 2608191217

np.random.seed(seed_int)

# ----- Project paths -----

setupDir = os.path.dirname(os.path.abspath(__file__))
projectDir = os.path.dirname(setupDir)
outputDir = os.path.join(projectDir, f"output/{seed_int}")
os.makedirs(outputDir, exist_ok=True)

masterFile = os.path.join(setupDir, "videoSpreadsheet.xlsx")

# ----- Select the filter file -----

#filterPath = selectFilterFile()
filterNameNoExt = os.path.splitext(
    os.path.basename(filterPath)
)[0]

print(f"Filter file selected: {filterPath}")
print(f"Filter name (no extension): {filterNameNoExt}")

# ------ MRI timing settings ------

durTR = 1.5
dummyNum = 4
dummyTime = durTR * dummyNum

# ------ Feedback settings ------

feedbackTime = 2.0
feedbackTrials = {2, 3, 6, 13, 14, 18, 22, 26, 29, 31, 33, 35}

# ----- Read and check the master spreadsheet -----

masterRows = data.importConditions(masterFile)

if len(masterRows) != expInfo["trialNumber"]:
    raise ValueError(
        f"Expected {expInfo['trialNumber']} rows, found {len(masterRows)}"
    )

# ----- Shuffle the complete rows -----

indices = np.arange(len(masterRows))
np.random.shuffle(indices)
shuffledRows = [masterRows[i] for i in indices]

# ----- Build the trial sequence -----

trialRows = []

for i, row in enumerate(shuffledRows):
    trialNum = i + 1

    videoFileName = str(row["movieFile"]).strip()
    audioBaseName = os.path.splitext(videoFileName)[0] + ".wav"

    # Relative to footballBrains.psyexp in the project root.
    movieFile = os.path.join("video", videoFileName)

    # Audio is now relative to the selected filter folder:
    # audio/filter/<FILTERNAME>/<clip>.wav
    audioFile = os.path.join(
        "audio",
        "filter",
        filterNameNoExt,
        audioBaseName,
    )

    movieTime = timeToSeconds(row["movieTime"])
    fixTime = int(np.random.randint(12, 19))
    goalTime = timeToSeconds(row["goalTime"])

    if trialNum in feedbackTrials:
        hasFeedback = 1
    else:
        hasFeedback = 0

    trialRows.append({
        "trialNum": trialNum,
        "movieFile": movieFile,
        "audioFile": audioFile,
        "movieTime": movieTime,
        "fixTime": fixTime,
        "goalTime": goalTime,
        "hasFeedback": hasFeedback,
        "feedbackTime": feedbackTime,
    })

# ----- Build per-run timing files -----

for runNum in range(1, 5):
    runStart = (runNum - 1) * 10
    runEnd = runNum * 10

    runRows = trialRows[runStart:runEnd]

    movieTimingRows = []
    feedbackTimingRows = []

    for i, row in enumerate(runRows):
        globalTrialNum = row["trialNum"]

        if i == 0:
            onset = row["fixTime"] - dummyTime
        else:
            previousRow = runRows[i - 1]

            previousFeedbackTime = (
                feedbackTime
                if previousRow["trialNum"] in feedbackTrials
                else 0
            )

            onset = (
                movieTimingRows[-1]["onset"]
                + previousRow["movieTime"]
                + previousFeedbackTime
                + row["fixTime"]
            )

        movieTimingRows.append({
            "onset": round(onset, 3),
            "duration": row["movieTime"],
            "weight": 1,
        })

        if globalTrialNum in feedbackTrials:
            feedbackOnset = onset + row["movieTime"]

            feedbackTimingRows.append({
                "onset": round(feedbackOnset, 3),
                "duration": feedbackTime,
                "weight": 1,
            })

    # ----- Save movie timing file -----

    movieTimingName = f"movie_run{runNum}_{seed_int}.txt"
    movieTimingPath = os.path.join(
        outputDir,
        movieTimingName
    )

    with open(movieTimingPath, "w", encoding="utf-8") as movieTimingFile:
        for row in movieTimingRows:
            movieTimingFile.write(
                f"{row['onset']}\t"
                f"{row['duration']}\t"
                f"{row['weight']}\n"
            )

    print(f"Wrote movie timing file: {movieTimingPath}")

    # ----- Save feedback timing file -----

    feedbackTimingName = f"feedback_run{runNum}_{seed_int}.txt"
    feedbackTimingPath = os.path.join(
        outputDir,
        feedbackTimingName
    )

    with open(
        feedbackTimingPath,
        "w",
        encoding="utf-8"
    ) as feedbackTimingFile:
        for row in feedbackTimingRows:
            feedbackTimingFile.write(
                f"{row['onset']}\t"
                f"{row['duration']}\t"
                f"{row['weight']}\n"
            )

    print(
        f"Wrote feedback timing file: "
        f"{feedbackTimingPath}"
    )

# ----- Save the trial sequence -----

outName = f"trialSequence{seed_int}.csv"
outPath = os.path.join(outputDir, outName)

with open(outPath, "w", newline="", encoding="utf-8") as outputFile:
    writer = csv.DictWriter(
        outputFile,
        fieldnames=[
            "trialNum",
            "movieFile",
            "audioFile",
            "movieTime",
            "fixTime",
            "goalTime",
            "hasFeedback",
            "feedbackTime",
        ]
    )
    writer.writeheader()
    writer.writerows(trialRows)

print(f"Wrote trial sequence: {outPath}")
print(f"Seed used: {seed_int}")
print(f"Filter used: {filterNameNoExt}")

outName = f"scannerDetails{seed_int}.txt"
outPath = os.path.join(outputDir, outName)

with open(outPath, "w", newline="", encoding="utf-8") as f:
    f.write(f"TR duration: {durTR}\n")
    f.write(f"Number of dummy scans: {dummyNum}\n")
    f.write(f"Time taken by dummy scans: {dummyTime}\n")