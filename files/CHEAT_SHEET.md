# CineGraph AI - Developer Cheat Sheet

## Agent Specifications (One-Liner Each)

| Agent | Input | Output | Command |
|-------|-------|--------|---------|
| **1. Parser** | Raw narrative | Structured story (characters, timeline, emotions) | `python -m agents.parser "story text"` |
| **2. Planner** | Structured story | Scene breakdown (scene_001, scene_002, ...) | `python -m agents.planner story_id` |
| **3. Director** | Scenes | Cinematic decisions (camera, lighting, color) | `python -m agents.director story_id` |
| **4. Continuity** | Scenes + Director | Character state log + violations | `python -m agents.continuity story_id` |
| **5. Prompt Gen** | Scenes + Cinematic | Flux/SDXL image prompts | `python -m agents.prompt_gen story_id` |
| **6. Ambiguity** | Flagged ambiguities | Resolutions (auto or user-provided) | `python -m agents.ambiguity story_id` |
| **7. Evaluator** | Generated output | Quality scores (0-1) + feedback | `python -m agents.evaluator story_id` |

---

## Database at a Glance

```sql
-- Create story
INSERT INTO stories (id, title, raw_input, status) 
VALUES ('uuid', 'Title', 'narrative...', 'processing');

-- Save parsed narrative
INSERT INTO narrative_states (story_id, parsed_data)
VALUES ('uuid', '{"characters": [...], ...}');

-- Save scene
INSERT INTO scenes (story_id, scene_number, title, metadata_json)
VALUES ('uuid', 1, 'Scene Title', '{"location": "..."}');

-- Track character appearance
INSERT INTO character_states (story_id, scene_id, character_name, appearance_json)
VALUES ('uuid', 'scene_uuid', 'Maya', '{"hair": "black", "clothing": "jacket"}');

-- Save cinematic decisions
INSERT INTO cinematic_decisions (scene_id, camera_json, lighting_json)
VALUES ('scene_uuid', '{"angle": "close_up", ...}', '{"intensity": "low", ...}');

-- Generate image
INSERT INTO visual_prompts (scene_id, positive_prompt, seed)
VALUES ('scene_uuid', 'detailed prompt...', 42);

-- Log agent execution
INSERT INTO agent_logs (story_id, agent_name, input_json, output_json, execution_time_ms)
VALUES ('uuid', 'parser', '{}', '{}', 1234);
```

---

## API Endpoints (Copy-Paste URLs)

```
# Create story (202 Accepted, returns job_id)
POST /api/v1/stories
  → {"story_id": "...", "status": "processing"}

# Get story (200 OK)
GET /api/v1/stories/{story_id}
  → {"id": "...", "title": "...", "status": "..."}

# Get all scenes (200 OK)
GET /api/v1/stories/{story_id}/scenes
  → [{"scene_id": "...", "title": "...", ...}]

# Get execution trace (200 OK)
GET /api/v1/stories/{story_id}/trace
  → {"agents": [...], "timing": {...}}

# Get evaluation (200 OK)
GET /api/v1/stories/{story_id}/evaluation
  → {"overall_score": 0.88, "metrics": {...}}

# Regenerate with seed (202 Accepted)
POST /api/v1/stories/{story_id}/regenerate
  {"seed": 42}

# Get scene graph for viz (200 OK)
GET /api/v1/stories/{story_id}/narrative-graph
  → {"nodes": [...], "links": [...]}

# Get storyboard frames (200 OK)
GET /api/v1/stories/{story_id}/scenes/{scene_id}/storyboard
  → {"frames": [{"image_url": "...", "prompt": "..."}]}
```

---

## Agent Template (Copy This)

```python
from pydantic import BaseModel
from anthropic import Anthropic
import json

class Input(BaseModel):
    narrative: str

class Output(BaseModel):
    result: dict

class Agent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
    
    async def execute(self, input_data: dict) -> dict:
        validated = Input(**input_data)
        
        prompt = f"""[System prompt here]
        
Input: {validated.narrative}"""
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        output = json.loads(response.content[0].text)
        return Output(**output).model_dump()
```

---

## FastAPI Endpoint Template

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models import Story
from agents.my_agent import MyAgent

router = APIRouter(prefix="/api/v1")

@router.post("/stories")
async def create_story(request: StoryRequest, db: Session, bg: BackgroundTasks):
    story = Story(title=request.title, raw_input=request.input)
    db.add(story)
    db.commit()
    
    bg.add_task(process, story.id, db)
    
    return {"story_id": story.id, "status": "processing"}

async def process(story_id: str, db: Session):
    story = db.query(Story).filter(Story.id == story_id).first()
    agent = MyAgent(api_key="...")
    result = await agent.execute({"narrative": story.raw_input})
    # Save to DB...
```

---

## Test Stories (Quick Copy)

### Story 1: Emotional
```
A retired astronaut receives radio messages from his dead co-pilot. 
At first he thinks it's a malfunction. As messages continue, he realizes 
the transmission is real. He spirals into obsession, spending nights in 
his observatory trying to decode the messages.
```

### Story 2: Action  
```
A hacker infiltrates a floating cyberpunk city. She needs to steal 
a biometric encryption key from the central tower. With her team monitoring 
from outside, she uses parkour and hacking tools to navigate through security 
systems and guards. She escapes with the key before the tower explodes.
```

### Story 3: Ambiguous
```
A woman opens a letter. Her hands tremble. She reads silently, 
tears streaming down her face. The camera pans to show an empty living room. 
A wedding photo on the shelf is turned face-down. She sits alone at a table, 
the letter crumpled in her hand. Outside, rain falls.
```

---

## Key Constants

```python
# Always use
MODEL = "claude-3-5-sonnet-20241022"
TEMPERATURE = 0.3  # Low entropy for determinism
MAX_TOKENS = 2000   # Balanced for cost/quality

