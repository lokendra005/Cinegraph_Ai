# CineGraph AI - Implementation Guide

## Quick Start for Developers

This guide provides step-by-step instructions for implementing CineGraph AI based on the comprehensive PRD.

---

## Table of Contents
1. Setup & Environment
2. Phase-by-Phase Implementation
3. Code Structure & Templates
4. Key Implementation Patterns
5. Testing Strategy
6. Debugging & Troubleshooting

---

## 1. SETUP & ENVIRONMENT

### 1.1 Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Git
- Docker (optional but recommended)

### 1.2 Environment Setup

```bash
# Clone repository
git clone <repo>
cd cinegraph-ai

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Create .env files
# Backend: backend/.env
# Frontend: frontend/.env.local
```

### 1.3 Database Setup

```bash
# Create PostgreSQL database
createdb cinegraph_ai

# Run migrations
cd backend
alembic upgrade head

# Seed test data (optional)
python -m scripts.seed_test_data
```

### 1.4 API Keys

Required keys to add to `.env`:
```
ANTHROPIC_API_KEY=sk-...
REPLICATE_API_TOKEN=...  # For image generation
AWS_S3_BUCKET=cinegraph-ai
DATABASE_URL=postgresql://user:pass@localhost/cinegraph_ai
```

---

## 2. PHASE-BY-PHASE IMPLEMENTATION

### Phase 1: Core MVP (Weeks 1-3)

**Goal**: Parse narratives → Break into scenes → Store in DB → Serve via API

#### Week 1: Parser Agent + Database
1. **Create database schema** (models.py)
   - Stories table
   - Narrative states table
   - Scenes table (basic)

2. **Implement Narrative Parser Agent**
   ```python
   # backend/agents/parser_agent.py
   from anthropic import Anthropic
   from pydantic import BaseModel, ValidationError
   
   class CharacterSchema(BaseModel):
       name: str
       role: str  # protagonist, antagonist, secondary
       description: str
       relationships: List[dict]
   
   class NarrativeParserAgent:
       def __init__(self, api_key: str):
           self.client = Anthropic(api_key=api_key)
       
       async def parse(self, narrative: str) -> dict:
           prompt = """
           Parse this narrative into structured JSON:
           [Include full schema from PRD]
           
           RULES:
           1. Return ONLY valid JSON
           2. Use structured format
           3. Flag ambiguities
           """
           
           response = self.client.messages.create(
               model="claude-3-5-sonnet-20241022",
               max_tokens=4000,
               temperature=0.3,
               messages=[{"role": "user", "content": prompt + "\n\nNarrative: " + narrative}]
           )
           
           # Parse and validate JSON
           return self._validate_output(response.content[0].text)
   ```

3. **Create API endpoint** (routes/stories.py)
   ```python
   @router.post("/api/v1/stories")
   async def create_story(request: StoryCreateRequest):
       # 1. Save raw input to DB
       # 2. Call parser agent
       # 3. Save parsed output to narrative_states table
       # 4. Return story_id
   ```

4. **Build basic frontend**
   - Input form (textarea)
   - Loading indicator
   - Display story metadata

#### Week 2: Scene Planner Agent
1. **Implement Scene Planner Agent**
   ```python
   # backend/agents/planner_agent.py
   class ScenePlannerAgent:
       async def plan(self, narrative_state: dict) -> dict:
           # Convert narrative structure to scenes
           # Extract scenes with metadata
           # Return scene list
   ```

2. **Create Scene Timeline Viewer**
   - Frontend: Display scenes in horizontal timeline
   - Show scene number, title, location, tone
   - API: GET /api/v1/stories/{story_id}/scenes

3. **Add database logging**
   - Agent logs table
   - Execution time tracking
   - Token usage logging

#### Week 3: Storyboard Placeholder + Frontend Polish
1. **Create placeholder storyboard viewer**
   - Display scene information
   - Show which scenes need images

2. **Polish UI**
   - Responsive design
   - Error handling
   - Loading states

### Phase 2: Complete Agent System (Weeks 4-5)

