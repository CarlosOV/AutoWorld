from .llm import ask_llm
from .memory import save_agent
import json

def generate_agent(world_name: str, existing_names: list[str]) -> dict:
    """Generate a new agent with LLM."""
    names_str = ", ".join(existing_names) if existing_names else "ninguno"
    prompt = f"""
Crea un habitante para el mundo llamado "{world_name}".
Habitantes existentes: {names_str}

Responde SOLO con JSON válido, sin markdown:
{{
  "name": "Nombre Apellido",
  "age": 25,
  "occupation": "su trabajo",
  "personality": ["rasgo1", "rasgo2", "rasgo3"],
  "goals": ["objetivo1", "objetivo2"],
  "backstory": "2 oraciones de historia",
  "mood": "neutral",
  "memories": []
}}
"""
    raw = ask_llm(prompt, max_tokens=300)
    # extract JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    save_agent(data["name"], data)
    return data

def agent_react(agent: dict, event: str, world_name: str) -> str:
    """Get agent's reaction to a world event."""
    personality = ", ".join(agent.get("personality", []))
    recent_memories = agent.get("memories", [])[-3:]
    memories_str = "; ".join(recent_memories) if recent_memories else "ninguna"

    prompt = f"""
Eres {agent['name']}, {agent['age']} años, {agent['occupation']} en el mundo {world_name}.
Personalidad: {personality}
Memorias recientes: {memories_str}

Evento que acaba de ocurrir: "{event}"

¿Cómo reaccionas? Responde en 1-2 oraciones en primera persona, como tu personaje.
"""
    return ask_llm(prompt, max_tokens=150)