# Database
DATABASE_URL = "postgresql://user:pass@localhost/cinegraph_ai"

# Image Generation
FLUX_MODEL = "black-forest-labs/FLUX.1-dev"
IMAGE_SEED = hash(story_input) % (2**31)  # Deterministic seed

# Timeouts
AGENT_TIMEOUT = 60  # seconds
API_TIMEOUT = 30    # seconds

# Paths
OUTPUT_DIR = "./outputs/{story_id}/"
LOGS_DIR = "./logs/"
```

---

## SQL Queries (For Debugging)

```sql
-- Get all stories
SELECT id, title, status, created_at FROM stories ORDER BY created_at DESC;

-- Get story with agent logs
SELECT * FROM agent_logs WHERE story_id = 'story_uuid' ORDER BY created_at;

-- Get scenes for a story
SELECT * FROM scenes WHERE story_id = 'story_uuid' ORDER BY scene_number;

-- Get character state through a story
SELECT DISTINCT character_name FROM character_states WHERE story_id = 'story_uuid';

-- Find slow agents
SELECT agent_name, AVG(execution_time_ms) as avg_time 
FROM agent_logs 
WHERE status = 'success' 
GROUP BY agent_name 
ORDER BY avg_time DESC;

-- Check continuity violations
SELECT * FROM continuity_violations WHERE story_id = 'story_uuid';

-- Get evaluation scores
SELECT overall_score, metrics FROM evaluation_results WHERE story_id = 'story_uuid';
```

---

## Environment Variables

```bash
# .env (Backend)
ANTHROPIC_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@localhost/cinegraph_ai
REDIS_URL=redis://localhost:6379
AWS_S3_BUCKET=cinegraph-ai
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
REPLICATE_API_TOKEN=...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## Determinism Checklist

```
☑ temperature = 0.3
☑ seed = hash(input) or provided_seed
☑ random.seed(seed) at start
☑ All outputs stored with seed
☑ Test 3x with same seed, compare outputs
☑ Document determinism % in logs
```

---

## Common Commands

```bash
# Setup
pip install -r requirements.txt
createdb cinegraph_ai
alembic upgrade head
export ANTHROPIC_API_KEY="sk-..."

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
npm run dev

# Run tests
pytest tests/ -v
pytest tests/ --cov=backend/

# Format code
black backend/ frontend/
pylint backend/

# Database
psql cinegraph_ai -c "SELECT * FROM stories LIMIT 5;"
alembic revision --autogenerate -m "description"

# Docker
docker-compose up -d
docker-compose logs -f api
docker-compose down
```

---

## Error Handling Pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_agent(agent, input_data):
    try:
        return await agent.execute(input_data)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise

# Usage
try:
    result = await call_agent(parser, narrative)
except Exception as e:
    story.status = "failed"
    story.error_message = str(e)
    db.commit()
```

---

## Frontend Components (Quick Checklist)

```
☑ StoryInput          - textarea + metadata + submit
☑ ProcessingStatus    - progress bar + agent names + time
☑ SceneTimeline       - horizontal timeline + cards
☑ StoryboardViewer    - grid of frames + zoom
☑ NarrativeGraph      - D3 force graph + scene nodes
☑ AgentTraceViewer    - tree view + JSON outputs
☑ EvaluationDashboard - scores + metrics + issues
```

---

## React Hooks Pattern

```typescript
// useStory.ts
export const useStory = (storyId: string) => {
  const [story, setStory] = useState(null);
  const [status, setStatus] = useState('loading');
  
  useEffect(() => {
    const interval = setInterval(() => {
      api.getStory(storyId).then(setStory);
    }, 2000);
    
    return () => clearInterval(interval);
  }, [storyId]);
  
  return { story, status };
};

// Usage in component
const { story, status } = useStory(storyId);
if (status === 'loading') return <Spinner />;
return <div>{story.title}</div>;
```

---

## Success Metrics Targets

| Metric | Target | How to Check |
|--------|--------|-------------|
| Narrative Alignment | > 0.90 | Manual review |
| Continuity | > 0.88 | Character consistency |
| Visual Quality | > 0.80 | Image inspection |
| Determinism | > 99% | Run 3x, compare |
| Speed | < 300s | Check logs |
| Ambiguity Detection | > 90% | Test Story 3 |

---

## One-Minute Troubleshooting

**Agent returns invalid JSON?**
→ Lower temperature to 0.1, simplify prompt

**Determinism breaks?**
→ Check temperature, seed, random calls

**Images don't match?**
→ Add more detail to prompt, reference styles

**Database error?**
→ Check migrations: `alembic current`

**API timeout?**
→ Increase timeout, optimize prompts, add caching

**Frontend not updating?**
→ Check polling interval, WebSocket connection

---

**Remember: Simple, reliable > Complex, broken. Start small, test often.**