**Goal**: Implement all agents + character continuity + image generation

#### Week 4: Continuity + Director Agents
1. **Character Continuity Agent**
   ```python
   # backend/agents/continuity_agent.py
   class CharacterContinuityAgent:
       def __init__(self, db_session):
           self.db = db_session
       
       async def validate(self, scenes: List[dict]) -> dict:
           violations = []
           
           for i, scene in enumerate(scenes):
               prev_scene = scenes[i-1] if i > 0 else None
               
               # Check character appearance continuity
               # Check object persistence
               # Check time progression
               
               if violation := self._check_violation(scene, prev_scene):
                   violations.append(violation)
           
           return {"violations": violations}
   ```

2. **Director Agent**
   - Cinematic decisions (camera, lighting, style)
   - Reference famous films for style
   - Output JSON with metadata

3. **Store all outputs in DB**
   - Cinematic decisions table
   - Character states table

#### Week 5: Ambiguity Resolution + Prompt Generator
1. **Ambiguity Resolution Agent**
   - Detect ambiguous sections
   - Auto-resolve or ask user
   - Store resolutions

2. **Visual Prompt Generator Agent**
   ```python
   class VisualPromptGeneratorAgent:
       async def generate(self, scene: dict, director_decisions: dict) -> dict:
           # Combine scene info + cinematic decisions
           # Generate optimized prompts for Flux/SDXL
           # Include seed for determinism
           
           prompt = f"""
           Create image prompt for this scene:
           Scene: {scene['title']}
           Emotional Tone: {scene['emotional_tone']}
           Camera: {director_decisions['camera']['angle']}
           Lighting: {director_decisions['lighting']['intensity']}
           ...
           """
   ```

3. **Integrate image generation API**
   - Use Replicate for Flux
   - Or use local setup for SDXL

### Phase 3: Polish & Deployment (Week 6)

**Goal**: Evaluation agent + full observability + deploy

#### Week 6: Evaluation + Observability
1. **Evaluation Agent**
   - Score alignment, continuity, quality
   - Flag issues

2. **Agent Trace Viewer**
   - Frontend component showing execution
   - Tree view of agent decisions
   - Timing analysis

3. **Deploy**
   - Push to Vercel (frontend)
   - Deploy to Railway/Render (backend)
   - Configure environments
   - Test in production

---

## 3. CODE STRUCTURE & TEMPLATES

### 3.1 Agent Template

Every agent should follow this pattern:

```python
# backend/agents/template_agent.py
from typing import Any, Dict, List
from pydantic import BaseModel, Field, ValidationError
from anthropic import Anthropic
import logging

logger = logging.getLogger(__name__)

class AgentInputSchema(BaseModel):
    # Define input schema
    narrative: str = Field(..., description="Input narrative")

class AgentOutputSchema(BaseModel):
    # Define output schema
    result: Dict[str, Any]

class TemplateAgent:
    """
    Description of what this agent does.
    
    Inputs: [Description]
    Outputs: [Description]
    """
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.temperature = 0.3
        self.max_tokens = 2000
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method.
        
        Args:
            input_data: Input following AgentInputSchema
        
        Returns:
            Output following AgentOutputSchema
        """
        # Validate input
        validated_input = AgentInputSchema(**input_data)
        
        # Build prompt
        prompt = self._build_prompt(validated_input)
        
        # Call API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse output
        output = self._parse_response(response)
        
        # Validate output
        validated_output = AgentOutputSchema(**output)
        
        return validated_output.model_dump()
    
    def _build_prompt(self, input_data: AgentInputSchema) -> str:
        """Build the system prompt."""
        return f"""
        You are [Agent name]. Your task is [Task description].
        
        RULES:
        1. Return ONLY valid JSON
        2. Follow the schema exactly
        3. [Other rules]
        
        INPUT:
        {input_data.json()}
        
        OUTPUT FORMAT:
        {AgentOutputSchema.schema_json(indent=2)}
        """
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse Claude response."""
        text = response.content[0].text
        
        # Extract JSON
        import json
        try:
            # Try direct parsing
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown
            import re
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Could not parse response: {text}")
```

