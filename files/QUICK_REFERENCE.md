# CineGraph AI - Quick Reference Guide

## 🚀 Quick Start (5 minutes)

```bash
# 1. Setup
git clone <repo> && cd cinegraph-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Database
createdb cinegraph_ai
alembic upgrade head

# 3. Environment
# Create backend/.env with ANTHROPIC_API_KEY

# 4. Run
cd backend && uvicorn main:app --reload
# Frontend: cd ../frontend && npm run dev
```

---

## 📋 Core Agents (At a Glance)

| Agent | Input | Output | Key Task |
|-------|-------|--------|----------|
| **Parser** | Raw narrative | Structured JSON (characters, timeline, etc.) | Understand story |
| **Planner** | Narrative struct | Scene breakdown | Split into cinematic scenes |
| **Director** | Scenes | Camera/lighting/style | Make cinematic decisions |
| **Continuity** | Scenes + Director | Character state log | Track consistency |
| **Prompt Gen** | Scenes + Cinematic | Image generation prompts | Optimize for generation |
| **Ambiguity** | Flagged sections | Resolutions | Resolve vague sections |
| **Evaluator** | Generated output | Quality scores | Grade outputs |

---

## 🔑 Key Concepts

### Determinism
- **Same input + same seed = same output (99%)**
- Always set `temperature=0.3`
- Seed all random operations
- Log everything

### Immutable State
- Each agent receives copy of state
- Agent produces new state
- Parent orchestrator merges
- All changes logged

### Observability
- Every agent execution logged
- Store inputs, outputs, timing
- Enable replay from logs
- Trace viewer shows full execution

---

## 📦 Database Schema (Quick Reference)

```sql
-- Core tables
stories(id, title, raw_input, status, created_at)
narrative_states(id, story_id, parsed_data, version)
scenes(id, story_id, scene_number, title, location, metadata_json)
character_states(id, character_name, scene_id, appearance_json, emotion_json)
cinematic_decisions(id, scene_id, camera_json, lighting_json, visual_style_json)
visual_prompts(id, scene_id, frame_number, positive_prompt, negative_prompt, seed)
storyboard_frames(id, visual_prompt_id, image_url, generation_time_ms)
agent_logs(id, story_id, agent_name, input_json, output_json, execution_time_ms)
```

---

## 🛠️ Agent Template (Copy-Paste Ready)

```python
from pydantic import BaseModel
from anthropic import Anthropic

class InputSchema(BaseModel):
    data: str

class OutputSchema(BaseModel):
    result: dict

class MyAgent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
    
    async def execute(self, input_data: dict) -> dict:
        # Validate
        validated_input = InputSchema(**input_data)
        
        # Build prompt
        prompt = f"[System prompt]\n{validated_input.data}"
        
        # Call API
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse & validate
        import json
        output = json.loads(response.content[0].text)
        validated_output = OutputSchema(**output)
        
        return validated_output.model_dump()
```

---

## 🔌 API Endpoints (MVP)

```
POST   /api/v1/stories                      # Create story
GET    /api/v1/stories/{id}                 # Get story
GET    /api/v1/stories/{id}/scenes          # Get scenes
GET    /api/v1/stories/{id}/trace           # Get execution trace
GET    /api/v1/stories/{id}/evaluation      # Get quality scores
POST   /api/v1/stories/{id}/regenerate      # Regenerate with seed
GET    /api/v1/stories/{id}/narrative-graph # Get scene graph
```

---

## 📝 Test Stories (Use These!)

### Story 1: Emotional Drama
```
"A retired astronaut receives radio messages from his dead co-pilot..."
Expected: Melancholic, 4-5 scenes, emotional arc
```

### Story 2: Action
```
"A hacker infiltrates a floating cyberpunk city..."
Expected: Fast-paced, 5-6 scenes, neon visuals
```

### Story 3: Ambiguous
```
"A woman opens a letter and begins crying silently..."
Expected: Flags ambiguities, emotional inference, 3-4 scenes
```

---

## ✅ Pre-Commit Checklist

