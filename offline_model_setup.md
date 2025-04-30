# Manual Model Caching for OmniDictate (Offline Setup)

This guide explains how to manually download and arrange model files in the Hugging Face cache directory. This allows programs like OmniDictate, which rely on the `huggingface_hub` library, to load models locally when automatic downloading fails (e.g., due to network issues, proxies, or firewalls).

**Use Case:** You need to run OmniDictate with a specific `faster-whisper` compatible model, but the application cannot download it automatically from the Hugging Face Hub.

**Prerequisites:**

*   **Model Identifier:** Know the Hugging Face repository ID of the model (e.g., `Systran/faster-whisper-medium.en`). It **must** be a model compatible with `faster-whisper` (using the CTranslate2 format).
*   **Git:** You need `git` installed to clone the repository. (Alternatively, you can manually download the required files via the website).
*   **Cache Location:** Know where your Hugging Face cache is located.
    *   Default Windows: `C:\Users\<YourUsername>\.cache\huggingface\hub`
    *   Default Linux/macOS: `/home/<YourUsername>/.cache/huggingface/hub` (or `~/.cache/huggingface/hub`)
    *   *(Note: This location can be changed by the `HF_HOME` or `HF_HUB_CACHE` environment variables)*.

# Basically, you must have a folder that looks like this:
```
C:\Users\Username\.cache\huggingface\hub\
└── models--Systran--faster-whisper-medium.en/
    ├── refs/
    │   └── main                # (Text file containing the commit hash for the 'main' branch reference)
    └── snapshots/
        └── a29b04bd15381511a9af671baec01072039215e3/  # (Folder named after the specific model commit hash)
            ├── config.json
            ├── model.bin
            ├── README.md
            ├── tokenizer.json
            └── vocabulary.txt
```

## Now let's make it happen:

**Steps:**

1.  **Download Model Files (to a Temporary Location):**
    *   Open a command prompt, terminal, or Git Bash.
    *   Clone the model repository into a **new, temporary folder** (e.g., `temporary_model_files`). **Do NOT clone directly into the cache.**
        ```bash
        # Replace with the actual model ID you need
        git clone https://huggingface.co/Systran/faster-whisper-medium.en temporary_model_files
        ```
    *   *(Alternative: Manually download essential files like `model.bin`, `config.json`, `tokenizer.json`, `vocabulary.txt` from the model's "Files and versions" tab on the Hugging Face website into your `temporary_model_files` folder).*

2.  **Find the Full Commit Hash:**
    *   Go to the model's page on the Hugging Face Hub website (e.g., `https://huggingface.co/Systran/faster-whisper-medium.en`).
    *   Click the **"Files and versions"** tab.
    *   Click the **"History"** or "**XXX commits**" link for the `main` branch (or the specific branch/tag you need).
    *   The latest commit will usually be at the top. Locate the **full 40-character commit hash**. There's often a copy icon next to it.
    *   **Copy this full hash.** (e.g., `a29b04bd15381511a9af671baec01072039215e3` - *this is just an example, find the current one for your model!*)

3.  **Create Cache Folders and `refs/main` File:**
    *   Navigate to your Hugging Face hub cache directory (see Prerequisites).
    *   Convert the model identifier (`Systran/faster-whisper-medium.en`) into the cache folder name format (`models--Vendor--ModelName`): `models--Systran--faster-whisper-medium.en`.
    *   Create this main model directory using File Explorer or the command line:
        ```bash
        # Navigate to your hub cache first, e.g., cd C:\Users\YourUser\.cache\huggingface\hub
        mkdir models--Systran--faster-whisper-medium.en
        cd models--Systran--faster-whisper-medium.en
        ```
    *   Create the `refs` folder:
        ```bash
        mkdir refs
        cd refs
        ```
    *   Create the `main` file (**no extension**):
        *   *Using File Explorer:* Right-click -> New -> Text Document. Name it `main.txt`, then rename it to `main` (confirm removing the `.txt` extension).
        *   *Using Command Prompt (Windows):* `echo. > main`
        *   *Using Terminal (Linux/macOS):* `touch main`
    *   Open the newly created `main` file with a text editor (like Notepad).
    *   Paste the **full commit hash** (from Step 2) into this file. Save and close.

4.  **Create Snapshot Directory:**
    *   Navigate back up to the main model cache folder (`models--Systran--fasfaster-whisper-medium.en`).
        ```bash
        # If you are inside refs, go up one level
        cd ..
        ```
    *   Create the `snapshots` directory:
        ```bash
        mkdir snapshots
        cd snapshots
        ```
    *   Create a directory named *exactly* like the full commit hash (from Step 2):
        ```bash
        # Use the actual hash you copied
        mkdir a29b04bd15381511a9af671baec01072039215e3
        ```

5.  **Move Essential Model Files into Snapshot Folder:**
    *   Open File Explorer.
    *   Go to the temporary folder where you downloaded the files in Step 1 (`temporary_model_files`).
    *   Select the essential model files:
        *   `model.bin`
        *   `config.json`
        *   `tokenizer.json`
        *   `vocabulary.txt`
        *   *(Include other files like `README.md` if they were present.
    *   **Cut** (Ctrl+X) these selected files. **Important: Do NOT** include the `.git` folder if you used `git clone`.
    *   Navigate to the commit hash folder you created inside `snapshots` in Step 4.
    *   **Paste** (Ctrl+V) the files into this commit hash folder.

6.  **Test in OmniDictate:**
    *   Clean up: You can now delete the temporary download folder (`temporary_model_files`) from Step 1.
    *   Open OmniDictate and go to its Settings.
    *   Select or type the identifier for the model you just cached (e.g., `medium.en`).
    *   Click "Start Dictation".

The application should now detect the correctly structured cache entry and load the model locally without needing an internet connection for this specific model.
