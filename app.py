# -*- coding: utf-8 -*-
import os, json
from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

# ==========================================================
# 🧿 Amulet Backend v2.9 — Flask Edition (Render-ready)
# ==========================================================
load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///amulet.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'amulet-secret')
db = SQLAlchemy(app)

# ==========================================================
# MODELS
# ==========================================================
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    mac_id = db.Column(db.String(255))
    credit = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), default='active')

class Voice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    voice_id = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(50), default='1.0.0')
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.Text, default='')
    update_description = db.Column(db.Text, default='')
    update_links = db.Column(db.Text, default='')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer)
    action = db.Column(db.String(50))
    char_count = db.Column(db.Integer, default=0)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================================
# INIT DB
# ==========================================================
with app.app_context():
    db.create_all()
    if Config.query.first() is None:
        db.session.add(Config(update_description="Initial config"))
        db.session.commit()

# ==========================================================
# API (для клієнтів)
# ==========================================================
@app.route("/api", methods=["POST"])
def api_main():
    req = request.get_json(force=True, silent=True) or {}
    action = (req.get("action") or "").strip()

    mapping = {
        "check": api_check,
        "debit": api_debit,
        "refund": api_refund,
        "next_api_key": api_next_api_key,
        "release_api_key": lambda r: jsonify({"ok": True}),
        "deactivate_api_key": api_deactivate_api_key,
        "get_voices": api_get_voices,
        "get_config": api_get_config
    }

    if action not in mapping:
        return jsonify({"ok": False, "msg": "Unknown action"}), 400

    try:
        return mapping[action](req)
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


def api_check(req):
    key, mac = req.get("key","").strip(), req.get("mac","").strip()
    if not key or not mac:
        return jsonify({"ok": False, "msg": "key/mac required"})
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "msg": "License not found"})
    if not lic.active:
        return jsonify({"ok": False, "msg": "License inactive"})
    if not lic.mac_id:
        lic.mac_id = mac
        db.session.commit()
        return jsonify({"ok": True, "credit": lic.credit})
    if lic.mac_id != mac:
        return jsonify({"ok": False, "msg": "License activated on another device"})
    return jsonify({"ok": True, "credit": lic.credit})


def api_debit(req):
    key, mac, count = req.get("key","").strip(), req.get("mac","").strip(), int(req.get("count") or 0)
    model = req.get("model","")
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "msg": "License not found"})
    if lic.mac_id != mac:
        return jsonify({"ok": False, "msg": "MAC mismatch"})
    if lic.credit < count:
        return jsonify({"ok": False, "msg": "Insufficient credit", "credit": lic.credit})
    lic.credit -= count
    db.session.add(ActivityLog(license_id=lic.id, action="debit", char_count=count, details=f"model={model}"))
    db.session.commit()
    return jsonify({"ok": True, "debited": count, "credit": lic.credit})


def api_refund(req):
    key, mac, count = req.get("key","").strip(), req.get("mac","").strip(), int(req.get("count") or 0)
    reason, model = req.get("reason",""), req.get("model","")
    lic = License.query.filter_by(key=key).first()
    if not lic:
        return jsonify({"ok": False, "msg": "License not found"})
    if lic.mac_id != mac:
        return jsonify({"ok": False, "msg": "MAC mismatch"})
    lic.credit += count
    db.session.add(ActivityLog(license_id=lic.id, action="refund", char_count=count, details=f"model={model}, reason={reason}"))
    db.session.commit()
    return jsonify({"ok": True, "refunded": count, "credit": lic.credit})


def api_next_api_key(_):
    k = ApiKey.query.filter_by(status="active").first()
    if not k:
        return jsonify({"ok": False, "msg": "No active API keys"})
    return jsonify({"ok": True, "api_key": k.api_key})


def api_deactivate_api_key(req):
    key = req.get("api_key")
    k = ApiKey.query.filter_by(api_key=key).first()
    if not k:
        return jsonify({"ok": False, "msg": "API key not found"})
    k.status = "inactive"
    db.session.commit()
    return jsonify({"ok": True, "status": "inactive"})


def api_get_voices(_=None):
    return jsonify({"ok": True, "voices": [
        {"Назва голосу": v.name, "ID ГОЛОСУ": v.voice_id}
        for v in Voice.query.filter_by(active=True)
    ]})


def api_get_config(_=None):
    c = Config.query.first()
    return jsonify({
        "ok": True,
        "config": {
            "latest_version": c.latest_version,
            "force_update": c.force_update,
            "maintenance": c.maintenance,
            "maintenance_message": c.maintenance_message,
            "update_description": c.update_description,
            "update_links": json.loads(c.update_links or "[]")
        }
    })


# ==========================================================
# ADMIN API
# ==========================================================
@app.route("/admin_api/licenses", methods=["GET","POST"])
def admin_licenses():
    if request.method == "GET":
        q = (request.args.get("q") or "").strip()
        query = License.query
        if q:
            query = query.filter(License.key.ilike(f"%{q}%"))
        items = query.order_by(License.id.desc()).all()
        return jsonify([{
            "id":x.id,"key":x.key,"mac_id":x.mac_id,"credit":x.credit,"active":x.active,
            "created_at":x.created_at.isoformat() if x.created_at else ""
        } for x in items])
    d = request.get_json(force=True)
    lic = License(key=d["key"], mac_id=d.get("mac_id"), credit=d.get("credit",0), active=d.get("active",True))
    db.session.add(lic)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/licenses/<int:lid>", methods=["PUT","DELETE"])
