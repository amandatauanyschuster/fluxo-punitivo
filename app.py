import os
from flask import Flask, request, jsonify, send_from_directory
from supabase import create_client, Client
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.')

# Configuração do Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Rota para abrir a página inicial (index.html)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/aplicar_punicao', methods=['POST'])
def aplicar_punicao():
    dados = request.json
    colaborador_id = dados['colaborador_id']
    
    # 1. Buscar a PRIMEIRA punição ativa do fluxo
    res = supabase.table("punicoes")\
        .select("*")\
        .eq("colaborador_id", colaborador_id)\
        .eq("fluxo_ativo", True)\
        .order("data_aplicacao", desc=False)\
        .limit(1)\
        .execute()

    punicoes_ativas = res.data
    
    if punicoes_ativas:
        # Corrige a leitura da data removendo o fuso horário para cálculo
        data_str = punicoes_ativas[0]['data_aplicacao'].replace('Z', '').split('+')[0]
        primeira_data = datetime.fromisoformat(data_str)
        
        # 2. Verificar se passou 6 meses (180 dias)
        if datetime.now() > (primeira_data + timedelta(days=180)):
            # RESETAR FLUXO: Desativar punições antigas
            supabase.table("punicoes")\
                .update({"fluxo_ativo": False})\
                .eq("colaborador_id", colaborador_id)\
                .execute()
            
            tipo_nova = "Advertência 1"
        else:
            # CONTINUAR FLUXO
            res_total = supabase.table("punicoes").select("*").eq("colaborador_id", colaborador_id).eq("fluxo_ativo", True).execute()
            total = len(res_total.data)
            hierarquia = ["Advertência 1", "Advertência 2", "Suspensão", "Justa Causa"]
            tipo_nova = hierarquia[min(total, 3)]
    else:
        tipo_nova = "Advertência 1"

    # 3. Inserir nova punição
    nova_punicao = {
        "colaborador_id": colaborador_id,
        "tipo": tipo_nova,
        "fluxo_ativo": True
    }
    supabase.table("punicoes").insert(nova_punicao).execute()

    return jsonify({"mensagem": f"Sucesso! Aplicada: {tipo_nova}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
