# Rota Segura – Dynamic Programming

Global Solution Citizen Tech · FIAP · Engenharia de Software

## Integrantes
| Nome | RM |
|---|---|
| Bernardo Yuji Rodriguez Hanashiro | 565266 |
| Matheus Vasques | 563309 |

## 1. A ideia
Moradores de áreas de risco so percebem a gravidade da chuva ou da enchente quando a água já está subindo, fazendo com que sintam desnorteadas e sem ideias do que fazer nesses momentos. O Rota Segura calcula o caminho a pé mais seguro da casa da pessoa até o abrigo mais próximo, evitando ruas alagadas e congestionamentos, visando ajudar a pessoa a chegar em segurança.

**Problema:** Os GPS atuais não calculam a rota contando com as ruas alagadas, levando as pessoas por caminho que por muitas das vezes não é o ideal no momento.

**Solução:** O Rota Segura calcula rotas evitando ruas alagadas, o sistema conta com informações de pluviômetros e medidores de nível de água, que trabalham em conjunto.

**Público-alvo:** O sistema visa chegar em todas as pessoas que moram em zonas de risco.

## 2. Cenário simulado
O programa usa um bairro **fictício**, a "Vila Esperança", só para demonstração:
- [13] ruas nomeadas formando um grid de quadras e um córrego que corta o bairro
- [3] abrigos: [dois abertos e um lotado]
- [3] moradores de teste: [Dona Maria, Seu João e Ana]
- Alagamentos simulando a leitura dos sensores do córrego

Os dados são definidos no código, apenas para simular o funcionamento do sistema, não possui integração com API.

## 3. Quando a rota de fuga aparece
A rota só é gerada para quem realmente precisa. O morador está em risco se:
1. a esquina do endereço está na zona de risco do córrego ([Rua do Córrego e Rua da Escola]); ou
2. alguma rua que chega nessa esquina está alagada no momento.

Caso contrário, o sistema informa "rua sem risco de alagamento" e não gera mapa.

## 4. Algoritmos e técnicas de Programação Dinâmica

### Grafos
As esquinas são nós, ruas são arestas ponderadas pela distância. Ruas alagadas são removidas do grafo, para não fazerem parte do cálculo da rota.

Usamos Dijkstra com fila de prioridade para achar o abrigo mais próximo pelo caminho seguro. Complexidade: O((V+E) log V)

**Por que escolhemos:** O caminho mais rápido e curto em linha reta pode passar por rua alagada, então precisamos do menor caminho no grafo já sem os trechos alagados.

### Memoização
O cache guarda, por usuário, o endereço e o abrigo/ caminho calculado com a chave (usuário, endereço, versão do grafo).

Consultas repetidas não recalculam.

Quando os sensores mudam o alagamento, a versão do grafo muda e o cache é invalidado.

**Por que escolhemos:** Em uma enchente muitos moradores consultam ao mesmo tempo e as mesmas rotas se repetem, então o cache poupa processamento

### Tabulação
Antes de plotar, a rota vira uma tabela estruturada com ordem de parada, local,
latitude, longitude, distância do trecho, distância acumulada e tempo estimado. Cada linha
é calculada a partir da anterior (bottom-up). A tabela é impressa, salva em CSV e depois
usada para desenhar o mapa.

**Por que escolhemos:** Separa o cálculo da visualização e deixa os dados organizados para exportar

## 5. Hipóteses e Considerações da Solução

Para viabilizar a simulação do "Rota Segura" dentro do escopo acadêmico, assumimos as seguintes hipóteses:

### 1. Hipóteses do Modelo Físico e Geográfico
* **Modelo Discreto (Grid):** O bairro fictício "Vila Esperança" foi modelado como um grafo não-direcionado ponderado, onde as esquinas são vértices e as ruas são arestas. Considerou-se a distância euclidiana/linear a pé entre as esquinas.
* **Pontos de Alojamento Limitados:** A capacidade dos abrigos é binária no modelo de decisão (aberto vs. lotado). Abrigos lotados são removidos dinamicamente do conjunto de destinos válidos antes do cálculo de menor caminho.
* **Velocidade de Deslocamento:** Considera-se uma velocidade média padrão de caminhada a pé para estimar o tempo estimado de chegada (ETA) nas tabelas e relatórios.

### 2. Hipóteses de Alagamento e Sensores
* **Atualização em Tempo Real (Simulada):** Assume-se que os dados dos pluviômetros e sensores de nível do córrego mudam de estado de forma síncrona. Quando um limiar de risco é atingido, as arestas correspondentes às ruas afetadas são removidas do grafo.
* **Gatilho de Risco:** O sistema assume que apenas moradores cujos endereços estejam adjacentes às zonas de escoamento do córrego ou rotas de escoamento críticas necessitam de rota de fuga ativa, otimizando o processamento computacional.

### 3. Considerações de Engenharia de Software e Algoritmos
* **Invalidação de Cache por Versão:** O sistema considera que o cache de rotas (Memoização) deve ser invalidado rigidamente sempre que a "versão do grafo" muda (ou seja, quando o estado de alagamento das ruas é alterado pelos sensores). Isso evita que um morador receba uma rota antiga e potencialmente perigosa.
* **Separação de Camadas:** A lógica de cálculo (Dijkstra + Tabulação) é estritamente desacoplada da camada de apresentação (Matplotlib / CLI), permitindo que a mesma rota tabulada seja exportada para CSV ou renderizada visualmente.

## 6. Funcionalidades
- [x] Verifica se o morador está em risco de alagamento
- [x] Calcula a rota a pé até o abrigo mais próximo disponível (ignora abrigos lotados)
- [x] Evita ruas alagadas
- [x] Cache de rotas por usuário, com invalidação quando o alagamento muda
- [x] Tabela da rota (terminal e CSV)
- [x] Mapa desenhado com matplotlib, com rota numerada, trechos alagados, abrigos e casa
- [x] Consulta de endereço digitado pelo usuário

## 7. Como executar
Requisitos: Python e matplotlib.
```
pip install matplotlib
python rota_segura.py
python rota_segura.py --endereco "Rua da Escola, 100"
python rota_segura.py --salvar
```
- Sem argumentos: roda a demonstração com os 3 moradores de teste.
- `--endereco`: consulta um endereço do bairro fictício (o número indica a esquina: 245 = esquina 2).
- `--salvar`: grava os mapas em PNG.

- Nos dados é possível adicionar novos usúarios para que o sistema calcule novos caminhos.

- Apenas é calculado rotas aonde o endereço da pessoa está próximo às márgens do rio.

## 8. Estrutura do projeto
```
rota_segura/
├── rota_segura.py  
└── README.md
```

## 9. Limitações e próximos passos
- [Dados e alagamentos são simulados; na versão real viriam dos sensores IoT]
- [Mapa fictício; na versão real usaria o mapa da cidade]
- [Ideias futuras: Melhorar a qualidade do mapa para se tornar mais fácil para as pessoas que possuem uma certa limitação de se localizarem.]