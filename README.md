# tocolab

Push code to Google Colab from the command line. One command, and your script is running in a Colab notebook with GPU. Pull results back when it's done.

```bash
cat train.py | tocolab --gpu
# ... run in Colab ...
tocolab pull --last
```

## Install

```bash
uv tool install tocolab
# or
pipx install tocolab
```

## Setup

tocolab uses the Google Drive API to upload notebooks. You need to create OAuth credentials once.

### 1. Create a Google Cloud project

- Go to [console.cloud.google.com](https://console.cloud.google.com/)
- Click **Select a project** > **New Project**
- Name it anything (e.g. "tocolab") and create it

### 2. Enable the Google Drive API

- In your project, go to **APIs & Services** > **Library**
- Search for **Google Drive API**
- Click **Enable**

### 3. Create OAuth credentials

- Go to **APIs & Services** > **Credentials**
- Click **Create Credentials** > **OAuth client ID**
- If prompted, configure the consent screen first (External, fill in app name, your email, skip scopes)
- Application type: **Desktop app**
- Name it anything
- Click **Create**, then **Download JSON**

### 4. Place the credentials file

Save the downloaded JSON as:

```
~/.config/tocolab/credentials.json
```

On Windows: `%USERPROFILE%\.config\tocolab\credentials.json`

### 5. Authenticate

```bash
tocolab auth
```

This opens your browser for Google sign-in. Token is saved locally and refreshes automatically.

## Usage

```bash
# Push a Python file — opens Colab in your browser
tocolab script.py

# Pipe from stdin
cat script.py | tocolab

# Set GPU runtime
tocolab train.py --gpu

# Set TPU runtime
tocolab train.py --tpu

# Custom notebook title
tocolab script.py --name "My Experiment"

# Upload to a specific Drive folder
tocolab script.py --folder "ML Experiments"

# Don't open browser, just print the URL
tocolab script.py --no-open

# Copy URL to clipboard
tocolab script.py --copy

# Upload an existing .ipynb
tocolab notebook.ipynb

# Combine flags
tocolab train.py --gpu --name "ResNet Training" --folder "Experiments" --no-open
```

### Pulling results

After running a notebook in Colab, pull the executed output back to your terminal:

```bash
# Pull the last pushed notebook
tocolab pull --last

# Pull by Colab URL
tocolab pull https://colab.research.google.com/drive/1AbCdEf...

# Pull by file ID
tocolab pull 1AbCdEfGhIjKlMnOp

# Save the executed notebook locally
tocolab pull --last --save output.ipynb

# Print raw notebook JSON
tocolab pull --last --raw
```

Output looks like:

```
--- In [1] ---
print(42)

--- Out [1] ---
42
```

Markdown cells are skipped. Images show `[image output]`. ANSI codes from tracebacks are stripped.

## Features

- **Auto cell splitting** — Uses `# %%` or `# In[]` markers to split your script into notebook cells
- **Auto dependency detection** — Scans imports, generates a `!pip install` setup cell for third-party packages
- **ipynb passthrough** — `.ipynb` files are uploaded directly with optional metadata updates
- **Pull results** — Download executed notebooks and view outputs in your terminal
- **Clean piping** — URLs and status go to stderr, so stdout stays clean for scripting

## Options

```
Arguments:
  [SOURCE]              File path (.py or .ipynb), or omit to read from stdin

Options:
  --name, -n TEXT       Notebook title
  --gpu                 Set Colab runtime to GPU
  --tpu                 Set Colab runtime to TPU
  --folder, -f TEXT     Drive folder name to upload into
  --no-open             Don't open browser, just print URL
  --copy, -c            Copy URL to clipboard
  --verbose, -v         Show full error traces
  --help                Show this message and exit

Subcommands:
  tocolab pull          Download executed notebook and display results
  tocolab auth          Re-run authentication flow

Pull options:
  [SOURCE]              Colab URL or Drive file ID
  --last                Pull the most recently pushed notebook
  --save PATH           Save executed notebook to a local file
  --raw                 Print raw notebook JSON
  --verbose, -v         Show full error traces
```

## How it works

**Push:**
1. Reads your Python source (from file or stdin)
2. Converts it to a valid `.ipynb` notebook using `nbformat`
3. Detects third-party imports and adds a pip install cell
4. Uploads to Google Drive via the Drive API (scope: `drive.file` — only files tocolab creates)
5. Opens `https://colab.research.google.com/drive/{file_id}` in your browser

**Pull:**
1. Downloads the notebook from Google Drive
2. Parses cell outputs (stream, execute_result, error, display_data)
3. Renders code inputs and outputs to the terminal

**Note:** The `drive.file` OAuth scope only accesses files tocolab created. You can only pull notebooks you pushed with tocolab.

## License

MIT

## Author

Aur Shalev Merin
