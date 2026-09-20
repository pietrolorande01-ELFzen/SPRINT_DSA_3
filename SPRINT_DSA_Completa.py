# ==========================================================
# TOTEM DE RECARGA INTELIGENTE (VALIDAÇÃO COMPLETA)
# ==========================================================

import time
import random
import json
import os
import uuid
from datetime import datetime, timedelta

# ----------------------------------------------------------
# BANCO DE SESSOES
# ----------------------------------------------------------

ARQUIVO_SESSOES = "sessoes_totem.json"

def carregar_sessoes():
    if os.path.exists(ARQUIVO_SESSOES):
        try:
            with open(ARQUIVO_SESSOES, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_sessoes(sessoes):
    with open(ARQUIVO_SESSOES, "w", encoding="utf-8") as f:
        json.dump(sessoes, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------
# TIMESTAMP PADRAO HH:MM:SS
# ----------------------------------------------------------

def ts():
    """Retorna timestamp atual no formato HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


# ----------------------------------------------------------
# SIMULACAO OCPP / MODBUS
# ----------------------------------------------------------

# Tipos de mensagem OCPP simulados
OCPP_MSG_TYPES = {
    2: "CALL",
    3: "CALLRESULT",
    4: "CALLERROR",
}

OCPP_ACTIONS = [
    "BootNotification",
    "Heartbeat",
    "StatusNotification",
    "StartTransaction",
    "MeterValues",
    "StopTransaction",
    "RemoteStartTransaction",
    "DataTransfer",
]

MODBUS_FUNCTION_CODES = {
    0x03: "Read Holding Registers",
    0x04: "Read Input Registers",
    0x06: "Write Single Register",
    0x10: "Write Multiple Registers",
}

def _gerar_message_id():
    return str(uuid.uuid4())[:8].upper()

def ocpp_send(action, payload, msg_type=2):
    """Simula envio de frame OCPP."""
    msg_id = _gerar_message_id()
    frame = [msg_type, msg_id, action, payload]
    print(f"   [OCPP][{ts()}] SEND  >> [{msg_type}, \"{msg_id}\", \"{action}\", {json.dumps(payload)}]")
    time.sleep(0.4)
    return msg_id

def ocpp_recv(msg_id, action, resposta):
    """Simula recebimento de frame OCPP (CALLRESULT)."""
    frame = [3, msg_id, resposta]
    print(f"   [OCPP][{ts()}] RECV  << [3, \"{msg_id}\", {json.dumps(resposta)}]")
    time.sleep(0.3)

def ocpp_error(msg_id, code, descricao):
    """Simula frame de erro OCPP (CALLERROR)."""
    frame = [4, msg_id, code, descricao, {}]
    print(f"   [OCPP][{ts()}] ERROR << [4, \"{msg_id}\", \"{code}\", \"{descricao}\"]")
    time.sleep(0.2)

def modbus_write(device_id, func_code, register, value):
    """Simula escrita Modbus RTU."""
    fc_name = MODBUS_FUNCTION_CODES.get(func_code, "Unknown")
    print(f"   [MODBUS][{ts()}] TX >> ID={device_id:#04x} FC={func_code:#04x}({fc_name}) REG={register:#06x} VAL={value}")
    time.sleep(0.3)

def modbus_read(device_id, func_code, register, qty):
    """Simula leitura Modbus RTU e retorna valor simulado."""
    fc_name = MODBUS_FUNCTION_CODES.get(func_code, "Unknown")
    valor = random.randint(0, 65535)
    print(f"   [MODBUS][{ts()}] TX >> ID={device_id:#04x} FC={func_code:#04x}({fc_name}) REG={register:#06x} QTY={qty}")
    time.sleep(0.3)
    print(f"   [MODBUS][{ts()}] RX << ID={device_id:#04x} DATA=[{valor:#06x}] ({valor})")
    return valor

def ocpp_boot_notification():
    """Sequencia de boot do chargepoint via OCPP."""
    print(f"\n[OCPP] Iniciando BootNotification...")
    mid = ocpp_send("BootNotification", {
        "chargePointVendor": "GoodWe",
        "chargePointModel": "LUMOS-T1",
        "firmwareVersion": "2.4.1",
        "chargePointSerialNumber": "LMS-2026-0042",
    })
    ocpp_recv(mid, "BootNotification", {
        "status": "Accepted",
        "currentTime": datetime.now().isoformat(),
        "heartbeatInterval": 300,
    })

def ocpp_status_notification(session_id, status):
    """Notifica status do conector."""
    mid = ocpp_send("StatusNotification", {
        "connectorId": 1,
        "errorCode": "NoError",
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "info": f"Session {session_id}",
    })
    ocpp_recv(mid, "StatusNotification", {"status": "Accepted"})

def ocpp_start_transaction(session_id, id_tag, meter_start):
    """Inicia transacao OCPP."""
    print(f"\n[OCPP] Iniciando transacao — {session_id}...")
    mid = ocpp_send("StartTransaction", {
        "connectorId": 1,
        "idTag": id_tag,
        "meterStart": meter_start,
        "timestamp": datetime.now().isoformat(),
    })
    transaction_id = random.randint(10000, 99999)
    ocpp_recv(mid, "StartTransaction", {
        "transactionId": transaction_id,
        "idTagInfo": {"status": "Accepted", "expiryDate": "2027-01-01T00:00:00Z"},
    })
    return transaction_id

def ocpp_meter_values(transaction_id, energia_kwh, potencia_kw):
    """Envia leituras de medidor durante a recarga."""
    mid = ocpp_send("MeterValues", {
        "connectorId": 1,
        "transactionId": transaction_id,
        "meterValue": [{
            "timestamp": datetime.now().isoformat(),
            "sampledValue": [
                {"value": str(round(energia_kwh * 1000)), "measurand": "Energy.Active.Import.Register", "unit": "Wh"},
                {"value": str(round(potencia_kw * 1000)), "measurand": "Power.Active.Import", "unit": "W"},
            ]
        }]
    })
    ocpp_recv(mid, "MeterValues", {"status": "Accepted"})

def ocpp_stop_transaction(transaction_id, meter_stop, motivo="EVDisconnected"):
    """Encerra transacao OCPP."""
    print(f"\n[OCPP] Encerrando transacao {transaction_id}...")
    mid = ocpp_send("StopTransaction", {
        "transactionId": transaction_id,
        "meterStop": meter_stop,
        "timestamp": datetime.now().isoformat(),
        "reason": motivo,
    })
    ocpp_recv(mid, "StopTransaction", {"idTagInfo": {"status": "Accepted"}})

def modbus_init_charger(potencia_kw):
    """Inicializa controlador de carga via Modbus."""
    print(f"\n[MODBUS] Configurando controlador de carga...")
    modbus_write(0x01, 0x06, 0x0100, int(potencia_kw * 10))   # set max power (x10)
    modbus_write(0x01, 0x06, 0x0101, 1)                        # enable charging
    modbus_read (0x01, 0x03, 0x0200, 1)                        # read status register

def modbus_read_meter():
    """Le registros do medidor de energia via Modbus."""
    print(f"\n[MODBUS] Lendo medidor de energia...")
    v  = modbus_read(0x01, 0x04, 0x0300, 1)
    i  = modbus_read(0x01, 0x04, 0x0301, 1)
    kw = modbus_read(0x01, 0x04, 0x0302, 1)
    return v, i, kw

def modbus_limit_power(novo_limite_kw):
    """Ajusta limite de potencia dinamicamente via Modbus."""
    print(f"\n[MODBUS] Ajustando limite de potencia para {novo_limite_kw} kW...")
    modbus_write(0x01, 0x06, 0x0100, int(novo_limite_kw * 10))
    modbus_write(0x01, 0x10, 0x0110, int(novo_limite_kw * 10))
    status = modbus_read(0x01, 0x03, 0x0200, 1)
    print(f"   [MODBUS][{ts()}] Confirmacao de limite aplicado: status={status:#06x}")


# ----------------------------------------------------------
# CONTROLE DE POTENCIA (LYNX POWER MANAGER)
# ----------------------------------------------------------

LIMITES_POTENCIA = {
    "Verde":    {"max_kw": 22.0},
    "Amarela":  {"max_kw": 15.0},
    "Vermelha": {"max_kw": 7.4},
}

POTENCIA_MAX_TOTEM_KW  = 22.0
MAX_SESSOES_SIMULTANEAS = 2

def calcular_potencia_disponivel(bandeira, sessoes_ativas, bateria_lynx):
    limite = LIMITES_POTENCIA[bandeira]["max_kw"]
    avisos = []

    # Regra 1: Bateria Lynx critica
    if bateria_lynx < 20:
        limite = min(limite, 3.7)
        avisos.append("ATENCAO: Bateria Lynx critica — modo carga lenta ativado")
    elif bateria_lynx < 40:
        limite = min(limite, 7.4)
        avisos.append("ATENCAO: Bateria Lynx baixa — potencia reduzida")

    # Regra 2: Multiplas sessoes simultaneas — limitacao de carga
    if sessoes_ativas > MAX_SESSOES_SIMULTANEAS:
        excedente = sessoes_ativas - MAX_SESSOES_SIMULTANEAS
        fator = max(1 - (0.10 * excedente), 0.5)
        limite_antes = limite
        limite *= fator
        avisos.append(
            f"ATENCAO: {sessoes_ativas} sessoes ativas — carga limitada "
            f"({limite_antes:.1f} kW -> {limite:.1f} kW, fator {fator*100:.0f}%)"
        )

    limite = min(limite, POTENCIA_MAX_TOTEM_KW)
    kwh_por_min = limite / 60
    return round(limite, 2), round(kwh_por_min, 4), avisos


# ----------------------------------------------------------
# INTEGRACAO COM SISTEMA EXTERNO (API simulada)
# ----------------------------------------------------------

def simular_requisicao_api(sistema, payload, delay=1.5):
    print(f"   -> Conectando a {sistema}...", end=" ", flush=True)
    time.sleep(delay)
    if random.random() < 0.10:
        print("TIMEOUT")
        return False, {"erro": "Timeout — sistema externo indisponivel"}
    print("OK")
    return True, {"status": "200 OK", "timestamp": datetime.now().isoformat(), "payload": payload}

def registrar_sessao_cloud(sessao):
    print(f"\n[INTEGRACAO EXTERNA] Registrando sessao na nuvem GoodWe...")
    ok, resp = simular_requisicao_api(
        "GoodWe Cloud",
        {"session_id": sessao["id"], "energia_kwh": sessao["energia_kwh"]},
    )
    if ok:
        sessao["cloud_sync"] = True
        sessao["cloud_timestamp"] = resp["timestamp"]
    else:
        sessao["cloud_sync"] = False
        print("   Sincronizacao adiada — dados salvos localmente.")
    return sessao

def validar_pagamento_externo(forma, valor):
    sistemas = {
        "1": ("Banco Central (PIX)", 2.0),
        "2": ("Bradesco Boletos",    3.0),
        "3": ("Sem Parar TAG",       1.5),
        "4": ("Mastercard/Visa",     2.0),
    }
    nome_sistema, delay = sistemas.get(forma, ("Desconhecido", 2.0))
    print(f"\n[INTEGRACAO EXTERNA] Validando pagamento — {nome_sistema}")
    ok, _ = simular_requisicao_api(nome_sistema, {"valor": valor}, delay)
    if not ok:
        print("   Tentando novamente...")
        ok, _ = simular_requisicao_api(nome_sistema, {"valor": valor}, delay)
    return ok

def consultar_grid_aneel(bandeira):
    print(f"\n[INTEGRACAO EXTERNA] Consultando status da rede ANEEL...")
    ok, _ = simular_requisicao_api("ANEEL Grid", {"bandeira": bandeira}, 1.0)
    if ok:
        estabilidade = random.choice(["Estavel", "Estavel", "Oscilante"])
        print(f"   Rede: {estabilidade} | Bandeira confirmada: {bandeira}")
        return estabilidade
    return "Desconhecida"


# ----------------------------------------------------------
# VALIDACAO DE ENTRADAS
# ----------------------------------------------------------

def texto_obrigatorio(msg):
    while True:
        valor = input(msg).strip()
        if valor != "":
            return valor
        print("Entrada invalida. Nao pode ser vazio.\n")

def numero_positivo(msg):
    while True:
        try:
            valor = int(input(msg))
            if valor > 0:
                return valor
            print("Digite um numero maior que zero.\n")
        except:
            print("Digite apenas numeros inteiros.\n")

def token_valido():
    while True:
        token = input("Digite seu token (6 digitos): ").strip()
        if token.isdigit() and len(token) == 6:
            return token
        print("Token invalido. Deve conter exatamente 6 numeros.\n")

def sim_ou_nao(msg):
    while True:
        valor = input(msg).strip().lower()
        if valor in ["s", "n"]:
            return valor
        print("Digite apenas 's' ou 'n'.\n")

def escolher_pagamento():
    while True:
        print("\nForma de pagamento:")
        print("1 - PIX (Governo)")
        print("2 - BOLETO")
        print("3 - TAG (Sem Parar)")
        print("4 - Cartao (Aproximacao)")
        op = input("Escolha: ").strip()
        if op in ["1", "2", "3", "4"]:
            return op
        print("Opcao invalida. Escolha de 1 a 4.\n")


# ----------------------------------------------------------
# GERADOR DE ID DE SESSAO
# ----------------------------------------------------------

def gerar_id_sessao(sessoes):
    return f"SESS-{len(sessoes) + 1:04d}-{datetime.now().strftime('%Y%m%d')}"


# ----------------------------------------------------------
# RELATORIOS
# ----------------------------------------------------------

def _linhas_sessao(s):
    """Retorna lista de linhas de texto para uma sessao."""
    linhas = []
    linhas.append("=" * 65)
    linhas.append("                RELATORIO DA SESSAO")
    linhas.append("=" * 65)
    linhas.append(f"ID Sessao.............: {s['id']}")
    linhas.append(f"Usuario...............: {s['usuario']}")
    linhas.append(f"Token.................: {s['token']}")
    linhas.append("")
    linhas.append("--- TEMPO ---")
    linhas.append(f"Inicio................: {s['inicio']}")
    linhas.append(f"Fim...................: {s['fim']}")
    linhas.append(f"Duracao...............: {s['duracao_min']} min")
    linhas.append("")
    linhas.append("--- VEICULO ---")
    linhas.append(f"Marca.................: {s['marca_carro']}")
    linhas.append(f"Bateria inicial.......: {s['bateria_inicial']}%")
    linhas.append(f"Bateria final.........: {s['bateria_final']:.1f}%")
    linhas.append("")
    linhas.append("--- ENERGIA ---")
    linhas.append(f"Bateria Lynx..........: {s['bateria_lynx']}%")
    linhas.append(f"Fonte.................: {s['fonte']}")
    linhas.append(f"Bandeira..............: {s['bandeira']}")
    linhas.append(f"Potencia max. usada...: {s['potencia_kw']} kW")
    linhas.append(f"Estabilidade rede.....: {s['estabilidade_rede']}")
    linhas.append(f"OCPP Transaction ID...: {s.get('ocpp_transaction_id', 'N/A')}")
    linhas.append("")
    linhas.append("--- COBRANCA ---")
    linhas.append(f"Valor energia.........: R$ {s['valor_energia']:.2f}")
    linhas.append(f"Taxa fixa.............: R$ {s['taxa_fixa']:.2f}")
    linhas.append(f"TOTAL.................: R$ {s['valor_total']:.2f}")
    linhas.append(f"Forma pagamento.......: {s['pagamento_nome']}")
    linhas.append(f"Pagamento confirmado..: {'Sim' if s['pagamento_ok'] else 'Falhou'}")
    linhas.append("")
    linhas.append("--- INTEGRACAO CLOUD ---")
    linhas.append(f"Sincronizado GoodWe...: {'Sim' if s.get('cloud_sync') else 'Pendente'}")
    if s.get("cloud_timestamp"):
        linhas.append(f"Timestamp cloud.......: {s['cloud_timestamp']}")
    linhas.append("=" * 65)
    return linhas

def gerar_relatorio_sessao(sessao):
    """Imprime o relatorio detalhado de uma sessao."""
    print()
    for linha in _linhas_sessao(sessao):
        print(linha)

def gerar_relatorio_geral(sessoes):
    """Imprime relatorio consolidado de todas as sessoes."""
    if not sessoes:
        print("\nNenhuma sessao registrada ainda.")
        return

    total_energia   = sum(s["energia_kwh"] for s in sessoes)
    total_valor     = sum(s["valor_total"]  for s in sessoes)
    total_duracao   = sum(s["duracao_min"]  for s in sessoes)
    marcas_count    = {}
    bandeiras_count = {}

    for s in sessoes:
        marcas_count[s["marca_carro"]] = marcas_count.get(s["marca_carro"], 0) + 1
        bandeiras_count[s["bandeira"]] = bandeiras_count.get(s["bandeira"], 0) + 1

    marca_top = max(marcas_count, key=marcas_count.get)

    print("\n" + "=" * 65)
    print("         RELATORIO CONSOLIDADO — TODAS AS SESSOES")
    print("=" * 65)
    print(f"Total de sessoes......: {len(sessoes)}")
    print(f"Energia total.........: {total_energia:.2f} kWh")
    print(f"Receita total.........: R$ {total_valor:.2f}")
    print(f"Tempo total de uso....: {total_duracao} min ({total_duracao/60:.1f} h)")
    print(f"Ticket medio..........: R$ {total_valor/len(sessoes):.2f}")
    print(f"Marca mais recorrente.: {marca_top} ({marcas_count[marca_top]}x)")

    print("\n--- DISTRIBUICAO POR BANDEIRA ---")
    for b, qtd in bandeiras_count.items():
        print(f"  {b:<10}: {qtd} sessao(oes)")

    print("\n--- ULTIMAS 5 SESSOES ---")
    for s in sessoes[-5:]:
        print(f"  [{s['id']}] {s['usuario']:<15} {s['energia_kwh']:.1f} kWh  R$ {s['valor_total']:.2f}  {s['inicio']}")

    nao_sync = sum(1 for s in sessoes if not s.get("cloud_sync"))
    if nao_sync:
        print(f"\n  ATENCAO: {nao_sync} sessao(oes) pendentes de sincronizacao com GoodWe Cloud.")

    print("=" * 65)

def exportar_relatorio_txt(sessoes):
    """Gera arquivo .txt completo com todas as sessoes e o relatorio consolidado."""
    if not sessoes:
        print("\nNenhuma sessao para exportar.")
        return

    print("\nAguarde, gerando relatorio...")
    time.sleep(3)

    nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    linhas = []

    linhas.append("=" * 65)
    linhas.append("    TOTEM DE RECARGA INTELIGENTE — RELATORIO EXPORTADO")
    linhas.append(f"    Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    linhas.append(f"    Total de sessoes: {len(sessoes)}")
    linhas.append("=" * 65)
    linhas.append("")

    # Secao 1: Relatorio individual de cada sessao
    linhas.append("=" * 65)
    linhas.append("  SECAO 1 — DETALHAMENTO POR SESSAO")
    linhas.append("=" * 65)
    for s in sessoes:
        linhas.extend(_linhas_sessao(s))
        linhas.append("")

    # Secao 2: Consolidado
    total_energia   = sum(s["energia_kwh"] for s in sessoes)
    total_valor     = sum(s["valor_total"]  for s in sessoes)
    total_duracao   = sum(s["duracao_min"]  for s in sessoes)
    marcas_count    = {}
    bandeiras_count = {}
    for s in sessoes:
        marcas_count[s["marca_carro"]] = marcas_count.get(s["marca_carro"], 0) + 1
        bandeiras_count[s["bandeira"]] = bandeiras_count.get(s["bandeira"], 0) + 1
    marca_top = max(marcas_count, key=marcas_count.get)

    linhas.append("=" * 65)
    linhas.append("  SECAO 2 — CONSOLIDADO GERAL")
    linhas.append("=" * 65)
    linhas.append(f"Total de sessoes......: {len(sessoes)}")
    linhas.append(f"Energia total.........: {total_energia:.2f} kWh")
    linhas.append(f"Receita total.........: R$ {total_valor:.2f}")
    linhas.append(f"Tempo total de uso....: {total_duracao} min ({total_duracao/60:.1f} h)")
    linhas.append(f"Ticket medio..........: R$ {total_valor/len(sessoes):.2f}")
    linhas.append(f"Marca mais recorrente.: {marca_top} ({marcas_count[marca_top]}x)")
    linhas.append("")
    linhas.append("Distribuicao por bandeira:")
    for b, qtd in bandeiras_count.items():
        linhas.append(f"  {b:<10}: {qtd} sessao(oes)")
    linhas.append("")
    nao_sync = sum(1 for s in sessoes if not s.get("cloud_sync"))
    if nao_sync:
        linhas.append(f"ATENCAO: {nao_sync} sessao(oes) pendentes de sincronizacao.")
    linhas.append("=" * 65)
    linhas.append("Fim do relatorio.")

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"Relatorio exportado com sucesso: {nome_arquivo}")
    return nome_arquivo


# ----------------------------------------------------------
# BUSCA DE SESSOES (Sprint 3 - DSA)
# ----------------------------------------------------------
# Ambas as buscas trabalham pelo campo "id" da sessao.
# Nao utilizam nenhuma funcao pronta de busca do Python.

def busca_sequencial(sessoes, id_procurado):
    """
    Busca sequencial pelo campo 'id'.
    Percorre a lista posicao a posicao ate encontrar o ID ou
    chegar ao final.

    Complexidade: O(n) — no pior caso (ID no final ou inexistente)
    percorre todas as n posicoes da lista.
    """
    for i in range(len(sessoes)):
        if sessoes[i]["id"] == id_procurado:
            return i
    return -1


def busca_binaria(sessoes, id_procurado):
    """
    Busca binaria pelo campo 'id'.
    PRE-REQUISITO: a lista precisa estar ordenada por 'id' antes
    de chamar esta funcao (ver bubble_sort_sessoes com criterio='id').

    Complexidade: O(log n) — a cada iteracao o espaco de busca
    e dividido pela metade.
    """
    baixo = 0
    alto = len(sessoes) - 1

    while baixo <= alto:
        meio = (baixo + alto) // 2
        id_meio = sessoes[meio]["id"]

        if id_meio == id_procurado:
            return meio
        elif id_meio < id_procurado:
            baixo = meio + 1
        else:
            alto = meio - 1

    return -1


def menu_buscar_sessao(sessoes):
    """Submenu de busca: permite escolher o algoritmo e exibe o resultado."""
    if not sessoes:
        print("\nNenhuma sessao registrada.")
        return

    print("\n--- BUSCAR SESSAO ---")
    print("1 - Busca sequencial")
    print("2 - Busca binaria")
    algoritmo = input("Escolha o algoritmo: ").strip()

    if algoritmo not in ("1", "2"):
        print("Opcao invalida.")
        return

    id_procurado = texto_obrigatorio("Digite o ID da sessao (ex: SESS-0001-20260831): ")

    if algoritmo == "1":
        print(f"\n[{ts()}] Executando busca sequencial...")
        idx = busca_sequencial(sessoes, id_procurado)
    else:
        # A busca binaria exige a lista ordenada por id.
        # Ordena uma copia para nao alterar a ordem original sem o usuario pedir.
        sessoes_ordenadas = sessoes[:]
        bubble_sort_sessoes(sessoes_ordenadas, "id")
        print(f"\n[{ts()}] Lista ordenada por ID para permitir busca binaria...")
        print(f"[{ts()}] Executando busca binaria...")
        idx = busca_binaria(sessoes_ordenadas, id_procurado)
        if idx != -1:
            gerar_relatorio_sessao(sessoes_ordenadas[idx])
            return

    if idx == -1:
        print(f"\nNenhuma sessao encontrada com o ID '{id_procurado}'.")
    else:
        gerar_relatorio_sessao(sessoes[idx])


# ----------------------------------------------------------
# ORDENACAO DE SESSOES (Sprint 3 - DSA)
# ----------------------------------------------------------
# Bubble Sort implementado manualmente. Nao utiliza sort()/sorted().

CRITERIOS_ORDENACAO = {
    "1": ("id",           "ID"),
    "2": ("energia_kwh",  "Energia consumida"),
    "3": ("valor_total",  "Custo total"),
    "4": ("duracao_min",  "Tempo de recarga"),
}

def bubble_sort_sessoes(sessoes, criterio, decrescente=False):
    """
    Ordena a lista de sessoes in-place por 'criterio' usando Bubble Sort.

    A cada passagem, compara pares adjacentes e troca quando estao
    fora de ordem. Usa uma flag 'trocou' para encerrar mais cedo
    caso a lista ja esteja ordenada (melhora o caso medio/melhor,
    mas o pior caso continua O(n^2)).

    Complexidade: O(n^2) — dois lacos aninhados, cada um percorrendo
    ate n posicoes (o segundo diminui a cada passagem externa).
    """
    n = len(sessoes)

    for i in range(n):
        trocou = False
        for j in range(n - 1 - i):
            valor_a = sessoes[j][criterio]
            valor_b = sessoes[j + 1][criterio]

            fora_de_ordem = (valor_a > valor_b) if not decrescente else (valor_a < valor_b)

            if fora_de_ordem:
                sessoes[j], sessoes[j + 1] = sessoes[j + 1], sessoes[j]
                trocou = True

        if not trocou:
            break

    return sessoes


def menu_ordenar_sessoes(sessoes):
    """Submenu de ordenacao: escolhe criterio e direcao, ordena in-place."""
    if not sessoes:
        print("\nNenhuma sessao registrada.")
        return

    print("\n--- ORDENAR SESSOES ---")
    print("1 - ID")
    print("2 - Energia consumida")
    print("3 - Custo total")
    print("4 - Tempo de recarga")
    escolha = input("Ordenar por: ").strip()

    if escolha not in CRITERIOS_ORDENACAO:
        print("Opcao invalida.")
        return

    criterio, nome_criterio = CRITERIOS_ORDENACAO[escolha]
    direcao = sim_ou_nao("Ordem decrescente? (s/n): ")
    decrescente = (direcao == "s")

    print(f"\n[{ts()}] Ordenando por {nome_criterio} ({'decrescente' if decrescente else 'crescente'}) com Bubble Sort...")
    bubble_sort_sessoes(sessoes, criterio, decrescente)
    salvar_sessoes(sessoes)
    print("Sessoes ordenadas com sucesso.\n")

    print("--- SESSOES ORDENADAS ---")
    for s in sessoes:
        print(f"  [{s['id']}] {s['usuario']:<15} {s['energia_kwh']:.2f} kWh  "
              f"R$ {s['valor_total']:.2f}  {s['duracao_min']} min")


# ----------------------------------------------------------
# ESTATISTICAS DETALHADAS (Sprint 3 - DSA)
# ----------------------------------------------------------

def mostrar_estatisticas(sessoes):
    """Calcula e exibe as estatisticas obrigatorias da Sprint 3."""
    if not sessoes:
        print("\nNenhuma sessao registrada ainda.")
        return

    total_sessoes = len(sessoes)
    energia_total = sum(s["energia_kwh"] for s in sessoes)
    faturamento   = sum(s["valor_total"] for s in sessoes)
    ticket_medio  = faturamento / total_sessoes

    # Maior e menor consumo (busca manual, sem max()/min() prontos do Python)
    maior_consumo = sessoes[0]["energia_kwh"]
    menor_consumo = sessoes[0]["energia_kwh"]
    for s in sessoes:
        if s["energia_kwh"] > maior_consumo:
            maior_consumo = s["energia_kwh"]
        if s["energia_kwh"] < menor_consumo:
            menor_consumo = s["energia_kwh"]

    print("\n" + "=" * 65)
    print("               ESTATISTICAS DA ESTACAO")
    print("=" * 65)
    print(f"Sessoes realizadas....: {total_sessoes}")
    print(f"Energia fornecida.....: {energia_total:.2f} kWh")
    print(f"Faturamento...........: R$ {faturamento:.2f}")
    print(f"Ticket medio..........: R$ {ticket_medio:.2f}")
    print(f"Maior consumo.........: {maior_consumo:.2f} kWh")
    print(f"Menor consumo.........: {menor_consumo:.2f} kWh")
    print("=" * 65)


# ----------------------------------------------------------
# SESSAO DE RECARGA (fluxo principal)
# ----------------------------------------------------------

NOMES_PAGAMENTO = {"1": "PIX (Governo)", "2": "Boleto", "3": "TAG Sem Parar", "4": "Cartao"}

def executar_sessao(sessoes):
    """Executa uma sessao completa de recarga."""

    print("\n" + "-" * 65)
    print("          NOVA SESSAO DE RECARGA")
    print("-" * 65)

    # Entradas do usuario
    nome  = texto_obrigatorio("Nome do usuario: ")
    token = token_valido()

    inicio    = datetime.now()
    id_sessao = gerar_id_sessao(sessoes)
    print(f"\nID da sessao: {id_sessao}")
    print(f"Horario de inicio: {inicio.strftime('%H:%M:%S')}")

    # Boot OCPP
    print("\nAguarde, inicializando protocolo de comunicacao...")
    time.sleep(3)
    ocpp_boot_notification()

    # Simulacao do veiculo
    print(f"\n[{ts()}] Conectando ao veiculo...")
    time.sleep(1)

    marcas           = ["BYD", "Tesla", "Volvo", "BMW", "Renault", "Hyundai", "Kia"]
    marca_carro      = random.choice(marcas)
    bateria_inicial  = random.randint(10, 80)
    capacidade_total = 100
    energia_necessaria = capacidade_total - bateria_inicial
    tempo_sugerido   = int(energia_necessaria / 0.5)

    print(f"\n--- VEICULO DETECTADO [{ts()}] ---")
    print(f"Marca: {marca_carro}")
    print(f"Bateria atual: {bateria_inicial}%")
    print(f"Tempo sugerido: {tempo_sugerido} min")

    escolha = sim_ou_nao("\nAceitar sugestao? (s/n): ")
    tempo = tempo_sugerido if escolha == "s" else numero_positivo("Tempo desejado (minutos): ")

    # Sistema energetico
    bateria_lynx = random.randint(10, 100)
    bandeiras    = ["Verde", "Amarela", "Vermelha"]
    bandeira     = random.choice(bandeiras)

    if bandeira == "Verde":
        taxa_bandeira = 0
    elif bandeira == "Amarela":
        taxa_bandeira = 0.20
    else:
        taxa_bandeira = 0.45

    if bateria_lynx >= 70:
        tarifa = 0.85
        fonte  = "Solar + Bateria Lynx"
    elif bateria_lynx >= 40:
        tarifa = 1.20
        fonte  = "Bateria Parcial"
    else:
        tarifa = 1.60 + taxa_bandeira
        fonte  = "Rede de Apoio"

    hora = inicio.hour
    if 0 <= hora < 6:
        tarifa -= 0.20
    tarifa = max(tarifa, 0)

    taxa_fixa = 15

    # Controle de potencia com limitacao por sessoes simultaneas
    sessoes_ativas = len([s for s in sessoes if s.get("ativa", False)])
    potencia_kw, kwh_por_min, avisos = calcular_potencia_disponivel(
        bandeira, sessoes_ativas, bateria_lynx
    )

    print(f"\n--- CONTROLE DE POTENCIA [{ts()}] ---")
    print(f"Bandeira tarifaria...: {bandeira}")
    print(f"Sessoes ativas.......: {sessoes_ativas}")
    print(f"Bateria Lynx.........: {bateria_lynx}%")
    print(f"Potencia disponivel..: {potencia_kw} kW")
    for av in avisos:
        print(f"  {av}")

    # Modbus: configura controlador de carga
    modbus_init_charger(potencia_kw)

    # Consulta ANEEL
    estabilidade_rede = consultar_grid_aneel(bandeira)

    # Pagamento
    pagamento = escolher_pagamento()
    valor_est = energia_necessaria * kwh_por_min * tarifa * 60 + taxa_fixa

    print("\nAguarde, processando pagamento...")
    time.sleep(3)

    pag_ok = validar_pagamento_externo(pagamento, round(valor_est, 2))
    if not pag_ok:
        print("\nPagamento nao confirmado. Sessao cancelada.")
        return None

    formas_pag = {"1": "PIX", "2": "Boleto", "3": "TAG", "4": "Cartao"}
    print(f"\nPagamento aprovado via {formas_pag[pagamento]}. [{ts()}]")

    # OCPP: inicio de transacao
    id_tag = token
    meter_start = 0
    transaction_id = ocpp_start_transaction(id_sessao, id_tag, meter_start)
    ocpp_status_notification(id_sessao, "Charging")

    # Recarga
    print(f"\nAguarde, iniciando recarga...\n")
    time.sleep(3)
    print(f"[{ts()}] Recarga iniciada — {potencia_kw} kW\n")

    energia_total     = 0
    tempo_atual       = inicio
    meter_values_tick = 0

    for minuto in range(1, tempo + 1):
        energia_total += kwh_por_min
        tempo_atual   += timedelta(minutes=1)
        print(f"{tempo_atual.strftime('%H:%M:%S')} | {energia_total:.3f} kWh | {potencia_kw} kW")

        # Envia MeterValues a cada 10 minutos via OCPP
        meter_values_tick += 1
        if meter_values_tick >= 10:
            ocpp_meter_values(transaction_id, energia_total, potencia_kw)
            modbus_read_meter()
            meter_values_tick = 0

        time.sleep(0.03)

    fim          = tempo_atual
    bateria_final = min(100, bateria_inicial + (energia_total / (capacidade_total / 100)))

    # OCPP: encerrar transacao
    ocpp_stop_transaction(transaction_id, int(energia_total * 1000))
    ocpp_status_notification(id_sessao, "Available")

    # Modbus: desabilitar carga
    modbus_write(0x01, 0x06, 0x0101, 0)

    # Valores
    valor_energia = energia_total * tarifa
    valor_total   = valor_energia + taxa_fixa

    # Monta objeto da sessao
    sessao = {
        "id":                  id_sessao,
        "ativa":               False,
        "usuario":             nome,
        "token":               token,
        "inicio":              inicio.strftime("%H:%M:%S"),
        "fim":                 fim.strftime("%H:%M:%S"),
        "duracao_min":         tempo,
        "marca_carro":         marca_carro,
        "bateria_inicial":     bateria_inicial,
        "bateria_final":       round(bateria_final, 1),
        "bateria_lynx":        bateria_lynx,
        "fonte":               fonte,
        "bandeira":            bandeira,
        "potencia_kw":         potencia_kw,
        "energia_kwh":         round(energia_total, 3),
        "estabilidade_rede":   estabilidade_rede,
        "tarifa":              round(tarifa, 2),
        "taxa_fixa":           taxa_fixa,
        "valor_energia":       round(valor_energia, 2),
        "valor_total":         round(valor_total, 2),
        "pagamento":           pagamento,
        "pagamento_nome":      NOMES_PAGAMENTO[pagamento],
        "pagamento_ok":        pag_ok,
        "ocpp_transaction_id": transaction_id,
    }

    # Integracao Cloud
    sessao = registrar_sessao_cloud(sessao)

    # Relatorio da sessao
    print("\nAguarde, gerando relatorio da sessao...")
    time.sleep(3)
    gerar_relatorio_sessao(sessao)

    return sessao


# ----------------------------------------------------------
# MENU PRINCIPAL
# ----------------------------------------------------------

def menu_principal():
    print("=" * 65)
    print("""
██╗░░░░░██╗░░░██╗███╗░░░███╗░█████╗░░██████╗
██║░░░░░██║░░░██║████╗░████║██╔══██╗██╔════╝
██║░░░░░██║░░░██║██╔████╔██║██║░░██║╚█████╗░
██║░░░░░██║░░░██║██║╚██╔╝██║██║░░██║░╚═══██╗
███████╗╚██████╔╝██║░╚═╝░██║╚█████╔╝██████╔╝
╚══════╝░╚═════╝░╚═╝░░░░░╚═╝░╚════╝░╚═════╝░""")
    print("=" * 65)
    print()
    print("  -  TOTEM DE CARREGAMENTO INTELIGENTE  -")
    print()
    print("  迈向更绿色的未来 — Rumo a um Futuro mais Verde")
    print()

    sessoes = carregar_sessoes()

    while True:
        print("\n" + "=" * 65)
        print("  MENU PRINCIPAL")
        print("=" * 65)
        print(f"  Sessoes registradas: {len(sessoes)}")
        print()
        print("  1 - Iniciar nova sessao de recarga")
        print("  2 - Ver relatorio consolidado")
        print("  3 - Ver detalhes de uma sessao (por posicao)")
        print("  4 - Buscar sessao (sequencial / binaria)")
        print("  5 - Ordenar sessoes (Bubble Sort)")
        print("  6 - Estatisticas da estacao")
        print("  7 - Exportar relatorio para .txt")
        print("  8 - Sair")
        print()

        op = input("  Escolha uma opcao: ").strip()

        if op == "1":
            sessao = executar_sessao(sessoes)
            if sessao:
                sessoes.append(sessao)
                salvar_sessoes(sessoes)
                print(f"\nSessao {sessao['id']} salva com sucesso.")

        elif op == "2":
            print("\nAguarde, carregando relatorio...")
            time.sleep(3)
            gerar_relatorio_geral(sessoes)

        elif op == "3":
            if not sessoes:
                print("\nNenhuma sessao registrada.")
                continue
            print("\nSessoes disponiveis:")
            for i, s in enumerate(sessoes):
                print(f"  {i+1}. [{s['id']}] {s['usuario']} — {s['inicio']}")
            try:
                idx = int(input("\nNumero da sessao: ")) - 1
                if 0 <= idx < len(sessoes):
                    print("\nAguarde, carregando detalhes da sessao...")
                    time.sleep(3)
                    gerar_relatorio_sessao(sessoes[idx])
                else:
                    print("Numero invalido.")
            except:
                print("Entrada invalida.")

        elif op == "4":
            menu_buscar_sessao(sessoes)

        elif op == "5":
            menu_ordenar_sessoes(sessoes)

        elif op == "6":
            mostrar_estatisticas(sessoes)

        elif op == "7":
            nome = exportar_relatorio_txt(sessoes)
            if nome:
                print(f"Arquivo disponivel em: {os.path.abspath(nome)}")

        elif op == "8":
            print("\nSistema encerrado. Desenvolvido por FIAP / GoodWe\n")
            break

        else:
            print("Opcao invalida. Escolha de 1 a 8.")


# ----------------------------------------------------------
# PONTO DE ENTRADA
# ----------------------------------------------------------

if __name__ == "__main__":
    menu_principal()
