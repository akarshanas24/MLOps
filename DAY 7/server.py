from __future__ import annotations

import json
import re
import math
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
BUNDLE_PATH = BASE_DIR / "model_bundle.json"

SPECIALTY_TO_SEVERITY = {
    "Cardiovascular / Pulmonary": "Critical",
    "Neurology": "High",
    "Surgery": "High",
    "Orthopedic": "Moderate",
    "Urology": "Moderate",
    "Gastroenterology": "Moderate",
    "General Medicine": "Low",
    "Radiology": "Low",
    "SOAP / Chart / Progress Notes": "Low",
    "Consult - History and Phy.": "Low",
}

SPECIALTY_TO_RECOMMENDATION = {
    "Cardiovascular / Pulmonary": "Prioritize urgent cardiac and respiratory review.",
    "Neurology": "Escalate for neurological assessment and monitor for stroke signs.",
    "Surgery": "Review the case promptly and confirm perioperative stability.",
    "Orthopedic": "Monitor symptoms and arrange routine specialty follow-up.",
    "Urology": "Review clinically and confirm there are no acute complications.",
    "Gastroenterology": "Continue focused review and follow up as clinically indicated.",
    "General Medicine": "Routine review is reasonable unless symptoms change.",
    "Radiology": "Use the imaging result in the broader clinical context.",
    "SOAP / Chart / Progress Notes": "Continue documentation review and routine care planning.",
    "Consult - History and Phy.": "Review the consult context and route to the appropriate service.",
}

EMERGENCY_KEYWORDS = (
    "chest pain",
    "shortness of breath",
    "ecg",
    "ekg",
    "stroke",
    "seizure",
    "bleeding",
    "unresponsive",
    "shock",
    "trauma",
    "collapse",
    "hypoxia",
    "dyspnea",
    "palpitations",
)

SPECIALTY_KEYWORDS = {
    "Cardiovascular / Pulmonary": ("chest pain", "palpitations", "ecg", "dyspnea", "wheezing", "hypoxia", "shortness of breath"),
    "Neurology": ("stroke", "seizure", "weakness", "slurred speech", "confusion", "headache"),
    "Surgery": ("operative", "postoperative", "procedure", "incision", "anesthesia", "bleeding"),
    "Orthopedic": ("fracture", "joint", "bone", "pain", "sprain", "mobility"),
    "Urology": ("urinary", "bladder", "renal", "kidney", "catheter"),
    "Gastroenterology": ("abdominal", "nausea", "vomiting", "diarrhea", "gastro", "liver"),
    "General Medicine": ("follow up", "routine", "stable", "no acute distress", "improving"),
    "Radiology": ("ct", "mri", "x ray", "ultrasound", "imaging", "scan"),
    "SOAP / Chart / Progress Notes": ("progress", "chart", "soap", "note", "assessment", "plan"),
    "Consult - History and Phy.": ("consult", "history", "physical", "evaluation", "review"),
}


@lru_cache(maxsize=1)
def load_artifacts() -> Dict[str, object]:
    if not BUNDLE_PATH.exists():
        return {"loaded": False}

    with BUNDLE_PATH.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)
    bundle["loaded"] = True
    return bundle


def _get_classes(bundle: Dict[str, object]) -> List[str]:
    return [str(label).strip() for label in bundle.get("classes", [])]


