#!/usr/bin/env python3

"""
Apply the laboratory's MATLAB fMRI audio equalisation filter to all
WAV files in a user-selected raw audio folder.

The user selects:
1) the raw audio directory (e.g. .../audio/raw)
2) the MATLAB .mat filter file

Output is written to:

    ../filter/<FILTER_FILENAME>/

relative to the selected raw audio directory.
"""

from pathlib import Path
import warnings
import tkinter as tk
from tkinter import filedialog

import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample_poly


FILTER_FS = 44_100
SUPPORTED_FS = {44_100, 48_000}


def load_mat_filter(filter_path):
    """
    Load the first usable numeric matrix from a MATLAB .mat file.
    """

    filter_path = Path(filter_path)

    try:
        mat_data = loadmat(
            filter_path,
            squeeze_me=True,
            struct_as_record=False,
        )

        ignored_names = {
            "__header__",
            "__version__",
            "__globals__",
        }

        candidate_names = [
            name
            for name in mat_data
            if name not in ignored_names
        ]

        if not candidate_names:
            raise ValueError(
                f"No user variables were found in {filter_path}"
            )

        filter_array = None

        for name in candidate_names:
            candidate = np.asarray(mat_data[name])

            if np.issubdtype(candidate.dtype, np.number):
                filter_array = candidate
                print(f"Loaded filter variable: {name}")
                break

        if filter_array is None:
            raise ValueError(
                f"No numeric filter matrix was found in {filter_path}"
            )

    except ValueError as error:
        if "Unknown mat file type" not in str(error):
            raise

        try:
            import h5py
        except ImportError as import_error:
            raise ImportError(
                "This appears to be a MATLAB 7.3 .mat file. "
                "Install h5py with: python -m pip install h5py"
            ) from import_error

        with h5py.File(filter_path, "r") as mat_file:
            dataset_names = []

            def collect_datasets(name, obj):
                if isinstance(obj, h5py.Dataset):
                    dataset_names.append(name)

            mat_file.visititems(collect_datasets)

            if not dataset_names:
                raise ValueError(
                    f"No datasets were found in {filter_path}"
                )

            filter_array = np.asarray(
                mat_file[dataset_names[0]][()]
            )

            print(
                "Loaded MATLAB 7.3 dataset: "
                f"{dataset_names[0]}"
            )

    filter_array = np.asarray(filter_array, dtype=np.float64)

    if filter_array.ndim != 2:
        raise ValueError(
            "The filter must be a two-dimensional matrix. "
            f"Found shape {filter_array.shape}."
        )

    if filter_array.shape[0] < filter_array.shape[1]:
        warnings.warn(
            "Filter appears to be transposed; correcting orientation."
        )
        filter_array = filter_array.T

    if filter_array.shape[1] != 2:
        raise ValueError(
            "The filter must have exactly two columns "
            f"for stereo audio. Found shape {filter_array.shape}."
        )

    return filter_array


def resample_filter_kernel(kernel, source_fs, target_fs):
    """
    Resample a stereo FIR kernel while preserving its scale.
    """

    if source_fs == target_fs:
        return kernel

    gcd = np.gcd(source_fs, target_fs)
    up = target_fs // gcd
    down = source_fs // gcd

    resampled_kernel = resample_poly(
        kernel,
        up=up,
        down=down,
        axis=0,
        window=("kaiser", 5.0),
        padtype="constant",
    )

    resampled_kernel *= source_fs / target_fs

    return resampled_kernel


def matlab_same_convolution(signal, kernel):
    """
    Reproduce MATLAB conv(signal, kernel, 'same') for 1-D arrays.
    """

    from scipy.signal import convolve

    return convolve(
        signal,
        kernel,
        mode="same",
        method="auto",
    )


def filter_audio(audio, sample_rate, filter_kernel):
    """
    Apply the stereo FIR filter to an audio array.
    """

    audio = np.asarray(audio, dtype=np.float64)

    if audio.ndim == 1:
        warnings.warn(
            "Mono file detected. Converting to stereo."
        )
        audio = np.column_stack((audio, audio))

    elif audio.ndim == 2 and audio.shape[1] == 2:
        pass

    else:
        raise ValueError(
            "Only mono or stereo audio is supported. "
            f"Found audio shape {audio.shape}."
        )

    if sample_rate not in SUPPORTED_FS:
        supported = ", ".join(
            str(rate) for rate in sorted(SUPPORTED_FS)
        )
        raise ValueError(
            f"Sampling rate {sample_rate} Hz is not supported. "
            f"Supported rates: {supported} Hz."
        )

    if sample_rate == FILTER_FS:
        filter_at_audio_rate = filter_kernel
    else:
        print(
            f"Resampling filter kernel from {FILTER_FS} "
            f"to {sample_rate} Hz..."
        )

        filter_at_audio_rate = resample_filter_kernel(
            filter_kernel,
            FILTER_FS,
            sample_rate,
        )

    filtered_audio = np.empty_like(audio)

    for channel in range(2):
        filtered_audio[:, channel] = matlab_same_convolution(
            audio[:, channel],
            filter_at_audio_rate[:, channel],
        )

    return filtered_audio


