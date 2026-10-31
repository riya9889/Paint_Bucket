"""Flask entry point: routes only. All logic lives in /core."""
import time

import cv2
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

import config
from core.bucket_catalog import BucketCatalog
from core.camera import Camera
from core.ocr_engine import OCREngine
from core.overlay import draw_detections
from core.verifier import Verifier

app = Flask(__name__)

catalog = BucketCatalog(config.IMAGES_DIR, config.ALLOWED_EXTENSIONS)
camera = Camera(config.CAMERA_INDEX, config.FRAME_WIDTH, config.FRAME_HEIGHT)
ocr = OCREngine(config.OCR_LANGUAGES, config.OCR_USE_GPU, config.OCR_MAX_WIDTH)
verifier = Verifier(camera, ocr, catalog)

ocr.load_async()  # start loading the model right away


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buckets")
def api_buckets():
    return jsonify([{"name": b.name, "filename": b.filename} for b in catalog.scan()])


@app.route("/bucket_image/<path:filename>")
def bucket_image(filename):
    known = {b.filename for b in catalog.scan()}
    if filename not in known:
        return ("Not found", 404)
    return send_from_directory(catalog.directory, filename)


@app.route("/api/start", methods=["POST"])
def api_start():
    target = (request.get_json(silent=True) or {}).get("target", "")
    if not catalog.get(target):
        return jsonify(ok=False, error="Please select a valid paint bucket."), 400
    if not camera.start():
        return jsonify(ok=False, error=camera.last_error), 500
    verifier.start(target)
    return jsonify(ok=True)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    verifier.stop()
    camera.stop()
    return jsonify(ok=True)


@app.route("/api/target", methods=["POST"])
def api_target():
    target = (request.get_json(silent=True) or {}).get("target", "")
    if not catalog.get(target):
        return jsonify(ok=False, error="Unknown bucket."), 400
    verifier.set_target(target)
    return jsonify(ok=True)


@app.route("/api/status")
def api_status():
    data = verifier.snapshot()
    data["camera_running"] = camera.is_running
    data["ocr_ready"] = ocr.ready
    return jsonify(data)


def _mjpeg():
    while camera.is_running:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.02)
            continue
        status = verifier.snapshot()["status"]
        frame = draw_detections(frame, verifier.get_detections(), status)
        ok, buf = cv2.imencode(".jpg", frame,
                               [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
        if ok:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.tobytes() + b"\r\n")
        time.sleep(0.033)


@app.route("/video_feed")
def video_feed():
    return Response(_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    # debug=False avoids the reloader loading the OCR model twice
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)