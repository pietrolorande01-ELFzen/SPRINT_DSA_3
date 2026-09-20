# SPRINT_DSA_3

# Totem de Recarga Inteligente — Sistema de Gerenciamento de Estação de Recarga

Sprint 3 — Estruturas de Dados e Algoritmos (DSA)




Pietro Lorande da Silva — RM 569125
Ana Beatriz Berbel Marini - RM 574176
Gustavo Bonamico Piccoli - RM 569984
Julian Nayde Moncoski - RM 572603
Marcelo Francisco Josafá Ribeiro Martins - RM 573905
Maria Eduarda Medeiros Lemos - RM 574094


## O que é este projeto

Simulador de um totem de recarga de veículos elétricos que evoluiu de um simulador de sessão única (Sprints anteriores) para um **sistema de gerenciamento de múltiplas sessões**, aplicando estruturas de dados, listas, funções, algoritmos de busca e ordenação implementados manualmente, e análise de complexidade (Big-O).

Além dos requisitos da Sprint 3, o simulador reproduz de forma realista:
- comunicação via protocolo **OCPP** (BootNotification, StartTransaction, MeterValues, StopTransaction etc.);
- comunicação via **Modbus RTU** (leitura/escrita de registradores do controlador de carga);
- controle dinâmico de potência (bandeira tarifária + nível da bateria do sistema Lynx + sessões simultâneas);
- integração simulada com sistemas externos (nuvem GoodWe, validação de pagamento, consulta à ANEEL).

## Requisitos

- Python 3.8 ou superior
- Nenhuma dependência externa — usa apenas a biblioteca padrão (`time`, `random`, `json`, `os`, `uuid`, `datetime`)

Não é necessário `pip install` nada.

## Como executar

```bash
python SPRINT_DSA_Completa.py
```

ou, dependendo do sistema:

```bash
python3 SPRINT_DSA_Completa.py
```

O programa roda em loop pelo terminal até que a opção **8 - Sair** seja escolhida.

## Arquivos gerados automaticamente

| Arquivo | Quando é criado | Conteúdo |
|---|---|---|
| `sessoes_totem.json` | Sempre que uma sessão é cadastrada ou a lista é ordenada | Todas as sessões registradas, em formato JSON, para persistência entre execuções |
| `relatorio_AAAAMMDD_HHMMSS.txt` | Ao escolher a opção **7 - Exportar relatório** | Relatório completo em texto: detalhamento de cada sessão + consolidado geral |

Na primeira execução, o `sessoes_totem.json` ainda não existe — o programa cria a lista vazia normalmente e o arquivo aparece após a primeira sessão ser salva.

## Menu principal

```
1 - Iniciar nova sessão de recarga
2 - Ver relatório consolidado
3 - Ver detalhes de uma sessão (por posição)
4 - Buscar sessão (sequencial / binária)
5 - Ordenar sessões (Bubble Sort)
6 - Estatísticas da estação
7 - Exportar relatório para .txt
8 - Sair
```

### O que cada opção faz

- **1 — Nova sessão**: coleta nome e token do usuário, simula boot OCPP, detecção do veículo, cálculo de potência disponível, a recarga minuto a minuto, pagamento e fechamento da sessão. Ao final, a sessão é salva na lista e no JSON.
- **2 — Relatório consolidado**: mostra totais (energia, receita, tempo), ticket médio, marca de carro mais recorrente, distribuição por bandeira tarifária e as últimas 5 sessões.
- **3 — Detalhes por posição**: lista as sessões numeradas e exibe o relatório completo da escolhida.
- **4 — Buscar sessão**: permite escolher entre busca sequencial ou binária pelo campo `id` (veja detalhes no item "Algoritmos" abaixo).
- **5 — Ordenar sessões**: ordena a lista real de sessões (in-place) por ID, energia, custo ou tempo de recarga, crescente ou decrescente, usando Bubble Sort.
- **6 — Estatísticas**: total de sessões, energia total, faturamento, ticket médio, maior e menor consumo registrado.
- **7 — Exportar relatório**: gera um `.txt` com o detalhamento de todas as sessões e o consolidado geral.
- **8 — Sair**: encerra o programa.

## Estrutura de dados

Cada sessão é representada como um **dicionário** (não uma classe), com mais de 20 campos — dados do usuário, veículo, protocolo OCPP, tarifação, pagamento e integração em nuvem. O motivo dessa escolha (em vez de classe) está detalhado no relatório técnico (`Relatorio_Sprint3_DSA.docx`), seção 2.

Todas as sessões ficam em uma lista:

```python
sessoes = []
sessoes.append(nova_sessao)
```

## Algoritmos implementados manualmente

Nenhum destes usa função pronta do Python (`sort()`, `sorted()`, funções de busca prontas):

- **Busca sequencial** — `busca_sequencial()` — percorre a lista posição a posição. Complexidade **O(n)**.
- **Busca binária** — `busca_binaria()` — exige lista ordenada por `id`; por isso, ao escolher essa opção no menu, o programa ordena uma **cópia** da lista (preservando a ordem original) antes de buscar. Complexidade **O(log n)**.
- **Bubble Sort** — `bubble_sort_sessoes()` — ordena por ID, energia, custo ou tempo, crescente ou decrescente, com otimização de parada antecipada (flag `trocou`). Complexidade **O(n²)** no pior/médio caso, **O(n)** no melhor caso (lista já ordenada).

A explicação detalhada de cada complexidade, com trechos de código e comparação prática entre os algoritmos, está no relatório técnico, seções 4 a 7.

## Validações de entrada

- Nome e token não podem ser vazios/inválidos (`texto_obrigatorio`, `token_valido` — token precisa ter exatamente 6 dígitos).
- Tempo de recarga precisa ser um número inteiro positivo (`numero_positivo`), com tratamento de `ValueError`.
- Respostas de sim/não e opções de menu são validadas em loop até uma entrada válida ser digitada.
- ID da sessão é gerado automaticamente e energia/custo são resultado de cálculo da simulação — por isso não há risco de ID duplicado ou valores negativos digitados manualmente (decisão de arquitetura explicada no relatório, seção 3).