def db_to_gain(gain_db):
    """
    Convert dB gain to linear amplitude gain.
    """

    return 10 ** (gain_db / 20)


def amplitude_to_db(amplitude):
    """
    Convert amplitude to dB safely.
    """

    if amplitude <= 0:
        return float("-inf")

    return 20 * np.log10(amplitude)


def process_file(
    input_path,
    output_dir,
    filter_kernel,
    gain_db,
):
    """
    Filter one audio file and write it to output_dir.
    """

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nReading: {input_path}")

    audio, sample_rate = sf.read(
        input_path,
        always_2d=False,
        dtype="float64",
    )

    print(f"Sample rate: {sample_rate} Hz")
    print(f"Input shape: {np.asarray(audio).shape}")

    input_max = float(np.max(np.abs(audio)))

    print(
        f"Input max amplitude: {input_max:.9f} "
        f"({amplitude_to_db(input_max):.3f} dB)"
    )

    scaled_kernel = filter_kernel * db_to_gain(gain_db)

    filtered_audio = filter_audio(
        audio,
        sample_rate,
        scaled_kernel,
    )

    output_max = float(np.max(np.abs(filtered_audio)))

    print(
        f"Output max amplitude: {output_max:.9f} "
        f"({amplitude_to_db(output_max):.3f} dB)"
    )

    output_path = output_dir / input_path.name

    print(f"Writing: {output_path}")

    sf.write(
        output_path,
        filtered_audio,
        sample_rate,
        subtype="PCM_24",
    )

    return input_max, output_max


def main():
    # ----- GUI: select raw audio directory -----

    root = tk.Tk()
    root.withdraw()

    raw_dir = filedialog.askdirectory(
        title="Select the RAW AUDIO folder (e.g. .../audio/raw)"
    )

    if not raw_dir:
        raise SystemExit("No raw audio folder selected. Exiting.")

    raw_dir = Path(raw_dir).resolve()

    # ----- GUI: select filter file -----

    filter_path = filedialog.askopenfilename(
        title="Select the MATLAB .mat filter file",
        filetypes=[
            ("MATLAB filter files", "*.mat"),
            ("All files", "*.*"),
        ],
    )

    if not filter_path:
        raise SystemExit("No filter file selected. Exiting.")

    filter_path = Path(filter_path).resolve()

    # ----- Derive output directory relative to raw_dir -----

    if not raw_dir.is_dir():
        raise FileNotFoundError(
            f"Raw audio directory not found: {raw_dir}"
        )

    if not filter_path.is_file():
        raise FileNotFoundError(
            f"Filter file not found: {filter_path}"
        )

    filter_name_no_ext = filter_path.stem

    filter_base_dir = raw_dir.parent / "filter"
    output_dir = filter_base_dir / filter_name_no_ext

    print(f"Raw audio directory: {raw_dir}")
    print(f"Filter file: {filter_path}")
    print(f"Output directory: {output_dir}")

    # ----- Load filter -----

    print(f"\nLoading filter: {filter_path}")

    filter_kernel = load_mat_filter(filter_path)

    print(f"Filter shape: {filter_kernel.shape}")

    if filter_kernel.shape[1] != 2:
        raise ValueError(
            "The filter must contain two stereo channels."
        )

    # ----- Find all WAV files in raw_dir -----

    wav_files = sorted(raw_dir.glob("*.wav"))

    if not wav_files:
        raise FileNotFoundError(
            f"No .wav files found in {raw_dir}"
        )

    print(f"\nFound {len(wav_files)} WAV file(s) to process.")

    # ----- Additional gain in dB (0 = no change) -----

    gain_db = 0.0

    # ----- Process each file -----

    input_global_max = 0.0
    output_global_max = 0.0

    for input_file in wav_files:
        input_max, output_max = process_file(
            input_file,
            output_dir,
            filter_kernel,
            gain_db,
        )

        input_global_max = max(input_global_max, input_max)
        output_global_max = max(output_global_max, output_max)

    print("\nFinished normally.")
    print("Summary:")
    print(
        f"Input max amplitude: {input_global_max:.9f} "
        f"({amplitude_to_db(input_global_max):.3f} dB)"
    )
    print(
        f"Output max amplitude: {output_global_max:.9f} "
        f"({amplitude_to_db(output_global_max):.3f} dB)"
    )


if __name__ == "__main__":
    main()