def admin_license_edit(lid):
    lic = License.query.get(lid)
    if not lic: return jsonify({"ok": False}), 404
    if request.method == "DELETE":
        db.session.delete(lic)
        db.session.commit()
        return jsonify({"ok": True})
    d = request.get_json(force=True)
    for k in ["key","mac_id","credit","active"]:
        if k in d: setattr(lic, k, d[k])
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/licenses/filter", methods=["GET"])
def admin_filter_licenses():
    min_credit=request.args.get("min_credit",type=int)
    max_credit=request.args.get("max_credit",type=int)
    active=request.args.get("active")
    q=License.query
    if min_credit is not None: q=q.filter(License.credit>=min_credit)
    if max_credit is not None: q=q.filter(License.credit<=max_credit)
    if active in("true","false"): q=q.filter(License.active==(active=="true"))
    res=q.all()
    return jsonify([{"id":x.id,"key":x.key,"credit":x.credit,"active":x.active,"mac_id":x.mac_id} for x in res])

# ---------- API KEYS ----------
@app.route("/admin_api/apikeys", methods=["GET","POST"])
def admin_keys():
    if request.method=="GET":
        return jsonify([{"id":x.id,"api_key":x.api_key,"status":x.status} for x in ApiKey.query.all()])
    d=request.get_json(force=True)
    k=ApiKey(api_key=d["api_key"],status=d.get("status","active"))
    db.session.add(k); db.session.commit(); return jsonify({"ok":True})

@app.route("/admin_api/apikeys/<int:id>", methods=["DELETE"])
def admin_del_key(id):
    k=ApiKey.query.get(id)
    if not k:return jsonify({"ok":False}),404
    db.session.delete(k);db.session.commit();return jsonify({"ok":True})

# ---------- VOICES ----------
@app.route("/admin_api/voices", methods=["GET","POST"])
def admin_voices():
    if request.method=="GET":
        return jsonify([{"id":x.id,"name":x.name,"voice_id":x.voice_id,"active":x.active} for x in Voice.query.all()])
    d=request.get_json(force=True)
    name, vid = d.get("name"), d.get("voice_id")
    if not name or not vid: return jsonify({"ok":False,"msg":"Invalid data"})
    if Voice.query.filter_by(voice_id=vid).first():
        return jsonify({"ok":False,"msg":"Voice already exists"})
    v=Voice(name=name,voice_id=vid,active=d.get("active",True))
    db.session.add(v);db.session.commit();return jsonify({"ok":True})

@app.route("/admin_api/voices/bulk", methods=["POST"])
def admin_bulk_voices():
    d=request.get_json(force=True)
    voices=d.get("voices",[])
    added=0
    for v in voices:
        name=v.get("name"); vid=v.get("voice_id")
        if name and vid and not Voice.query.filter_by(voice_id=vid).first():
            db.session.add(Voice(name=name,voice_id=vid,active=True)); added+=1
    db.session.commit()
    return jsonify({"ok":True,"added":added})

@app.route("/admin_api/voices/<int:vid>", methods=["DELETE"])
def admin_delete_voice(vid):
    v=Voice.query.get(vid)
    if not v:return jsonify({"ok":False}),404
    db.session.delete(v);db.session.commit();return jsonify({"ok":True})

@app.route("/admin_api/voices/delete_all", methods=["DELETE"])
def admin_delete_all_voices():
    Voice.query.delete();db.session.commit()
    return jsonify({"ok":True,"msg":"All voices deleted"})

# ---------- LOGS ----------
@app.route("/admin_api/logs")
def admin_logs():
    logs=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(200).all()
    return jsonify([{"id":x.id,"license_id":x.license_id,"action":x.action,"char_count":x.char_count,"details":x.details,"created_at":x.created_at.isoformat()} for x in logs])

# ---------- CONFIG ----------
@app.route("/admin_api/config", methods=["GET","PUT"])
def admin_config():
    c=Config.query.first()
    if request.method=="GET":
        return jsonify({"latest_version":c.latest_version,"force_update":c.force_update,"maintenance":c.maintenance,
                        "maintenance_message":c.maintenance_message,"update_description":c.update_description,
                        "update_links":c.update_links})
    d=request.get_json(force=True)
    for k,v in d.items(): setattr(c,k,v)
    db.session.commit();return jsonify({"ok":True})

# ---------- BACKUPS ----------
@app.route("/admin_api/backup", methods=["GET"])
def admin_backup():
    data={"licenses":[{"key":x.key,"credit":x.credit} for x in License.query.all()]}
    buf=BytesIO(json.dumps(data,indent=2,ensure_ascii=False).encode())
    return send_file(buf,mimetype="application/json",as_attachment=True,download_name="amulet_backup.json")

@app.route("/admin_api/backup/users", methods=["GET"])
def admin_backup_users():
    data={"licenses":[{"key":x.key,"mac_id":x.mac_id,"credit":x.credit,"active":x.active} for x in License.query.all()]}
    buf=BytesIO(json.dumps(data,indent=2,ensure_ascii=False).encode())
    return send_file(buf,mimetype="application/json",as_attachment=True,download_name="users_backup.json")

# ==========================================================
# STATIC UI
# ==========================================================
@app.route("/")
@app.route("/admin")
def admin_page():
    return send_from_directory('static', 'admin.html')

@app.route("/<path:p>")
def static_files(p):
    return send_from_directory('static', p)

# ==========================================================
# RUN (for local)
# ==========================================================
if __name__ == "__main__":
    app.run(port=3030, debug=True)