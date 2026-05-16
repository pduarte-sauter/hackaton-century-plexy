import agent_tracer_sdk as ats

# Inicializa o SDK (o console exporter vai imprimir na tela, e o MLFlowExporter vai disparar o POST)
ats.init(service_name="teste-mlflow-local", export_mode="console")

@ats.trace(kind="agent")
def agente_teste(mensagem: str):
    """Simula um agente que recebe uma mensagem e dá uma resposta."""
    print("Processando a mensagem...")
    return chamar_llm(mensagem)

@ats.trace(kind="llm", model="gemini-2.0-flash", provider="google")
def chamar_llm(prompt: str):
    """Simula a chamada a um LLM."""
    return {
        "text": "Esta é uma resposta de teste gerada pelo LLM simulado.",
        "usage": {
            "input_tokens": 120,
            "output_tokens": 45
        }
    }

if __name__ == "__main__":
    print("Iniciando teste de envio para o MLflow API...\n")
    
    # 1. Roda a simulação do agente
    resposta = agente_teste("Como o sistema está se comportando?")
    print(f"Resposta gerada: {resposta}\n")
    
    # 2. Desliga o SDK (isso força o flush de qualquer telemetria pendente, disparando o POST)
    print("Finalizando SDK e disparando POST para o MLflow...")
    ats.shutdown()
    
    print("\nFeito! Verifique os logs da sua API no Cloud Run para ver se o payload chegou.")
