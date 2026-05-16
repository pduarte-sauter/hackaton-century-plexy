import os
import agent_tracer_sdk as ats

# 1. INICIALIZA O SDK ANTES DE QUALQUER COISA
ats.init(
    service_name="sre-assistant-adk",
    export_mode="cloud",  # Envia direto para Cloud Logging e Cloud Trace
    auto_instrument=True  # Intercepta as chamadas do google-genai
)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import SREAssistantAgent

app = FastAPI(title="SRE Assistant API")
root_agent = SREAssistantAgent()

class PerguntaRequest(BaseModel):
    mensagem: str

@app.get("/")
def home():
    return {"status": "online", "plataforma": "AgentTracer Demo"}

@app.post("/diagnosticar")
async def diagnosticar(request: PerguntaRequest):
    try:
        # A chamada ao start() sera rastreada pelo @ats.trace que colocaremos la
        resposta = root_agent.start(request.mensagem)
        
        return {
            "agente": "SRE Assistant",
            "diagnostico": resposta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Agente: {str(e)}")

# Para rodar localmente de forma facil:
if __name__ == "__main__":
    import uvicorn
    # A porta padrão do Cloud Run é 8080
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