def normalize_text(text: str) -> str:
    text_value = str(text or "").lower()
    text_value = re.sub(r"http\S+|www\S+", " ", text_value)
    text_value = re.sub(r"[^a-z0-9\s]", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def extract_keywords(text: str) -> List[str]:
    lowered = normalize_text(text)
    matches: List[str] = []
    for terms in SPECIALTY_KEYWORDS.values():
        for term in terms:
            if term in lowered and term not in matches:
                matches.append(term)
    return matches


def _tokenize(text: str, bundle: Dict[str, object]) -> List[str]:
    lowered = normalize_text(text) if bundle.get("lowercase", True) else str(text or "")
    token_pattern = bundle.get("token_pattern", r"(?u)\b\w\w+\b")
    tokens = re.findall(token_pattern, lowered)
    tokens = [token for token in tokens if len(token) > 1]
    return tokens


def _generate_ngrams(tokens: Sequence[str], ngram_range: Tuple[int, int]) -> List[str]:
    min_n, max_n = ngram_range
    features: List[str] = []
    for n in range(min_n, max_n + 1):
        if n <= 0 or len(tokens) < n:
            continue
        for index in range(len(tokens) - n + 1):
            features.append(" ".join(tokens[index : index + n]))
    return features


def _vectorize(text: str, bundle: Dict[str, object]) -> List[float]:
    vocabulary = bundle.get("vocabulary", {})
    if not vocabulary:
        return []

    ngram_range = tuple(bundle.get("ngram_range", (1, 1)))  # type: ignore[arg-type]
    tokens = _tokenize(text, bundle)
    features = _generate_ngrams(tokens, ngram_range)

    counts: Dict[int, int] = {}
    for feature in features:
        index = vocabulary.get(feature)
        if index is not None:
            counts[index] = counts.get(index, 0) + 1

    vector = [0.0] * len(vocabulary)
    idf = bundle.get("idf", [])
    sublinear_tf = bool(bundle.get("sublinear_tf", False))

    for index, count in counts.items():
        tf = 1.0 + math.log(count) if sublinear_tf and count > 0 else float(count)
        idf_value = float(idf[index]) if index < len(idf) else 1.0
        vector[index] = tf * idf_value

    norm = str(bundle.get("norm", "l2") or "").lower()
    if norm == "l2":
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude > 0:
            vector = [value / magnitude for value in vector]
    return vector


def _softmax(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    maximum = max(values)
    exps = [math.exp(value - maximum) for value in values]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def keyword_scores(text: str) -> Dict[str, float]:
    lowered = normalize_text(text)
    scores = {specialty: 0.05 for specialty in SPECIALTY_TO_SEVERITY}

    for specialty, terms in SPECIALTY_KEYWORDS.items():
        for term in terms:
            if term in lowered:
                scores[specialty] += 0.35

    for keyword in EMERGENCY_KEYWORDS:
        if keyword in lowered:
            scores["Cardiovascular / Pulmonary"] += 0.15
            scores["Neurology"] += 0.1
            scores["Surgery"] += 0.1

    if any(term in lowered for term in SPECIALTY_KEYWORDS["General Medicine"]):
        scores["General Medicine"] += 0.25

    total = sum(scores.values()) or 1.0
    return {specialty: value / total for specialty, value in scores.items()}


def severity_from_specialty(specialty: str, confidence: float) -> str:
    severity = SPECIALTY_TO_SEVERITY.get(specialty.strip(), "Low")
    if severity == "Critical":
        return "Critical" if confidence >= 70 else "High"
    if severity == "High":
        return "High" if confidence >= 55 else "Moderate"
    if severity == "Moderate":
        return "Moderate" if confidence >= 45 else "Low"
    return "Stable" if confidence >= 45 else "Low"


def recommendation_from_specialty(specialty: str, severity: str) -> str:
    if severity == "Critical":
        return "Escalate immediately for urgent review and stabilization."
    if severity == "High":
        return "Prioritize same-day clinical review and monitor closely."
    if severity == "Moderate":
        return SPECIALTY_TO_RECOMMENDATION.get(specialty, "Review the case promptly and monitor for changes.")
    return SPECIALTY_TO_RECOMMENDATION.get(specialty, "Continue routine monitoring and follow up as needed.")


def emergency_flag_from_text(specialty: str, confidence: float, text: str) -> bool:
    lowered = normalize_text(text)
    if any(keyword in lowered for keyword in EMERGENCY_KEYWORDS):
        return True
    return specialty in {"Cardiovascular / Pulmonary", "Neurology"} and confidence >= 55


def score_to_risk(specialty: str, confidence: float) -> float:
    weights = {
        "Cardiovascular / Pulmonary": 1.0,
        "Neurology": 0.92,
        "Surgery": 0.84,
        "Orthopedic": 0.65,
        "Urology": 0.62,
        "Gastroenterology": 0.66,
        "General Medicine": 0.45,
        "Radiology": 0.35,
        "SOAP / Chart / Progress Notes": 0.3,
        "Consult - History and Phy.": 0.4,
    }
    return round(min(100.0, confidence * weights.get(specialty, 0.5)), 2)


def predict_with_model(text: str) -> Dict[str, object] | None:
    artifacts = load_artifacts()
    if not artifacts.get("loaded"):
        return None

    cleaned_text = normalize_text(text)
    classes = _get_classes(artifacts)
    feature_log_prob = artifacts.get("feature_log_prob", [])
    class_log_prior = artifacts.get("class_log_prior", [])
    vector = _vectorize(cleaned_text, artifacts)

    model_scores: Dict[str, float] = {}
    for class_index, class_name in enumerate(classes):
        log_prior = float(class_log_prior[class_index]) if class_index < len(class_log_prior) else 0.0
        feature_row = feature_log_prob[class_index] if class_index < len(feature_log_prob) else []
        log_likelihood = log_prior
        for feature_index, value in enumerate(vector):
            if value and feature_index < len(feature_row):
                log_likelihood += value * float(feature_row[feature_index])
        model_scores[class_name] = log_likelihood

    probabilities = _softmax(list(model_scores.values()))
    model_probs = {label: prob for label, prob in zip(classes, probabilities)}
    heuristic_scores = keyword_scores(cleaned_text)
    combined_scores = {
        specialty: (0.55 * model_probs.get(specialty, 0.0)) + (0.45 * heuristic_scores.get(specialty, 0.0))
        for specialty in SPECIALTY_TO_SEVERITY
    }

    ranked = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
    prediction, probability = ranked[0]
    confidence = round(probability * 100, 2)
    severity = severity_from_specialty(prediction, confidence)
    matched_keywords = extract_keywords(cleaned_text)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "risk_score": score_to_risk(prediction, confidence),
        "emergency_flag": emergency_flag_from_text(prediction, confidence, cleaned_text),
        "model_source": artifacts.get("source", "trained sklearn artifact"),
        "recommendation": recommendation_from_specialty(prediction, severity),
        "cleaned_text": cleaned_text,
        "input_text": text,
        "matched_keywords": matched_keywords,
        "top_predictions": [
            {"label": label, "confidence": round(score * 100, 2)}
            for label, score in ranked[:3]
        ],
    }


def predict_with_rules(text: str) -> Dict[str, object]:
    lowered = normalize_text(text)
    scores = {specialty: 0.1 for specialty in SPECIALTY_TO_SEVERITY}
    matched = extract_keywords(lowered)

    for specialty, terms in SPECIALTY_KEYWORDS.items():
        for term in terms:
            if term in lowered:
                scores[specialty] += 0.35

    if not matched:
        scores["General Medicine"] += 0.4

    total = sum(scores.values()) or 1.0
    probabilities = {specialty: score / total for specialty, score in scores.items()}
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    prediction, probability = ranked[0]
    confidence = round(probability * 100, 2)
    severity = severity_from_specialty(prediction, confidence)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "risk_score": score_to_risk(prediction, confidence),
        "emergency_flag": emergency_flag_from_text(prediction, confidence, text),
        "model_source": "rule-based fallback",
        "recommendation": recommendation_from_specialty(prediction, severity),
        "cleaned_text": lowered,
        "input_text": text,
        "matched_keywords": matched,
        "top_predictions": [
            {"label": label, "confidence": round(score * 100, 2)}
            for label, score in ranked[:3]
        ],
    }