Before pushing code:
- [ ] Tests pass: `pytest tests/`
- [ ] Linting clean: `pylint backend/`
- [ ] Type hints: `mypy backend/`
- [ ] No API keys in code
- [ ] Database migrations created
- [ ] Agent outputs logged
- [ ] Determinism verified (run test 3x)

---

## 🐛 Debugging Commands

```bash
# Test agent in isolation
python -m cli.test_agent parser "narrative text"

# Check database state
psql cinegraph_ai -c "SELECT * FROM agent_logs LIMIT 5;"

# View full execution trace
curl http://localhost:8000/api/v1/stories/{id}/trace | jq

# Regenerate with same seed
curl -X POST http://localhost:8000/api/v1/stories/{id}/regenerate \
  -H "Content-Type: application/json" \
  -d '{"seed": 42}'

# Check image generation
curl http://localhost:8000/api/v1/stories/{id}/scenes/1/storyboard
```

---

## 🎯 Success Metrics

| Metric | Target | How to Test |
|--------|--------|------------|
| Narrative Alignment | > 0.90 | Review output vs input |
| Continuity | > 0.88 | Check character appearance |
| Visual Quality | > 0.80 | Inspect generated images |
| Determinism | > 99% | Run story 3x, compare |
| Speed | < 5 min | Check execution logs |

---

## 🔑 Determinism Checklist

```python
# ✅ Always do this
temperature = 0.3
seed = hash(input + provided_seed)
random.seed(seed)
output['seed'] = seed

# ❌ Never do this
temperature = 0.7  # Too high, non-deterministic
random_value = random.random()  # Not seeded
np.random.randn()  # NumPy not seeded
```

---

## 📊 Prompt Engineering Tips

1. **Be explicit**: Include every detail (camera angle, lighting, etc.)
2. **Use examples**: Reference films or styles
3. **Set constraints**: "Return ONLY JSON", "Output must validate against schema"
4. **Be consistent**: Use same structure across agents
5. **Test iteratively**: Try variations, measure quality

---

## 🚨 Common Pitfalls

| Problem | Fix |
|---------|-----|
| Agent returns invalid JSON | Lower temperature, simplify prompt |
| Continuity breaks | Ensure state saved after each agent |
| Images don't match | Add more detail to visual prompts |
| Determinism lost | Check all randomness is seeded |
| API errors | Implement retry with exponential backoff |
| Database corruption | Always use migrations, test rollback |

---

## 📚 File Structure Reference

```
cinegraph-ai/
├── backend/
│   ├── agents/          ← Agent implementations
│   ├── api/routes/      ← API endpoints
│   ├── database/        ← Models, schemas, migrations
│   ├── orchestration/   ← DAG engine
│   └── main.py          ← FastAPI app
│
├── frontend/
│   ├── components/      ← React components
│   ├── pages/           ← Next.js pages
│   └── lib/             ← Utilities, API client
│
├── tests/               ← Test files
└── docs/                ← Documentation
```

---

## 🔗 Important Links

- **Anthropic Docs**: https://docs.anthropic.com
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Flux Model**: https://huggingface.co/black-forest-labs/FLUX.1-dev
- **Replicate API**: https://replicate.com/docs

---

## 💡 Pro Tips

1. **Use `jq`** to pretty-print JSON responses:
   ```bash
   curl http://localhost:8000/api/v1/stories/123 | jq
   ```

2. **Test agents individually** before integration:
   ```bash
   python -c "from agents.parser_agent import Parser; await Parser().execute({'narrative': '...'})"
   ```

3. **Keep a test notebook** for quick iteration:
   ```python
   # test.ipynb
   from agents.parser_agent import Parser
   agent = Parser(api_key="...")
   await agent.execute({"narrative": "test"})
   ```

4. **Version your prompts** in version control:
   ```
   prompts/
   ├── v1/
   │   └── parser_prompt.txt
   └── v2/
       └── parser_prompt.txt
   ```

5. **Use seed 42** for testing (lucky number!)

---

## 🎉 You're Ready!

Start with Phase 1:
1. Build database
2. Implement Parser Agent
3. Create API endpoint
4. Build basic UI
5. Test with test stories

Good luck! 🚀
