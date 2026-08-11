# pull — a small web front end for yt-dlp

A single-page app: paste a URL, choose video or audio, get a file. Backend is
Flask calling the `yt-dlp` Python library directly (no shelling out), frontend
is plain HTML/CSS/JS.

## Local run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You also need **ffmpeg** on the machine (yt-dlp uses it to merge video+audio
streams and to extract mp3 audio):

```bash
# Debian/Ubuntu
sudo apt install ffmpeg
# macOS
brew install ffmpeg
```

Then:

```bash
python app.py
```

Visit `http://localhost:5000`.

## Deploying for others

Run it behind a real WSGI server, not the Flask dev server:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 --timeout 300 app:app
```

Put a reverse proxy (nginx / Caddy) in front for TLS. A few things worth
doing before you open this up publicly:

- **Rate-limit it.** One person queuing 50 downloads at once will peg the
  box. A reverse-proxy rate limit or something like `flask-limiter` is enough
  to start.
- **Cap concurrency / disk.** `app.py` already sweeps finished downloads
  after 30 minutes (`FILE_TTL` in `app.py`), but on a small box you'll still
  want a disk quota or periodic `df` check.
- **Auth, if it's not meant to be public.** There's none built in — anyone
  who can reach the server can use it as-is.
- **Legal responsibility is on whoever runs the server and whoever uses it.**
  yt-dlp itself is just a general-purpose media downloader; whether a given
  download is okay depends on the source site's terms and the copyright
  status of the content. Worth a line on the page (already there in the
  footer) and worth thinking about before deploying somewhere public.

## Structure

```
app.py                 Flask app: /, /api/info, /api/download
templates/index.html   page markup
static/style.css       styling
static/script.js       form handling, status log, result card
downloads/             scratch space for in-progress + finished files (gitignored)
```

## Extending it

- Swap the mp3/mp4 defaults in `app.py`'s `ydl_opts` for format selection if
  you want quality options exposed in the UI.
- `noplaylist: True` is set everywhere — drop it if you want playlist
  support, but then you'll want a progress/queue UI, not just a spinner.
