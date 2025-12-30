#!/usr/bin/env python3
"""Simple server to view photo scores with images (converts HEIC to JPEG)."""

import http.server
import json
import os
import socketserver
import webbrowser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

# Register HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("Warning: pillow-heif not installed, HEIC files won't work")

PORT = 8080
PHOTOS_DIR = "test_photos"
CSV_FILE = "test_photos_results.csv"

# Cache converted images
image_cache = {}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo Score Viewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 { text-align: center; margin-bottom: 10px; color: #fff; }
        .controls {
            text-align: center;
            margin-bottom: 20px;
        }
        .controls select, .controls button {
            background: #16213e;
            border: 1px solid #0f3460;
            color: #eee;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            margin: 5px;
        }
        .controls button:hover { background: #0f3460; }
        .stats { text-align: center; margin-bottom: 20px; color: #888; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-5px); }
        .card img {
            width: 100%;
            height: 300px;
            object-fit: cover;
            cursor: pointer;
            background: #0f3460;
        }
        .card-content { padding: 15px; }
        .filename {
            font-weight: bold;
            font-size: 14px;
            color: #aaa;
            margin-bottom: 10px;
            word-break: break-all;
        }
        .score-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        .score { font-size: 36px; font-weight: bold; }
        .score.excellent { color: #4ade80; }
        .score.strong { color: #a3e635; }
        .score.competent { color: #facc15; }
        .score.tourist { color: #fb923c; }
        .score.flawed { color: #f87171; }
        .score-label {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .score-label.excellent { background: #166534; }
        .score-label.strong { background: #3f6212; }
        .score-label.competent { background: #713f12; }
        .score-label.tourist { background: #9a3412; }
        .score-label.flawed { background: #991b1b; }
        .metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        .metric {
            background: #0f3460;
            padding: 10px;
            border-radius: 8px;
        }
        .metric-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .metric-value { font-size: 18px; font-weight: bold; }
        .metric-bar {
            height: 4px;
            background: #1a1a2e;
            border-radius: 2px;
            margin-top: 5px;
            overflow: hidden;
        }
        .metric-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #e94560, #0f3460);
            border-radius: 2px;
        }
        .description {
            font-size: 14px;
            color: #ccc;
            margin-bottom: 10px;
            line-height: 1.5;
        }
        .tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 15px; }
        .tag {
            background: #0f3460;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            color: #aaa;
        }
        .location { font-size: 13px; color: #e94560; margin-bottom: 10px; }
        .expandable {
            background: #0f3460;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .expandable-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            cursor: pointer;
            user-select: none;
        }
        .expandable-header:hover { background: rgba(255,255,255,0.05); }
        .expandable-title {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            font-weight: 600;
        }
        .expandable-toggle {
            font-size: 12px;
            color: #e94560;
            transition: transform 0.2s;
        }
        .expandable.open .expandable-toggle { transform: rotate(180deg); }
        .expandable-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .expandable.open .expandable-content {
            max-height: 2000px;
        }
        .explanation {
            padding: 0 12px 12px 12px;
            font-size: 14px;
            line-height: 1.6;
            color: #ccc;
        }
        .explanation p { margin-bottom: 12px; }
        .explanation strong { color: #e94560; }
        .explanation-summary {
            padding: 12px;
            font-size: 14px;
            line-height: 1.5;
            color: #ccc;
            border-left: 3px solid #e94560;
            background: rgba(233, 69, 96, 0.1);
            margin: 0 12px 12px 12px;
            border-radius: 0 8px 8px 0;
        }
        .improvements {
            background: #1a1a2e;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .improvements-content {
            padding: 0 12px 12px 12px;
        }
        .improvement-item {
            font-size: 13px;
            color: #aaa;
            padding: 10px 12px;
            border-bottom: 1px solid #16213e;
            line-height: 1.5;
            background: #0f3460;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .improvement-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        .improvement-item strong { color: #4ade80; }
        .cost-badge {
            display: inline-block;
            background: #0f3460;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            color: #4ade80;
            margin-left: 10px;
        }
        .correction-form {
            background: #0f3460;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        .correction-form h4 {
            font-size: 12px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .form-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: center;
        }
        .form-row label { font-size: 12px; color: #aaa; width: 100px; }
        .form-row input[type="range"] { flex: 1; accent-color: #e94560; }
        .form-row input[type="number"] {
            width: 60px;
            background: #1a1a2e;
            border: 1px solid #16213e;
            color: #eee;
            padding: 5px;
            border-radius: 4px;
            text-align: center;
        }
        .form-row textarea {
            flex: 1;
            background: #1a1a2e;
            border: 1px solid #16213e;
            color: #eee;
            padding: 8px;
            border-radius: 4px;
            resize: vertical;
            min-height: 60px;
        }
        .btn-save {
            background: #e94560;
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            width: 100%;
            margin-top: 10px;
        }
        .btn-save:hover { background: #c73e54; }
        .btn-save.saved { background: #4ade80; }
        .lightbox {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .lightbox.active { display: flex; }
        .lightbox img { max-width: 95%; max-height: 95%; object-fit: contain; }
        .lightbox-close {
            position: absolute;
            top: 20px; right: 30px;
            font-size: 40px;
            color: white;
            cursor: pointer;
        }
        .export-section {
            text-align: center;
            margin: 30px auto;
            padding: 20px;
            background: #16213e;
            border-radius: 12px;
            max-width: 800px;
        }
        .corrections-count { color: #4ade80; font-size: 18px; margin-bottom: 10px; }
        .model-scores { font-size: 11px; color: #666; margin-top: 10px; }
        .model-scores span { margin-right: 10px; }
    </style>
</head>
<body>
    <h1>Photo Score Viewer</h1>
    <div class="controls">
        <select id="sortBy" onchange="renderPhotos()">
            <option value="score_desc">Score (High to Low)</option>
            <option value="score_asc">Score (Low to High)</option>
            <option value="name">Filename</option>
            <option value="aesthetic">Aesthetic Score</option>
            <option value="technical">Technical Score</option>
        </select>
    </div>
    <div class="stats" id="stats"></div>
    <div class="grid" id="photoGrid"></div>
    <div class="export-section">
        <div class="corrections-count" id="correctionsCount">0 corrections made</div>
        <button class="btn-save" onclick="exportCorrections()">Export Corrections as JSON</button>
        <button class="btn-save" style="background:#0f3460;margin-top:10px" onclick="exportCSV()">Export Updated CSV</button>
    </div>
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img id="lightboxImg" src="">
    </div>

    <script>
        const photos = PHOTOS_DATA;
        let corrections = {};

        function formatExplanation(text) {
            if (!text) return '';
            // Convert markdown-style formatting to HTML
            return text
                // Convert **bold** to <strong>
                .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
                // Convert newlines to paragraphs
                .split('\\n\\n')
                .map(p => p.trim())
                .filter(p => p)
                .map(p => `<p>${p}</p>`)
                .join('');
        }

        function formatImprovement(text) {
            if (!text) return '';
            // Convert **bold** to <strong>
            return text.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
        }

        function getScoreClass(score) {
            if (score >= 85) return 'excellent';
            if (score >= 70) return 'strong';
            if (score >= 50) return 'competent';
            if (score >= 30) return 'tourist';
            return 'flawed';
        }

        function getScoreLabel(score) {
            if (score >= 85) return 'Excellent';
            if (score >= 70) return 'Strong';
            if (score >= 50) return 'Competent';
            if (score >= 30) return 'Tourist';
            return 'Flawed';
        }

        function renderPhotos() {
            const sortBy = document.getElementById('sortBy').value;
            let sorted = [...photos];

            switch(sortBy) {
                case 'score_desc':
                    sorted.sort((a, b) => b.final_score - a.final_score);
                    break;
                case 'score_asc':
                    sorted.sort((a, b) => a.final_score - b.final_score);
                    break;
                case 'name':
                    sorted.sort((a, b) => a.image_path.localeCompare(b.image_path));
                    break;
                case 'aesthetic':
                    sorted.sort((a, b) => b.aesthetic_score - a.aesthetic_score);
                    break;
                case 'technical':
                    sorted.sort((a, b) => b.technical_score - a.technical_score);
                    break;
            }

            const scores = photos.map(p => p.final_score);
            const avg = (scores.reduce((a,b) => a+b, 0) / scores.length).toFixed(1);
            const min = Math.min(...scores).toFixed(1);
            const max = Math.max(...scores).toFixed(1);
            document.getElementById('stats').innerHTML = `${photos.length} photos | Avg: ${avg} | Range: ${min} - ${max}`;

            const grid = document.getElementById('photoGrid');
            grid.innerHTML = sorted.map((photo) => {
                const score = photo.final_score;
                const scoreClass = getScoreClass(score);
                const aesthetic = photo.aesthetic_score || 0;
                const technical = photo.technical_score || 0;
                const correction = corrections[photo.image_path] || {};

                let features = {};
                try { if (photo.features_json) features = JSON.parse(photo.features_json); } catch(e) {}

                return `
                    <div class="card">
                        <img src="/photos/${encodeURIComponent(photo.image_path)}" alt="${photo.image_path}"
                             onclick="openLightbox('/photos/${encodeURIComponent(photo.image_path)}')"
                             loading="lazy">
                        <div class="card-content">
                            <div class="filename">${photo.image_path}</div>
                            <div class="score-row">
                                <div class="score ${scoreClass}">${score.toFixed(1)}</div>
                                <span class="score-label ${scoreClass}">${getScoreLabel(score)}</span>
                            </div>
                            <div class="metrics">
                                <div class="metric">
                                    <div class="metric-label">Aesthetic</div>
                                    <div class="metric-value">${(aesthetic * 100).toFixed(0)}%</div>
                                    <div class="metric-bar"><div class="metric-bar-fill" style="width:${aesthetic * 100}%"></div></div>
                                </div>
                                <div class="metric">
                                    <div class="metric-label">Technical</div>
                                    <div class="metric-value">${(technical * 100).toFixed(0)}%</div>
                                    <div class="metric-bar"><div class="metric-bar-fill" style="width:${technical * 100}%"></div></div>
                                </div>
                            </div>
                            ${photo.description ? `<div class="description">${photo.description}</div>` : ''}
                            <div class="tags">
                                ${photo.scene_type ? `<span class="tag">${photo.scene_type}</span>` : ''}
                                ${photo.lighting ? `<span class="tag">${photo.lighting}</span>` : ''}
                                ${photo.subject_position ? `<span class="tag">${photo.subject_position}</span>` : ''}
                                ${features.color_palette ? `<span class="tag">${features.color_palette}</span>` : ''}
                            </div>
                            ${photo.location_name ? `<div class="location">📍 ${photo.location_name}${photo.location_country ? ', ' + photo.location_country : ''}</div>` : ''}
                            <div class="score-row" style="margin-bottom:10px">
                                <span class="cost-badge">💰 ~$0.015 LLM cost</span>
                            </div>
                            ${photo.explanation ? `
                                <div class="expandable open" onclick="this.classList.toggle('open')">
                                    <div class="expandable-header">
                                        <span class="expandable-title">📝 Critique</span>
                                        <span class="expandable-toggle">▼</span>
                                    </div>
                                    <div class="expandable-content">
                                        <div class="explanation">${formatExplanation(photo.explanation)}</div>
                                    </div>
                                </div>
                            ` : ''}
                            ${photo.improvements ? `
                                <div class="expandable" onclick="this.classList.toggle('open')">
                                    <div class="expandable-header">
                                        <span class="expandable-title">💡 How to Improve</span>
                                        <span class="expandable-toggle">▼</span>
                                    </div>
                                    <div class="expandable-content">
                                        <div class="improvements-content">
                                            ${photo.improvements.split(' | ').map(imp => `<div class="improvement-item">${formatImprovement(imp)}</div>`).join('')}
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                            <div class="model-scores">
                                ${photo.qwen_aesthetic ? `<span>Qwen: ${photo.qwen_aesthetic}</span>` : ''}
                                ${photo.gpt4o_aesthetic ? `<span>GPT: ${photo.gpt4o_aesthetic}</span>` : ''}
                                ${photo.gemini_aesthetic ? `<span>Gemini: ${photo.gemini_aesthetic}</span>` : ''}
                            </div>
                            <div class="correction-form">
                                <h4>Your Assessment</h4>
                                <div class="form-row">
                                    <label>Score (0-100)</label>
                                    <input type="range" min="0" max="100" value="${correction.score ?? Math.round(score)}"
                                           oninput="this.nextElementSibling.value=this.value"
                                           onchange="updateCorrection('${photo.image_path}', 'score', this.value)">
                                    <input type="number" min="0" max="100" value="${correction.score ?? Math.round(score)}"
                                           onchange="updateCorrection('${photo.image_path}', 'score', this.value); this.previousElementSibling.value=this.value">
                                </div>
                                <div class="form-row">
                                    <label>Composition</label>
                                    <input type="range" min="0" max="100" value="${correction.composition ?? Math.round((photo.composition || 0) * 100)}"
                                           oninput="this.nextElementSibling.value=this.value"
                                           onchange="updateCorrection('${photo.image_path}', 'composition', this.value)">
                                    <input type="number" min="0" max="100" value="${correction.composition ?? Math.round((photo.composition || 0) * 100)}"
                                           onchange="updateCorrection('${photo.image_path}', 'composition', this.value); this.previousElementSibling.value=this.value">
                                </div>
                                <div class="form-row">
                                    <label>Subject</label>
                                    <input type="range" min="0" max="100" value="${correction.subject ?? Math.round((photo.subject_strength || 0) * 100)}"
                                           oninput="this.nextElementSibling.value=this.value"
                                           onchange="updateCorrection('${photo.image_path}', 'subject', this.value)">
                                    <input type="number" min="0" max="100" value="${correction.subject ?? Math.round((photo.subject_strength || 0) * 100)}"
                                           onchange="updateCorrection('${photo.image_path}', 'subject', this.value); this.previousElementSibling.value=this.value">
                                </div>
                                <div class="form-row">
                                    <label>Appeal</label>
                                    <input type="range" min="0" max="100" value="${correction.appeal ?? Math.round((photo.visual_appeal || 0) * 100)}"
                                           oninput="this.nextElementSibling.value=this.value"
                                           onchange="updateCorrection('${photo.image_path}', 'appeal', this.value)">
                                    <input type="number" min="0" max="100" value="${correction.appeal ?? Math.round((photo.visual_appeal || 0) * 100)}"
                                           onchange="updateCorrection('${photo.image_path}', 'appeal', this.value); this.previousElementSibling.value=this.value">
                                </div>
                                <div class="form-row">
                                    <label>Notes</label>
                                    <textarea placeholder="Why did you adjust the score?"
                                              onchange="updateCorrection('${photo.image_path}', 'notes', this.value)">${correction.notes || ''}</textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            updateCorrectionsCount();
        }

        function updateCorrection(imagePath, field, value) {
            if (!corrections[imagePath]) {
                corrections[imagePath] = {
                    image_path: imagePath,
                    timestamp: new Date().toISOString()
                };
                const photo = photos.find(p => p.image_path === imagePath);
                if (photo) {
                    corrections[imagePath].original_score = photo.final_score;
                    corrections[imagePath].original_aesthetic = photo.aesthetic_score;
                    corrections[imagePath].original_technical = photo.technical_score;
                }
            }
            corrections[imagePath][field] = field === 'notes' ? value : parseFloat(value);
            corrections[imagePath].timestamp = new Date().toISOString();
            updateCorrectionsCount();
            localStorage.setItem('photo_corrections', JSON.stringify(corrections));
        }

        function updateCorrectionsCount() {
            const count = Object.keys(corrections).length;
            document.getElementById('correctionsCount').textContent = `${count} correction${count !== 1 ? 's' : ''} made`;
        }

        function exportCorrections() {
            const data = {
                exported_at: new Date().toISOString(),
                total_photos: photos.length,
                corrections_count: Object.keys(corrections).length,
                corrections: Object.values(corrections)
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `photo_corrections_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
        }

        function exportCSV() {
            const headers = ['image_path','final_score','aesthetic_score','technical_score','composition','subject_strength','visual_appeal','sharpness','exposure','noise_level','scene_type','lighting','subject_position','description','location_name','location_country','human_score','human_composition','human_subject','human_appeal','human_notes'];
            let csv = headers.join(',') + '\\n';
            for (const photo of photos) {
                const c = corrections[photo.image_path] || {};
                const row = [
                    photo.image_path, photo.final_score, photo.aesthetic_score, photo.technical_score,
                    photo.composition, photo.subject_strength, photo.visual_appeal,
                    photo.sharpness, photo.exposure, photo.noise_level,
                    photo.scene_type, photo.lighting, photo.subject_position,
                    `"${(photo.description || '').replace(/"/g, '""')}"`,
                    photo.location_name || '', photo.location_country || '',
                    c.score || '', c.composition || '', c.subject || '', c.appeal || '',
                    `"${(c.notes || '').replace(/"/g, '""')}"`
                ];
                csv += row.join(',') + '\\n';
            }
            const blob = new Blob([csv], {type: 'text/csv'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `photo_scores_corrected_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
        }

        function openLightbox(src) {
            document.getElementById('lightboxImg').src = src;
            document.getElementById('lightbox').classList.add('active');
        }

        function closeLightbox() {
            document.getElementById('lightbox').classList.remove('active');
        }

        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLightbox(); });

        // Load saved corrections
        const saved = localStorage.getItem('photo_corrections');
        if (saved) try { corrections = JSON.parse(saved); } catch(e) {}

        renderPhotos();
    </script>
</body>
</html>
"""


def parse_csv(filepath):
    """Parse CSV file into list of dicts."""
    import csv

    photos = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ["final_score", "aesthetic_score", "technical_score",
                       "composition", "subject_strength", "visual_appeal",
                       "sharpness", "exposure", "noise_level"]:
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        row[key] = 0
            photos.append(row)
    return photos


def convert_image_to_jpeg(filepath: Path) -> bytes:
    """Convert any image to JPEG bytes for browser display."""
    if str(filepath) in image_cache:
        return image_cache[str(filepath)]

    with Image.open(filepath) as img:
        # Convert to RGB if needed
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize for web display (max 2000px)
        max_dim = 2000
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        data = buffer.getvalue()

        # Cache the result
        image_cache[str(filepath)] = data
        return data


class PhotoHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            # Serve the viewer with embedded data
            photos = parse_csv(CSV_FILE)
            html = HTML_TEMPLATE.replace("PHOTOS_DATA", json.dumps(photos))

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif parsed.path.startswith("/photos/"):
            # Serve photo files (converted to JPEG)
            from urllib.parse import unquote
            filename = unquote(parsed.path[8:])  # Remove "/photos/" and decode
            filepath = Path(PHOTOS_DIR) / filename

            if filepath.exists():
                try:
                    jpeg_data = convert_image_to_jpeg(filepath)

                    self.send_response(200)
                    self.send_header("Content-type", "image/jpeg")
                    self.send_header("Content-Length", len(jpeg_data))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(jpeg_data)
                except Exception as e:
                    print(f"Error converting {filepath}: {e}")
                    self.send_error(500, f"Error converting image: {e}")
            else:
                self.send_error(404, f"File not found: {filename}")
        else:
            super().do_GET()

    def log_message(self, format, *args):
        # Only log errors, not every request
        if "404" in str(args) or "500" in str(args):
            print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    global PHOTOS_DIR, CSV_FILE

    import argparse
    parser = argparse.ArgumentParser(description="Photo Score Viewer Server")
    parser.add_argument("-p", "--photos", default="test_photos", help="Photos directory")
    parser.add_argument("-c", "--csv", default="test_photos_results.csv", help="CSV results file")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    args = parser.parse_args()

    PHOTOS_DIR = args.photos
    CSV_FILE = args.csv

    if not Path(CSV_FILE).exists():
        print(f"Error: CSV file not found: {CSV_FILE}")
        return

    if not Path(PHOTOS_DIR).exists():
        print(f"Warning: Photos directory not found: {PHOTOS_DIR}")

    # Allow socket reuse
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", args.port), PhotoHandler) as httpd:
        url = f"http://localhost:{args.port}"
        print(f"\n{'='*50}")
        print(f"Photo Score Viewer")
        print(f"{'='*50}")
        print(f"URL:     {url}")
        print(f"Photos:  {PHOTOS_DIR}")
        print(f"CSV:     {CSV_FILE}")
        print(f"{'='*50}")
        print("Press Ctrl+C to stop\n")

        webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()
