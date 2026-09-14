"""
Generates the button press timing files from participants results.

The script:
- scans output/<SEED>/ folders;
- reads each run CSV;
- creates a button timing file when it does not already exist;
- writes only observed button presses as duration-0 motor events;
- includes feedback duration in the underlying trial timeline.
"""

import csv
import os

# ----- Project paths -----

setupDir = os.path.dirname(os.path.abspath(__file__))
projectDir = os.path.dirname(setupDir)
outputDir = os.path.join(projectDir, "output")

print("Setup directory:", setupDir)
print("Project directory:", projectDir)
print("Output directory:", outputDir)

# ----- MRI timing settings -----

durTR = 1.5
dummyNum = 4
dummyTime = durTR * dummyNum

# ----- Feedback settings -----

feedbackTime = 2.0

feedbackTrials = {
    2,
    3,
    6,
    13,
    14,
    18,
    22,
    26,
    29,
    31,
    33,
    35,
}

# ----- Check that output exists -----

if not os.path.isdir(outputDir):
    raise FileNotFoundError(
        f"Output directory was not found: {outputDir}"
    )

# ----- Look through all seed folders -----

for SEED in os.listdir(outputDir):

    seedPath = os.path.join(outputDir, SEED)

    # Ignore normal files located directly inside output/
    if not os.path.isdir(seedPath):
        continue

    # Ignore folders that are not numeric seed folders
    if not SEED.isdigit():
        print(f"Skipping non-seed folder: {SEED}")
        continue

    print(f"\nChecking seed folder: {SEED}")

    # ----- Check each of the four runs -----

    for runNum in range(1, 5):

        runCsvName = f"run{runNum}trials.csv"
        runCsvPath = os.path.join(seedPath, runCsvName)

        timingName = f"buttonTimingRun{runNum}.txt"
        timingPath = os.path.join(seedPath, timingName)

        # Do not overwrite an existing timing file
        if os.path.exists(timingPath):
            print(
                f"Skipping run {runNum}: "
                f"button timing file already exists"
            )
            continue

        # Skip runs that do not have an output CSV
        if not os.path.exists(runCsvPath):
            print(
                f"Skipping run {runNum}: "
                f"{runCsvName} was not found"
            )
            continue

        try:
            # ----- Read all rows from the run CSV -----

            with open(
                runCsvPath,
                "r",
                newline="",
                encoding="utf-8-sig"
            ) as runFile:

                reader = csv.DictReader(runFile)
                runRows = list(reader)

            # Stop processing this run if the CSV contains no rows
            if not runRows:
                print(
                    f"Skipping run {runNum}: "
                    f"{runCsvName} contains no rows"
                )
                continue

            # Skip runs that were collected without a buttonPress component
            if "buttonPress.rt_raw" not in runRows[0]:
                print(
                    f"Skipping run {runNum}: "
                    f"buttonPress.rt_raw column is missing"
                )
                continue

            # ----- Keep actual trial rows only -----

            trialRows = []

            for row in runRows:

                try:
                    trialNum = int(row["trialNum"])
                    fixTime = float(row["fixTime"])
                    movieTime = float(row["movieTime"])

                except (TypeError, ValueError):
                    # Skip blank rows and PsychoPy metadata rows such as:
                    # extraInfo, participant, session, date, expName, etc.
                    continue

                buttonPressRtText = row.get(
                    "buttonPress.rt_raw",
                    ""
                )

                try:
                    buttonPressRt = float(buttonPressRtText)

                except (TypeError, ValueError):
                    # No valid response occurred on this trial.
                    buttonPressRt = None

                trialRows.append({
                    "trialNum": trialNum,
                    "fixTime": fixTime,
                    "movieTime": movieTime,
                    "buttonPressRt": buttonPressRt,
                })

            # Warn if the run is incomplete, but do not stop processing it
            if len(trialRows) != 10:
                print(
                    f"Warning for run {runNum} in seed {SEED}: "
                    f"found {len(trialRows)} valid trial rows; "
                    f"expected 10"
                )

            # Do not proceed if no actual trials were found
            if not trialRows:
                print(
                    f"Skipping run {runNum} in seed {SEED}: "
                    f"no valid trial rows found"
                )
                continue

            # Ensure trial order is correct even if CSV rows were reordered
            trialRows.sort(
                key=lambda row: row["trialNum"]
            )

            # ----- Calculate movie timeline and button onsets -----

            timingRows = []
            previousMovieOnset = None

            for i, row in enumerate(trialRows):

                # First movie begins after its own fixation period,
                # adjusted for dummy scans.
                if i == 0:
                    movieOnset = (
                        row["fixTime"]
                        - dummyTime
                    )

                # Every later movie begins after:
                # previous movie onset
                # + previous movie duration
                # + feedback after the previous trial, if any
                # + current fixation duration
                else:
                    previousRow = trialRows[i - 1]

                    if previousRow["trialNum"] in feedbackTrials:
                        previousFeedbackTime = feedbackTime
                    else:
                        previousFeedbackTime = 0

                    movieOnset = (
                        previousMovieOnset
                        + previousRow["movieTime"]
                        + previousFeedbackTime
                        + row["fixTime"]
                    )

                # Store this movie onset so the next trial can use it
                previousMovieOnset = movieOnset

                # Write a motor-event onset only if an actual button press
                # was recorded on this trial.
                if row["buttonPressRt"] is not None:

                    buttonOnset = (
                        movieOnset
                        + row["buttonPressRt"]
                    )

                    timingRows.append({
                        "onset": round(buttonOnset, 3),
                        "duration": 0,
                        "weight": 1,
                    })

                else:
                    print(
                        f"Run {runNum}, trial {row['trialNum']}: "
                        f"no button press; "
                        f"no button timing row written"
                    )

            # Do not create an empty file
            if not timingRows:
                print(
                    f"Skipping run {runNum} in seed {SEED}: "
                    f"no valid button presses were recorded"
                )
                continue

            # ----- Write the button timing file -----

            with open(
                timingPath,
                "w",
                encoding="utf-8"
            ) as timingFile:

                for row in timingRows:
                    timingFile.write(
                        f"{row['onset']}\t"
                        f"{row['duration']}\t"
                        f"{row['weight']}\n"
                    )

            print(
                f"Wrote button timing file: "
                f"{timingPath}"
            )

        except Exception as error:
            print(
                f"Skipping run {runNum} in seed {SEED}: "
                f"{error}"
            )
            continue