# CentryPlexy SDK

## 🎯 Escopo da Aplicação
O **CentryPlexy SDK** é uma biblioteca de observabilidade (Observability SDK) desenvolvida para monitorar e avaliar Agentes de Inteligência Artificial. Ele abstrai a complexidade do OpenTelemetry para fornecer uma interface simples e direta ("plug and play") com o intuito de rastrear métricas fundamentais de agentes de IA, tais como:
- Latência e tempo de execução.
- Consumo de tokens (input, output, total).
- Entradas (prompts) e Saídas (completions).
- Uso de ferramentas de apoio (tools/function calling).
- Captura de erros e status das chamadas.

O SDK suporta envio de telemetria estruturada para múltiplos destinos de avaliação e monitoramento, incluindo console local, Google Cloud (Logging/BigQuery via log router), MLflow (via API customizada) e endpoints OTLP genéricos.

---

## 🚀 Como Rodar

### Pré-requisitos
- Python 3.8+
- Recomenda-se a criação de um ambiente virtual (venv).

### 1. Instalação
Instale a biblioteca e suas dependências localmente através do `setup.py` incluído na raiz do projeto:

```bash
pip install -e .
```

### 2. Configuração de Variáveis de Ambiente
O SDK é amplamente customizável via variáveis de ambiente. Defina as seguintes variáveis conforme seu ambiente de execução (no arquivo `.env` ou nas variáveis do SO):

```env
AGENT_TRACER_SERVICE=meu-agente-ia
AGENT_TRACER_VERSION=0.1.0

# Opções de exportação: console, cloud, otlp
AGENT_TRACER_EXPORT=console  

# Endpoint para integração com MLflow (Opcional)
MLFLOW_API_URL=https://sua-url-api-mlflow/ingest

# Para Google Cloud (Obrigatório se EXPORT_MODE=cloud)
GOOGLE_CLOUD_PROJECT=seu-id-do-projeto
```

### 3. Exemplo de Uso
O SDK permite que você instrumente seus agentes e chamadas de LLM facilmente utilizando *decorators*.

```python
import agent_tracer_sdk as ats

# 1. Inicializa o SDK
ats.init(service_name="meu-agente-demo", export_mode="console", auto_instrument=True)

# 2. Decorator de Agente Principal
@ats.trace(kind="agent")
def executar_agente(pergunta: str):
    print("Processando sua pergunta...")
    return chamar_llm(pergunta)

# 3. Decorator de LLM Subjacente
@ats.trace(kind="llm", model="gemini-2.0-flash", provider="google")
def chamar_llm(prompt: str):
    # Simulação da resposta de um LLM
    resposta_simulada = {
        "text": "Esta é a resposta simulada do modelo.",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20
        }
    }
    
    # Usando a função set_attribute para atualizar os tokens manualmente no span
    ats.set_attribute("agent_tracer.input_tokens", resposta_simulada["usage"]["input_tokens"])
    ats.set_attribute("agent_tracer.output_tokens", resposta_simulada["usage"]["output_tokens"])
    
    return resposta_simulada

if __name__ == "__main__":
    resultado = executar_agente("Qual é o status do sistema?")
    print(f"Resultado: {resultado}")
    
    # IMPORTANTE: Força o envio (flush) de qualquer telemetria pendente
    ats.shutdown()
```

### 4. Executando o Teste de Validação
O projeto inclui um arquivo `test_mlflow.py` que demonstra a captura e o flush de telemetria no console e/ou para a API configurada. Para executá-lo:

```bash
python test_mlflow.py
```
