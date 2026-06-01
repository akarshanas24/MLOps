const SAMPLE_REPORTS = {
    cardiac: "Patient reports crushing chest pain, palpitations, diaphoresis, and shortness of breath with ECG changes.",
    respiratory: "Severe wheezing, hypoxia, and worsening dyspnea after an asthma exacerbation requiring urgent oxygen therapy.",
    neurological: "Sudden left-sided weakness, slurred speech, and confusion with concern for acute stroke.",
    emotional: "The patient is tearful, anxious, and describing panic attacks with hopelessness and severe stress.",
    normal: "Routine follow-up visit. The patient is stable, denies acute complaints, and exam is unremarkable.",
};

const API_BASE_URL = window.location.origin && window.location.origin !== "null"
    ? window.location.origin
    : "http://127.0.0.1:8000";

const elements = {
    form: document.getElementById("analysisForm"),
    textArea: document.getElementById("medicalText"),
    charCount: document.getElementById("charCount"),
    predictBtn: document.getElementById("predictBtn"),
    btnSpinner: document.getElementById("btnSpinner"),
    clearBtn: document.getElementById("clearBtn"),
    resultCard: document.getElementById("resultCard"),
    predictionTitle: document.getElementById("predictionTitle"),
    severityBadge: document.getElementById("severityBadge"),
    confidenceValue: document.getElementById("confidenceValue"),
    confidenceFill: document.getElementById("confidenceFill"),
    riskScore: document.getElementById("riskScore"),
    emergencyFlag: document.getElementById("emergencyFlag"),
    modelSource: document.getElementById("modelSource"),
    alertBox: document.getElementById("alertBox"),
    alertHeadline: document.getElementById("alertHeadline"),
    alertCopy: document.getElementById("alertCopy"),
    recommendationText: document.getElementById("recommendationText"),
    resultSummary: document.getElementById("resultSummary"),
    topPredictions: document.getElementById("topPredictions"),
    keywordTags: document.getElementById("keywordTags"),
    serviceStatus: document.getElementById("serviceStatus"),
};

function updateCharacterCount() {
    const value = elements.textArea.value.length;
    elements.charCount.textContent = `${value} character${value === 1 ? "" : "s"}`;
}

function setLoading(isLoading) {
    elements.predictBtn.disabled = isLoading;
    elements.btnSpinner.classList.toggle("visible", isLoading);
    elements.predictBtn.querySelector(".btn-text").textContent = isLoading
        ? "Analyzing report"
        : "Predict emergency";
}

function severityClass(severity) {
    const normalized = String(severity || "").toLowerCase();
    if (normalized.includes("critical")) return "severity-critical";
    if (normalized.includes("high")) return "severity-high";
    if (normalized.includes("moderate")) return "severity-moderate";
    if (normalized.includes("stable")) return "severity-stable";
    return "severity-low";
}

function alertClass(severity) {
    const normalized = String(severity || "").toLowerCase();
    if (normalized.includes("critical")) return "alert-critical";
    if (normalized.includes("high")) return "alert-high";
    if (normalized.includes("moderate")) return "alert-moderate";
    if (normalized.includes("stable")) return "alert-stable";
    return "alert-low";
}

function renderKeywordTags(keywords) {
    if (!keywords || !keywords.length) {
        elements.keywordTags.innerHTML = '<span class="tag tag-muted">No matching signals</span>';
        return;
    }

    elements.keywordTags.innerHTML = keywords.map((keyword) => `<span class="tag">${keyword}</span>`).join("");
}

function renderTopPredictions(predictions) {
    const entries = Array.isArray(predictions) ? predictions.slice(0, 3) : [];
    if (!entries.length) {
        elements.topPredictions.innerHTML = `
            <div class="rank-item">
                <div class="rank-row">
                    <span>No prediction data yet</span>
                    <strong>0.00%</strong>
                </div>
                <div class="rank-bar">
                    <div class="rank-fill" style="width: 0%"></div>
                </div>
            </div>
        `;
        return;
    }

    elements.topPredictions.innerHTML = entries
        .map((item) => {
            const confidence = Number(item.confidence || 0);
            const safeConfidence = Math.max(0, Math.min(100, confidence));
            return `
                <div class="rank-item">
                    <div class="rank-row">
                        <span>${item.label}</span>
                        <strong>${safeConfidence.toFixed(2)}%</strong>
                    </div>
                    <div class="rank-bar">
                        <div class="rank-fill" style="width: ${safeConfidence}%"></div>
                    </div>
                </div>
            `;
        })
        .join("");
}

