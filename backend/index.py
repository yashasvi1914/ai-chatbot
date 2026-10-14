from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Support both package-relative and top-level imports so the module can
# be started either as a package (e.g. `uvicorn package.module:app`) or
# directly from the `backend` folder (`uvicorn index:app`).
try:
    from .gemini_service import generate_chat_response
except Exception:
    from gemini_service import generate_chat_response
from youtube_transcript_api import YouTubeTranscriptApi
import json
import re

app = FastAPI(
    title="GenAI Chatbot SaaS API",
    description="FastAPI Backend for Gemini Integration",
    version="1.0.0"
)
@app.get("/api/health")
def health_check():
    return {"status": "ok"}
# Enable CORS so your frontend can connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your specific Vercel frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define what the incoming data from the frontend should look like
class ChatRequest(BaseModel):
    message: str


class YouTubeUrlRequest(BaseModel):
    url: str


class TranscriptRequest(BaseModel):
    transcript: str

# @app.post("/api/chat")
# async def chat(payload: ChatRequest):
#     user_message = payload.message.strip()
    
#     if not user_message:
#         raise HTTPException(status_code=400, detail="Message cannot be empty")
        
#     # Call our Gemini service to fetch the AI generation
#     bot_reply = generate_chat_response(user_message)
    
#     return {"reply": bot_reply}
# Just want to check (mikun)
from fastapi import HTTPException
import markdown  # 1. Import the markdown library

@app.post("/api/chat")
async def chat(payload: ChatRequest):
    user_message = payload.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    # Call our Gemini service to fetch the AI generation
    bot_reply = generate_chat_response(user_message)
    
    # 2. Convert the raw text/markdown from Gemini into valid HTML strings
    # 'extra' adds support for tables, code blocks, and lists
    html_reply = markdown.markdown(bot_reply, extensions=['extra'])
    
    return {"reply": html_reply}


# Serve frontend static files from the project's frontend folder at the root path
static_dir = Path(__file__).resolve().parent.parent / 'frontend'
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {"status": "healthy", "service": "FastAPI Chatbot Backend"}


@app.post('/api/youtube/transcript')
async def youtube_transcript(payload: YouTubeUrlRequest):
    """Fetch transcript for a public YouTube video using youtube-transcript-api.
    Returns a plain text transcript string.
    """
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail='URL is required')

    # try to extract video id naively
    try:
        if 'v=' in url:
            vid = url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            vid = url.split('youtu.be/')[1].split('?')[0]
        else:
            vid = url

        transcript_list = YouTubeTranscriptApi.get_transcript(vid)
        # join the text pieces into a single transcript
        transcript_text = '\n'.join([t.get('text', '') for t in transcript_list])
        return {'transcript': transcript_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Could not fetch transcript: {e}')


@app.post('/api/youtube/summarize')
async def youtube_summarize(payload: TranscriptRequest):
    """Summarize the provided transcript text using the Gemini service.
    Returns a JSON object with `summary` and `keypoints` (list).
    """
    text = (payload.transcript or '').strip()
    if not text:
        raise HTTPException(status_code=400, detail='Transcript text is required')

    # Limit the prompt length to avoid extremely long requests
    prompt_text = text if len(text) < 25000 else text[:25000]

    # Build a structured JSON-output prompt so the model returns machine-readable results
    prompt = (
        "You are an assistant that converts a YouTube transcript into concise study material.\n"
        "Return a JSON object ONLY (no surrounding commentary) with the following keys:\n"
        "  - summary: a concise 3-5 sentence summary of the video.\n"
        "  - keypoints: an array of the top 6 key points (short strings).\n"
        "  - study_plan: an ordered array of 4-6 actionable study steps the student should take to master the video's topic.\n"
        "  - timestamps: an array of objects {time: 'MM:SS' or 'HH:MM:SS', point: 'short description'} for important moments.\n"
        "  - links: an array of useful external links (papers, docs, docs examples) if any, else empty array.\n"
        "Make keypoints and study_plan concise. If timestamps are not present in the transcript, provide rough locations inferred by relative position (e.g., '00:02:15').\n\n"
        f"Transcript:\n{prompt_text}"
    )

    try:
        raw = generate_chat_response(prompt)

        # Try to extract the first JSON object found in the model output
        json_text = None
        match = re.search(r"\{", raw)
        if match:
            start = match.start()
            depth = 0
            end = None
            for i in range(start, len(raw)):
                if raw[i] == '{':
                    depth += 1
                elif raw[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end:
                candidate = raw[start:end]
                try:
                    parsed = json.loads(candidate)
                    json_text = parsed
                except Exception:
                    json_text = None

        if json_text is None:
            try:
                json_text = json.loads(raw)
            except Exception:
                # Return raw output if parsing fails so frontend can show it
                return {'raw': raw}

        summary = json_text.get('summary', '')
        keypoints = json_text.get('keypoints', [])
        study_plan = json_text.get('study_plan', [])
        timestamps = json_text.get('timestamps', [])
        links = json_text.get('links', [])

        return {
            'summary': summary,
            'keypoints': keypoints,
            'study_plan': study_plan,
            'timestamps': timestamps,
            'links': links
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Summarization failed: {e}')