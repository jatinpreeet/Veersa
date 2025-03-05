import streamlit as st
import requests
import re
import json
from vosk import Model, KaldiRecognizer
import soundfile as sf
from io import BytesIO

# Initialize Vosk with small model (auto-downloads if missing)
try:
    model = Model(lang="en-us")
except Exception as e:
    st.error(f"Model initialization failed: {str(e)}")
    st.stop()

# Configure patterns
MEDICATION_PATTERN = r"\b(aspirin|lisinopril|metformin|warfarin|atorvastatin|ibuprofen|paracetamol)\b"
SYMPTOM_PATTERN = r"\b(cough|nausea|dizziness|rash|headache|vomiting|fatigue|swelling)\b"

def transcribe_audio(audio_file):
    """Transcribe audio using Vosk with error handling"""
    try:
        data, samplerate = sf.read(BytesIO(audio_file.read()))
        recognizer = KaldiRecognizer(model, samplerate)
        
        results = []
        for frame in data:
            if recognizer.AcceptWaveform(frame.tobytes()):
                results.append(json.loads(recognizer.Result()))
        results.append(json.loads(recognizer.FinalResult()))
        
        return " ".join([res.get("text", "") for res in results if res.get("text")])
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return ""

def extract_entities(text):
    """Enhanced entity extraction with normalization"""
    text = text.lower()
    meds = list(set(re.findall(MEDICATION_PATTERN, text)))
    symptoms = list(set(re.findall(SYMPTOM_PATTERN, text)))
    return meds, symptoms

def get_fda_events(medication):
    """Safe FDA API call"""
    try:
        response = requests.get(
            "https://api.fda.gov/drug/event.json",
            params={
                "search": f'patient.drug.medicinalproduct:"{medication}"',
                "count": "patient.reaction.reactionmeddrapt.exact",
                "limit": 5
            },
            timeout=10
        )
        if response.status_code == 200:
            return [item['term'].lower() for item in response.json().get('results', [])]
        return []
    except Exception as e:
        st.error(f"FDA API Error: {str(e)}")
        return []

# Streamlit UI
st.title("Adverse Event Checker 🚨")
st.write("Upload a conversation audio file or enter text below")

# Input section
input_type = st.radio("Input Type:", ("Audio", "Text"), horizontal=True)

text = ""
if input_type == "Audio":
    audio_file = st.file_uploader("Upload WAV audio", type=["wav"])
    if audio_file:
        with st.spinner("Transcribing audio..."):
            text = transcribe_audio(audio_file)
        if text:
            st.subheader("Transcript")
            st.write(text)
else:
    text = st.text_area("Enter conversation text:", height=150)

# Analysis section
if text:
    with st.spinner("Analyzing..."):
        meds, symptoms = extract_entities(text)
        
    if not meds:
        st.warning("No medications detected in the text")
    else:
        st.subheader("Analysis Results")
        
        for med in meds:
            med = med.capitalize()
            with st.expander(f"**{med}** Analysis"):
                adverse_events = get_fda_events(med)
                
                if not adverse_events:
                    st.write("No adverse event data found")
                    continue
                
                matches = [s for s in symptoms if s in adverse_events]
                if matches:
                    st.error("**Potential adverse effects detected:**")
                    for match in matches:
                        st.write(f"• {match.capitalize()}")
                    st.write("Common FDA-reported effects:")
                    st.write(", ".join([ae.capitalize() for ae in adverse_events]))
                else:
                    st.success("No matching adverse effects detected")
                    st.write("Known effects:", ", ".join([ae.capitalize() for ae in adverse_events]))

# Add sample input
st.markdown("---")
st.subheader("Sample Input")
st.code("Patient has been taking aspirin for a week but now reports severe headache and nausea.")