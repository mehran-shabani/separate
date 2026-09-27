# v to t

Local Python tools for speech transcription, audio cleanup, and speaker separation.

## Transcript app

Double-click `Transcript/start.cmd` to launch the local browser interface. Allow microphone access, speak, then stop recording to finish transcription. You can also upload audio, edit the result, and export a TXT file.

See [Transcript documentation](Transcript/README.md) for the Persian usage guide.

The app uses the existing project environment at `.venv` and the existing model at `.models/faster-whisper-large-v3-turbo`. It runs on CPU, processes audio locally, and does not download a new model.

## Audio tools

The root Python scripts extract, separate, clean, transcribe, and report on audio. `requirements-lock.txt` records the project's Python dependencies. Generated results are stored in `output`.

## Repository contents

Source code and documentation are versioned. Local environments, model weights, recordings, exports, temporary files, and secrets are excluded by `.gitignore` and remain on this computer. A fresh clone needs its own Python environment and local models before the app can run.
