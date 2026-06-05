"""
Katalog Delova — Flask backend
Port 5050
"""
from flask import Flask, jsonify, render_template, request, abort
import scraper

app = Flask(__name__)

# ── Katalog API ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    resp = app.make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/api/makes")
def api_makes():
    try:
        return jsonify(scraper.get_makes())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/models")
def api_models():
    make_id = request.args.get("make_id", "").strip()
    if not make_id: abort(400)
    try:
        return jsonify(scraper.get_models(make_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/types")
def api_types():
    make_id  = request.args.get("make_id", "").strip()
    model_id = request.args.get("model_id", "").strip()
    if not make_id or not model_id: abort(400)
    try:
        return jsonify(scraper.get_car_types(make_id, model_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/categories")
def api_categories():
    vid = request.args.get("vid", "").strip()
    if not vid: abort(400)
    try:
        return jsonify(scraper.get_categories(vid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/parts")
def api_parts():
    vid    = request.args.get("vid", "").strip()
    cat_id = request.args.get("cat", "").strip()
    if not vid or not cat_id: abort(400)
    gaids = request.args.get("gaids", "")
    mfr   = request.args.get("mfr", "")
    model = request.args.get("model", "")
    vtype = request.args.get("vtype", "")
    try:
        return jsonify(scraper.get_parts(vid, cat_id, gaids, mfr, model, vtype))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/vin")
def api_vin():
    vin = request.args.get("vin", "").strip()
    if not vin: abort(400)
    try:
        result = scraper.search_by_vin(vin)
        return jsonify(result or {"vehicle_id": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    scraper.cache_clear()
    return jsonify({"ok": True})

# ── Partsouq proxy ─────────────────────────────────────────────────────────


if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
