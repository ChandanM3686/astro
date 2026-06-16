"""
Vedic Astrology AI — Flask Backend
=====================================
API endpoints for generating premium horoscope charts and AI-powered readings.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import traceback
import tempfile
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

from astro_engine import compute_full_chart
from prompt import build_report_prompt, build_question_prompt
from pdf_generator import generate_pdf_report

# ─────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Determine paths for serving frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the frontend index.html on the root path."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve other static files like css and js."""
    return send_from_directory(app.static_folder, path)

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "Vedic Astrology AI"})


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """Generate a specific premium Vedic horoscope report.

    Expects JSON body:
    {
        "name": "John Doe",
        "birth_date": "1990-08-15",
        "birth_time": "10:30",
        "place_of_birth": "Delhi",
        "gender": "male",
        "report_type": "free" | "complete" | "business" | "child" | "celebrity" | "gemstone" | "numerology" | "relationship"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        # Validate required fields
        required = ["name", "birth_date", "birth_time", "place_of_birth", "gender", "report_type"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        report_type = data["report_type"]

        # 1. Compute chart using astro engine
        chart_data = compute_full_chart(
            name=data["name"],
            birth_date=data["birth_date"],
            birth_time=data["birth_time"],
            place_of_birth=data["place_of_birth"],
            gender=data["gender"]
        )

        partner_chart = None
        target_celebrity = data.get("target_celebrity")

        if report_type == "relationship" and "partner" in data:
            p_data = data["partner"]
            if p_data.get("name") and p_data.get("birth_date") and p_data.get("birth_time") and p_data.get("place_of_birth"):
                partner_chart = compute_full_chart(
                    name=p_data["name"],
                    birth_date=p_data["birth_date"],
                    birth_time=p_data["birth_time"],
                    place_of_birth=p_data["place_of_birth"],
                    gender=p_data.get("gender", "other")
                )

        # 2. Build optimized prompt and send to GPT
        messages = build_report_prompt(chart_data, report_type, partner_chart, target_celebrity)
        
        # Determine tokens based on report type
        max_tokens = 500 if report_type == "free" else 1500

        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens
        )
        prediction = gpt_response.choices[0].message.content

        # 3. Return prediction and daily data
        return jsonify({
            "daily": chart_data.get("daily", {}),
            "prediction": prediction,
            "report_type": report_type
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Generate a premium Vedic horoscope PDF report.
    Expects the same JSON body as /generate_report.
    Returns a PDF file.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        required = ["name", "birth_date", "birth_time", "place_of_birth", "gender"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        report_type = data.get("report_type", "complete")

        chart_data = compute_full_chart(
            name=data["name"],
            birth_date=data["birth_date"],
            birth_time=data["birth_time"],
            place_of_birth=data["place_of_birth"],
            gender=data["gender"]
        )

        partner_chart = None
        target_celebrity = data.get("target_celebrity")

        if report_type == "relationship" and "partner" in data:
            p_data = data["partner"]
            if p_data.get("name") and p_data.get("birth_date") and p_data.get("birth_time") and p_data.get("place_of_birth"):
                partner_chart = compute_full_chart(
                    name=p_data["name"],
                    birth_date=p_data["birth_date"],
                    birth_time=p_data["birth_time"],
                    place_of_birth=p_data["place_of_birth"],
                    gender=p_data.get("gender", "other")
                )

        messages = build_report_prompt(chart_data, report_type, partner_chart, target_celebrity)
        max_tokens = 500 if report_type == "free" else 1500

        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens
        )
        prediction = gpt_response.choices[0].message.content

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"Horoscope_{data['name'].replace(' ', '_')}.pdf")
        
        generate_pdf_report(chart_data, prediction, filename=file_path)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"Horoscope_{data['name']}.pdf",
            mimetype='application/pdf'
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@app.route('/ask', methods=['POST'])
def ask():
    """Answer a specific astrology question based on the user's chart."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        required = ["name", "birth_date", "birth_time", "place_of_birth", "gender", "question"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        chart_data = compute_full_chart(
            name=data["name"],
            birth_date=data["birth_date"],
            birth_time=data["birth_time"],
            place_of_birth=data["place_of_birth"],
            gender=data["gender"]
        )

        messages = build_question_prompt(chart_data, data["question"])
        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )
        answer = gpt_response.choices[0].message.content

        return jsonify({
            "question": data["question"],
            "answer": answer,
            "current_dasha": chart_data["dasha"]["current"],
            "daily": chart_data["daily"]
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("Vedic Astrology AI Server starting...")
    print("   Endpoints:")
    print("   GET  /                    - Frontend UI")
    print("   GET  /health              - Health check")
    print("   POST /generate_report     - Generates specific reports")
    print("   POST /generate_pdf        - Generates premium PDF reports")
    print("   POST /ask                 - Answer specific question")
    print()
    app.run(debug=True, port=5002)