### 3.2 API Endpoint Template

```python
# backend/api/routes/template.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models import Story, NarrativeState
from agents.parser_agent import NarrativeParserAgent
import logging

router = APIRouter(prefix="/api/v1", tags=["template"])
logger = logging.getLogger(__name__)

@router.post("/stories")
async def create_story(
    request: StoryCreateRequest,
    db: Session,
    background_tasks: BackgroundTasks
):
    """Create a new story and start processing."""
    
    try:
        # 1. Save story to DB
        story = Story(
            title=request.title,
            raw_input=request.input,
            input_type=request.input_type,
            status="processing"
        )
        db.add(story)
        db.commit()
        
        # 2. Add async task
        background_tasks.add_task(process_story, story.id, db)
        
        return {
            "story_id": story.id,
            "status": "processing",
            "created_at": story.created_at
        }
    
    except Exception as e:
        logger.error(f"Error creating story: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_story(story_id: str, db: Session):
    """Background task to process story."""
    
    try:
        # 1. Get story
        story = db.query(Story).filter(Story.id == story_id).first()
        
        # 2. Run parser agent
        parser = NarrativeParserAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
        parsed = await parser.execute({"narrative": story.raw_input})
        
        # 3. Save narrative state
        narrative_state = NarrativeState(
            story_id=story_id,
            parsed_data=parsed
        )
        db.add(narrative_state)
        
        # 4. Update story status
        story.status = "scenes_planned"
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing story: {e}")
        story.status = "failed"
        story.error_message = str(e)
        db.commit()
```

### 3.3 Frontend Component Template

```typescript
// frontend/components/TemplateComponent.tsx
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface TemplateComponentProps {
  storyId: string;
}

export function TemplateComponent({ storyId }: TemplateComponentProps) {
  const [data, setData] = useState(null);
  
  // Fetch data
  const { data: fetchedData, isLoading, error } = useQuery({
    queryKey: ['story', storyId],
    queryFn: () => api.getStory(storyId),
    refetchInterval: 2000
  });
  
  useEffect(() => {
    if (fetchedData) setData(fetchedData);
  }, [fetchedData]);
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div className="p-4">
      {/* Component content */}
      <h2>{data?.title}</h2>
    </div>
  );
}
```

---

## 4. KEY IMPLEMENTATION PATTERNS

### 4.1 Determinism Pattern

To ensure deterministic outputs:

```python
# Always set fixed temperature
temperature = 0.3

# Use seeded random for anything non-LLM
import random
seed = hash(story_input + provided_seed) % (2**31)
random.seed(seed)

# Store seed with output for reproducibility
output = {
    "result": actual_result,
    "seed": seed,
    "model": "claude-3-5-sonnet-20241022"
}
```

### 4.2 State Management Pattern

```python
# Central narrative state (immutable)
class NarrativeState(BaseModel):
    story_id: str
    characters: List[Character]  # Immutable
    scenes: List[Scene]          # Immutable
    continuity_log: List[dict]   # All changes logged
    timestamp: datetime

# Each agent receives copy, produces new state
async def process_story(narrative: dict):
    state = NarrativeState(**narrative)
    
    # Agent 1
    state = await parser_agent.execute(state)
    save_state(state)  # Save after each step
    
    # Agent 2
    state = await planner_agent.execute(state)
    save_state(state)
    
    # ... etc
```

### 4.3 Error Handling & Retry Pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_agent(agent, input_data):
    try:
        return await agent.execute(input_data)
    except (APIError, ValidationError) as e:
        logger.error(f"Agent failed: {e}")
        raise

# In main process
try:
    result = await call_agent(parser_agent, narrative)
except Exception as e:
    # Log failure
    story.status = "failed"
    story.error_message = str(e)
    db.commit()
```

### 4.4 Logging & Observability Pattern

```python
# Every agent logs its execution
import json
from datetime import datetime

