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

## 5. Funcionalidades
- [x] Verifica se o morador está em risco de alagamento
- [x] Calcula a rota a pé até o abrigo mais próximo disponível (ignora abrigos lotados)
- [x] Evita ruas alagadas
- [x] Cache de rotas por usuário, com invalidação quando o alagamento muda
- [x] Tabela da rota (terminal e CSV)
- [x] Mapa desenhado com matplotlib, com rota numerada, trechos alagados, abrigos e casa
- [x] Consulta de endereço digitado pelo usuário

## 6. Como executar
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

## 7. Estrutura do projeto
```
rota_segura/
├── rota_segura.py  
└── README.md
```

## 8. Limitações e próximos passos
- [Dados e alagamentos são simulados; na versão real viriam dos sensores IoT]
- [Mapa fictício; na versão real usaria o mapa da cidade]
- [Ideias futuras: Melhorar a qualidade do mapa para se tornar mais fácil para as pessoas que possuem uma certa limitação de se localizarem.]