function clearPrediction() {
    elements.resultCard.classList.add("is-empty");
    elements.resultCard.classList.remove("visible");
    elements.predictionTitle.textContent = "Awaiting review";
    elements.severityBadge.textContent = "Awaiting input";
    elements.severityBadge.className = "severity-pill";
    elements.resultSummary.textContent = "No report has been analyzed yet. Submit a clinical note to see the summary, score, and guidance.";
    elements.confidenceValue.textContent = "0%";
    elements.confidenceFill.style.width = "0%";
    elements.riskScore.textContent = "0.00";
    elements.emergencyFlag.textContent = "No";
    elements.modelSource.textContent = "Waiting";
    elements.alertBox.className = "alert-box calm";
    elements.alertHeadline.textContent = "Waiting for a report.";
    elements.alertCopy.textContent = "Results will appear here after analysis.";
    elements.recommendationText.textContent = "Submit a report to receive a recommendation.";
    elements.topPredictions.innerHTML = `
        <div class="rank-item">
            <div class="rank-row">
                <span>Waiting for model output</span>
                <strong>0.00%</strong>
            </div>
            <div class="rank-bar">
                <div class="rank-fill" style="width: 0%"></div>
            </div>
        </div>
    `;
    elements.keywordTags.innerHTML = '<span class="tag tag-muted">No signals yet</span>';
}

function showReadyState(message) {
    if (message) {
        elements.serviceStatus.textContent = message;
    }
}

async function refreshServerStatus() {
    elements.serviceStatus.textContent = "Connecting to server...";
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }
        const data = await response.json();
        elements.serviceStatus.textContent = data.model_loaded
            ? `Connected: ${data.model_source}`
            : "Server ready";
    } catch {
        elements.serviceStatus.textContent = "Server unavailable";
    }
}

async function predictEmergency() {
    const text = elements.textArea.value.trim();
    if (!text) {
        elements.serviceStatus.textContent = "Please enter a report first.";
        elements.textArea.focus();
        return;
    }

    setLoading(true);
    elements.serviceStatus.textContent = "Analyzing report...";

    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) {
            const errorPayload = await response.json().catch(() => ({}));
            throw new Error(errorPayload.detail || `Prediction failed with status ${response.status}`);
        }

        const result = await response.json();
        elements.resultCard.classList.remove("is-empty");
        elements.resultCard.classList.add("visible");

        const severity = result.severity || "Low";
        const prediction = result.prediction || "Normal";
        const confidence = Number(result.confidence || 0);
        const riskScore = Number(result.risk_score || 0);

        elements.predictionTitle.textContent = prediction;
        elements.severityBadge.textContent = severity;
        elements.severityBadge.className = `severity-pill ${severityClass(severity)}`;
        elements.resultSummary.textContent = result.emergency_flag
            ? `The model predicts ${prediction.toLowerCase()} with ${confidence.toFixed(2)}% confidence and this needs prompt review.`
            : `The model predicts ${prediction.toLowerCase()} with ${confidence.toFixed(2)}% confidence and this can be reviewed routinely.`;
        elements.confidenceValue.textContent = `${confidence.toFixed(2)}%`;
        elements.confidenceFill.style.width = `${Math.min(100, confidence)}%`;
        elements.riskScore.textContent = riskScore.toFixed(2);
        elements.emergencyFlag.textContent = result.emergency_flag ? "Yes" : "No";
        elements.modelSource.textContent = result.model_source || "Server";
        elements.alertBox.className = `alert-box ${alertClass(severity)}`;
        elements.alertHeadline.textContent = result.emergency_flag
            ? "Immediate review needed."
            : "Continue routine monitoring.";
        elements.alertCopy.textContent = result.emergency_flag
            ? "The report shows warning signs that deserve prompt attention."
            : "The report does not suggest an immediate emergency response.";
        elements.recommendationText.textContent = result.recommendation || "No recommendation available.";

        renderTopPredictions(result.top_predictions || []);
        renderKeywordTags(result.matched_keywords || []);
        elements.serviceStatus.textContent = `Prediction ready: ${result.prediction}`;
        elements.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        elements.serviceStatus.textContent = error.message || "Prediction failed";
        elements.alertBox.className = "alert-box alert-critical";
        elements.alertHeadline.textContent = "Prediction failed.";
        elements.alertCopy.textContent = error.message || "Unable to generate a result.";
    } finally {
        setLoading(false);
    }
}

elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await predictEmergency();
});

elements.textArea.addEventListener("input", updateCharacterCount);

elements.clearBtn.addEventListener("click", () => {
    elements.textArea.value = "";
    updateCharacterCount();
    clearPrediction();
    refreshServerStatus();
});

document.querySelectorAll(".sample-chip").forEach((button) => {
    button.addEventListener("click", () => {
        const sample = SAMPLE_REPORTS[button.dataset.sample];
        if (sample) {
            elements.textArea.value = sample;
            updateCharacterCount();
            elements.textArea.focus();
            refreshServerStatus();
        }
    });
});

clearPrediction();
updateCharacterCount();
refreshServerStatus();
