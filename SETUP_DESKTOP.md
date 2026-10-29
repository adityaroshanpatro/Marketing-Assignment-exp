# Running this project in the Claude desktop app (Claude Code)

About 20 minutes, once per laptop. Each teammate does this on their own machine with
their own API keys.

## Step 1: Install the prerequisites (once)

| Tool | macOS | Windows |
| --- | --- | --- |
| Claude desktop app | claude.com/download, then sign in. The Code tab needs a Pro, Max, Team or Enterprise plan | Same |
| Git | Open Terminal and run `git --version`. If macOS offers to install developer tools, accept | Install from git-scm.com with the default options (this includes Git Credential Manager for GitHub sign-in) |
| Python 3.10 or newer | python.org/downloads, or `brew install python` | python.org/downloads. **Tick "Add python.exe to PATH"** on the first installer screen |
| GitHub CLI (makes sign-in easy) | `brew install gh` | cli.github.com |

Check that everything installed: open a new Terminal (macOS) or PowerShell (Windows) and run:

```bash
git --version
python3 --version     # Windows: python --version
gh --version
```

## Step 2: Sign in to GitHub and clone the repo

The repo is private, so sign in first:

```bash
gh auth login
```

Choose: GitHub.com → HTTPS → "Login with a web browser". Copy the one-time code, then
approve it in the browser. Then clone into a folder you'll remember, for example Documents:

```bash
cd ~/Documents            # Windows: cd $HOME\Documents
gh repo clone adityaroshanpatro/Marketing-Assignment-exp
```

You now have a folder `Documents/Marketing-Assignment-exp`.

Teammates: Aditya must first add you as a collaborator on GitHub (repo → Settings →
Collaborators → Add people). Accept the email invite, then do the steps above.

## Step 3: Add your API keys (by hand, never in the chat)

1. In Finder or File Explorer, open the `Marketing-Assignment-exp` folder.
2. Duplicate `.env.example` and rename the copy to `.env`.
   - macOS hides dot-files: press Cmd+Shift+. in Finder to show them. Or, in Terminal inside
     the folder, run `cp .env.example .env`.
   - Windows: in PowerShell inside the folder, run `copy .env.example .env`.
3. Open `.env` in a text editor (TextEdit in plain-text mode, Notepad, or VS Code). Paste the
   keys you have, with no quotes or spaces:
   ```
   OPENROUTER_API_KEY=sk-or-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```
4. Save. `.env` is git-ignored, so it stays on your laptop.

Where to get keys: openrouter.ai/keys (one key covers most models), console.anthropic.com,
platform.openai.com/api-keys, aistudio.google.com/apikey. Add a small credit (USD 5–10)
for the pilot.

## Step 4: Open the project in the Code tab

1. Open the Claude desktop app and click **Code** at the top of the left sidebar.
2. In the row under the prompt box, click the first control (the environment selector) and
   pick the top entry under **Local**.
3. Click the folder control next to it → **Open folder…** → select `Marketing-Assignment-exp`.
4. Pick a model in the model picker at the right end of that row.
5. Set the permission mode (same row) to **Manual** for the first session, so Claude asks
   before every command and file edit. Switch to "Accept edits" once you're comfortable.

Claude Code reads `CLAUDE.md` in the folder automatically. It knows what the study is and
which rules to follow.

## Step 5: First prompts (paste these one at a time)

**Prompt 1 (set up and verify, no API spend):**
> Create a Python virtual environment in .venv, install requirements.txt, then run the dry
> run with the mock config and show me the "planted weights" line from the analysis.

Expected result: "100% of planted weights fall inside the 95% CI" (or close to 95%).

**Prompt 2 (connect real models):**
> Help me fill the FILL_ME model strings in config/models.yaml for this pilot set: Claude
> Haiku, a GPT mini model, a Gemini Flash model and one open-weight model via OpenRouter.
> Look up the exact current model IDs on each provider's model list, enable only those
> four, then run `python run.py check`. Do not print my API keys.

Every line should say OK. If one fails, Claude will show you the error.

**Prompt 3 (pilot):**
> Generate the pilot tasks (--m3 60 --m1 20 --seed 101 into data/pilot/tasks.jsonl), run
> `estimate` and tell me the cost, then, after I confirm, run the pilot into
> data/pilot/runs_<myname>.jsonl and analyse it into results/pilot. Show me the parse
> rates and 3 raw responses per model.

**Prompt 4 (share results):**
> Commit data/pilot and results/pilot and push to GitHub. Check that .env is not staged first.

## Step 6: Working as a team

- Before starting each session: ask Claude to `git pull`, so you have your teammate's latest runs.
- Each person writes to their own run file (`runs_aditya.jsonl`, `runs_<teammate>.jsonl`).
- Only one person changes `design.py`, and only before the pilot ends (the design is frozen after).
- Combine everyone's runs at analysis time: `--runs data/main/runs_aditya.jsonl,data/main/runs_<teammate>.jsonl`.

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| Code tab asks to upgrade | It needs a paid plan (Pro or above) |
| `python` not found (Windows) | Re-run the Python installer, choose Modify, tick "Add to PATH"; reopen the app |
| `git clone` asks for a password | Use `gh auth login` and `gh repo clone` instead (GitHub no longer accepts passwords) |
| `check` says 401 / authentication error | Key typo in `.env`, or no credit on that provider account |
| `check` says model not found | Wrong model string: copy it exactly from the provider's model list |
| Many "unparsed" answers | Raise `max_tokens` for that model in config/models.yaml (reasoning models need 2000+) |