async def execute_with_logging(agent: Agent, input_data: dict) -> dict:
    start_time = datetime.now()
    
    try:
        output = await agent.execute(input_data)
        
        # Log successful execution
        log_entry = {
            "agent": agent.name,
            "status": "success",
            "input": input_data,
            "output": output,
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "timestamp": start_time.isoformat()
        }
        
    except Exception as e:
        log_entry = {
            "agent": agent.name,
            "status": "failed",
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "timestamp": start_time.isoformat()
        }
    
    # Save to database
    agent_log = AgentLog(
        story_id=input_data['story_id'],
        agent_name=agent.name,
        log_json=log_entry
    )
    db.add(agent_log)
    db.commit()
    
    return output
```

---

## 5. TESTING STRATEGY

### 5.1 Unit Tests

```python
# tests/test_agents.py
import pytest
from agents.parser_agent import NarrativeParserAgent

@pytest.mark.asyncio
async def test_parser_agent_extracts_characters():
    agent = NarrativeParserAgent(api_key="test-key")
    
    narrative = "Alice and Bob are friends..."
    
    result = await agent.execute({"narrative": narrative})
    
    assert len(result['characters']) >= 2
    assert any(c['name'] == 'Alice' for c in result['characters'])

@pytest.mark.asyncio
async def test_parser_agent_flags_ambiguities():
    agent = NarrativeParserAgent(api_key="test-key")
    
    ambiguous_narrative = "He looked away silently."
    
    result = await agent.execute({"narrative": ambiguous_narrative})
    
    assert len(result['ambiguities']) > 0
```

### 5.2 Integration Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_story():
    response = client.post(
        "/api/v1/stories",
        json={
            "title": "Test Story",
            "input": "A retired astronaut receives radio messages...",
            "input_type": "text"
        }
    )
    
    assert response.status_code == 202
    assert "story_id" in response.json()

def test_get_story(story_id):
    response = client.get(f"/api/v1/stories/{story_id}")
    
    assert response.status_code == 200
    assert response.json()['title'] == "Test Story"
```

### 5.3 Determinism Tests

```python
# tests/test_determinism.py
@pytest.mark.asyncio
async def test_parser_determinism():
    """Same input + seed = same output"""
    
    narrative = "A woman opens a letter and begins crying..."
    seed = 42
    
    agent = NarrativeParserAgent(api_key="test-key")
    
    # Run 3 times
    outputs = []
    for _ in range(3):
        result = await agent.execute({
            "narrative": narrative,
            "seed": seed
        })
        outputs.append(result)
    
    # Verify all identical
    assert outputs[0] == outputs[1] == outputs[2]
```

---

## 6. DEBUGGING & TROUBLESHOOTING

### 6.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Agent returns invalid JSON | LLM not following schema | Increase detail in system prompt, use lower temperature |
| Determinism breaks | Random state not seeded | Check temperature, seed all randomness |
| Images don't match scenes | Prompts too generic | Add more detail to visual prompt generator |
| Continuity violations | State not persisted | Ensure state saved after each agent |
| API timeouts | Long-running agents | Increase timeout, optimize prompts |

### 6.2 Debugging Checklist

- [ ] Check agent logs: `GET /api/v1/stories/{id}/trace`
- [ ] Verify database state: `SELECT * FROM narrative_states WHERE story_id = '...'`
- [ ] Test agent in isolation: Run agent CLI directly
- [ ] Check Anthropic API usage: Review in dashboard
- [ ] Verify image generation: Check generated prompts in database

### 6.3 Useful CLI Commands

```bash
# Test parser agent
python -m cli.test_parser "A retired astronaut..."

# Check database
psql cinegraph_ai -c "SELECT * FROM stories LIMIT 5;"

# View agent logs
python -m cli.show_trace story_id

# Regenerate story
python -m cli.regenerate_story story_id --seed 42

# Check image generation
python -m cli.test_image_gen scene_id
```

---

## Next Steps

1. Start with **Phase 1 Week 1**: Database + Parser Agent
2. Test each component as you build
3. Use the predefined test stories frequently
4. Track execution with logs
5. Deploy incrementally

Good luck! 🚀
