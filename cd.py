import wave
from pathlib import Path

BASE_DIR = Path("modules")   # change if needed

def get_wav_duration(path):
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)

def main():

    wav_files = list(BASE_DIR.rglob("final_module.wav"))

    total_seconds = 0

    print(f"\nFound {len(wav_files)} modules\n")

    for wav_file in wav_files:

        duration = get_wav_duration(wav_file)
        total_seconds += duration

        minutes = duration / 60

        print(f"{wav_file}  ->  {minutes:.2f} mins")

    print("\n===============================")

    total_minutes = total_seconds / 60
    total_hours = total_minutes / 60

    print(f"Total Minutes : {total_minutes:.2f}")
    print(f"Total Hours   : {total_hours:.2f}")

if __name__ == "__main__":
    main()