def predict_report(text: str) -> Dict[str, object]:
    return predict_with_model(text) or predict_with_rules(text)


def health() -> Dict[str, object]:
    artifacts = load_artifacts()
    return {
        "status": "healthy",
        "model_loaded": bool(artifacts.get("loaded")),
        "model_source": artifacts.get("source", "rule-based fallback"),
    }


def json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, object], status: int = 200) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(data)


def file_response(handler: BaseHTTPRequestHandler, path: Path, content_type: str) -> None:
    data = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "ClinicalAlertMonitor/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/ui"}:
            return file_response(self, FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
        if self.path == "/style.css":
            return file_response(self, FRONTEND_DIR / "style.css", "text/css; charset=utf-8")
        if self.path == "/script.js":
            return file_response(self, FRONTEND_DIR / "script.js", "application/javascript; charset=utf-8")
        if self.path == "/health":
            return json_response(self, health())
        json_response(self, {"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/predict":
            return json_response(self, {"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            return json_response(self, {"detail": "Invalid JSON payload"}, status=HTTPStatus.BAD_REQUEST)

        text = str(payload.get("text", "")).strip()
        if not text:
            return json_response(self, {"detail": "Field 'text' is required"}, status=HTTPStatus.BAD_REQUEST)

        return json_response(self, predict_report(text))


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), RequestHandler)
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
