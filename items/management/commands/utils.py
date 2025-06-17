import requests


def calcular_icms_aliquota_reduzida(aliquota_id, redbcde):
    """
    Calcula o valor da ICMS Alíquota Reduzida a partir do REDBCDE e da alíquota cheia.

    :param aliquota_id: Alíquota cheia (ex: 18 para 18%)
    :param redbcde: Percentual de redução da base de cálculo (ex: 33.33 para 33,33%)
    :return: Valor da alíquota reduzida (ex: 12.00)
    """
    if aliquota_id == 0:
        return 0  # evitar divisão por zero

    return round(aliquota_id * (1 - redbcde / 100), 2)

def get_access_token_with_auth_code(client_id, client_secret, code):
    """
    Usa o código de autorização (authorization_code) para obter o access_token e o refresh_token.
    Esta função só deve ser usada na primeira execução.
    """
    url = 'https://api.dropbox.com/oauth2/token'
    data = {
        'code': code,
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')

        print('Access Token:', access_token)
        print('Refresh Token:', refresh_token)

        return access_token, refresh_token
    except requests.exceptions.RequestException as e:
        print('Erro ao obter tokens com o código de autorização:', e)
        return None, None

def refresh_access_token(client_id, client_secret, refresh_token):
    """
    Usa o refresh_token para obter um novo access_token.
    """
    url = 'https://api.dropbox.com/oauth2/token'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    try:
        response = requests.post(url, data=data, auth=(client_id, client_secret))
        response.raise_for_status()

        new_access_token = response.json().get('access_token')
        print('Novo token de acesso:', new_access_token)

        return new_access_token
    except requests.exceptions.RequestException as e:
        print('Erro ao atualizar o token de acesso:', e)
        return None

# # Primeira execução: obtenha o refresh_token usando o código de autorização
# client_id = '26a4qxszd8q32h1'
# client_secret = 'psb2blgkbylkv2v'
# authorization_code = 'SEU_AUTHORIZATION_CODE'

# # Descomente esta linha na primeira vez que rodar o código para obter os tokens
# # access_token, refresh_token = get_access_token_with_auth_code(client_id, client_secret, authorization_code)

# # Após a primeira execução, use o refresh_token salvo
# refresh_token = 'SEU_REFRESH_TOKEN_SALVO'

# # Atualize o token de acesso usando o refresh_token
# new_access_token = refresh_access_token(client_id, client_secret, refresh_token)
