import agent_tracer_sdk as ats
from google import genai
from google.genai import types

class SREAssistantAgent:
    def __init__(self):
        # O Client nativo do Gemini (será interceptado pelo SDK)
        self.client = genai.Client()
        self.model_name = "gemini-2.0-flash"

    @ats.trace(kind="tool")
    def consultar_logs_banco_dados(self, erro: str) -> str:
        """Simula uma busca nos logs do banco de dados baseada em uma mensagem de erro."""
        if "timeout" in erro.lower():
            return "LOGS DB: As consultas SQL estao demorando mais de 30s. Lock detectado na tabela 'users'."
        return "LOGS DB: Nenhuma anomalia grave detectada nas ultimas horas."

    @ats.trace(kind="agent")
    def start(self, mensagem: str) -> str:
        """Ponto de entrada do agente."""
        
        # 1. Agente usa uma Tool para coletar contexto
        contexto_logs = self.consultar_logs_banco_dados(mensagem)
        
        prompt_final = f"""Você é um Assistente SRE (Site Reliability Engineer) sênior.
O desenvolvedor reportou este incidente: "{mensagem}"

Contexto adicional extraído das ferramentas do sistema:
{contexto_logs}

Por favor, forneça um diagnóstico do problema e os próximos passos para resolver.
"""
        # 2. Chama o LLM
        # Como o ats.init(auto_instrument=True) foi chamado no main.py, 
        # essa chamada ao generate_content já vai pro BigQuery automaticamente!
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt_final,
        )

        return response.text
