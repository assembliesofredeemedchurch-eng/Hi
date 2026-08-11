import os
import re
import uuid
import shutil
import threading
import time

from flask import Flask, request, jsonify, send_file, render_template, after_this_request
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# How long a finished download is kept on disk before being swept, in seconds.
FILE_TTL = 60 * 30
# Reject wildly long-running extractions/downloads (seconds).
DOWNLOAD_TIMEOUT = 60 * 20

URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _cleanup_old_files():
    """Background sweep so a public deployment doesn't fill up disk."""
    while True:
        now = time.time()
        try:
            for name in os.listdir(DOWNLOAD_DIR):
                path = os.path.join(DOWNLOAD_DIR, name)
                if os.path.isdir(path) and now - os.path.getmtime(path) > FILE_TTL:
                    shutil.rmtree(path, ignore_errors=True)
        except FileNotFoundError:
            pass
        time.sleep(300)


threading.Thread(target=_cleanup_old_files, daemon=True).start()


def _validate_url(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return "Missing URL."
    url = url.strip()
    if not URL_RE.match(url):
        return "That doesn't look like a valid http(s) URL."
    if len(url) > 2048:
        return "URL is too long."
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    err = _validate_url(url)
    if err:
        return jsonify({"error": err}), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Couldn't read that URL: {e}"}), 422
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Unexpected error: {e}"}), 500

    return jsonify({
        "title": meta.get("title"),
        "thumbnail": meta.get("thumbnail"),
        "duration": meta.get("duration"),
        "uploader": meta.get("uploader"),
        "extractor": meta.get("extractor_key"),
    })


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    mode = data.get("mode", "video")  # "video" or "audio"

    err = _validate_url(url)
    if err:
        return jsonify({"error": err}), 400
    if mode not in ("video", "audio"):
        return jsonify({"error": "Invalid mode."}), 400

    job_id = uuid.uuid4().hex
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    outtmpl = os.path.join(job_dir, "%(title).150B.%(ext)s")

    if mode == "audio":
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Download failed: {e}"}), 422
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": f"Unexpected error: {e}"}), 500

    files = os.listdir(job_dir)
    if not files:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({"error": "No file was produced."}), 500

    result_path = os.path.join(job_dir, files[0])

    @after_this_request
    def _schedule_cleanup(response):
        # Individual job dirs are also swept by the background thread;
        # this is just a best-effort immediate cleanup after the response streams.
        return response

    return send_file(result_path, as_attachment=True, download_name=files[0])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
