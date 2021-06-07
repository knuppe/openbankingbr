
import os
import re
import platform
import time 
import requests
import json 

from requests.exceptions import (
    InvalidURL,
    Timeout
)

from hashlib import md5
from datetime import date, datetime

from . import __version__
from .errors import (
    OpenBankingException,
    RequiredFieldException
)

def get(d: dict, key: str, required: bool = False, valueType: type = None):
    """
    Obtem dados de um objeto JSON usando a chave especificada.

    Caso especificado `valueType` será realizado o cast garantindo que o valor está
    no formato esperado. Caso o cast de algum erro e o `required` for `True`, será 
    retornado um erro.
    """
    cur = None
    try:
        keys = key.split('.')
        cur = d
        for k in keys:
            cur = cur[k]
            if cur is None:
                return None

        if valueType == None:
            return cur
        elif valueType == list:
            if type(cur) == list:
                return cur
            
            raise ValueError()
        elif valueType == dict:
            if type(cur) == dict:
                return cur

            raise ValueError()
        elif valueType == int:
            return int(cur)
        elif valueType == str:
            return str(cur)
        elif valueType == float:
            return float(cur)
        elif valueType == bool:
            return bool(cur)
        elif valueType == date:
            return datetime.fromisoformat(cur)
        elif valueType == datetime:
            # Haha! Na documentação falam que a data tem que ser seguir a especificação RFC-3339
            # porém, o próprio exemplo que dão não é uma data válida no formato...
            #
            # https://openbanking-brasil.github.io/areadesenvolvedor-fase1/#introducao-tipos-de-dados-comuns
            #
            if type(cur) == str:
                cur = str(cur).rstrip('Z')
                
            return datetime.fromisoformat(cur)
        else:
            raise NotImplementedError("Tipo de dados solicitado é desconhecido")
        
    except ValueError:
        if required:
            raise RequiredFieldException(f"O tipo do valor atual '{type(cur)}' não está no formato esperado '{valueType}'") from None
    except KeyError:
        pass
        if required:
            raise RequiredFieldException(f'Campo obrigatório não encontrado nos dados: {key}') from None
    except Exception as e:
        if required:
            raise e from None

    return None

def getInt(dados: dict, key: str) -> int:
    """
    Procura a chave especificada nos dados, caso encontrado algum valor é extraido somente
    os caracteres reconhecidos como digitos então é retornado um cast de int do valor.

    Caso ocorra um erro ou o valor seja inválido, será retornado `None`.

    Essa função é usada pois em vários campos as financeiras formatam os valores, mesmo
    com a documentação orientando a não formatar. 
    """
    value = get(dados, key, valueType=str, required=False)
    if value == None:
        return None

    try:
        value = re.sub(r'\D', '', value)
        return int(value)
    except:
        return None

def fetchUrl(url: str, cacheDir: str = None) -> dict:
    """
    Executa a requisição dos dados da URL.

    Caso especificado o cacheDir, os dados de cada request serão armazenado sem arquivos JSON
    de cache por um dia.
    """
    if cacheDir != None:
        if not os.path.exists(cacheDir):
            os.makedirs(cacheDir)
        elif not os.path.isdir(cacheDir):
            raise OpenBankingException("O cacheDir especificado não é um diretório.")

        cacheEntry = os.path.join(cacheDir, md5(url.encode('ascii')).hexdigest() + '.json')
        if file_was_created_today(cacheEntry):
            with open(cacheEntry, 'r', encoding='utf8') as f:
                return json.load(f)
        else:
            if os.path.exists(cacheEntry):
                os.remove(cacheEntry)
            
    try:
        res = requests.get(url, headers = {
            'User-Agent': f'OpenBankingBR/{__version__}; (+https://github.com/knuppe/openbankingbr)'
        })

        data = res.json()

        if data != None:
            with open(cacheEntry, 'w', encoding='utf8') as f:
                json.dump(data, f, ensure_ascii=False)

        return data
    except InvalidURL:
        # ignora pois o erro é meio grotesco.
        return None
    except ValueError:
        raise OpenBankingException("O conteúdo retornado pelo endpoint não possui um JSON válido.") from None
    except:
        return None

def fetchUrlPages(url: str, cacheDir: str = None) -> dict:
    """
    Realiza a requisição dos dados da API retornando os dados paginados.

    https://openbanking-brasil.github.io/areadesenvolvedor-fase1/#introducao-paginacao
    """
    root = fetchUrl(url, cacheDir = cacheDir)
    if root == None or not type(root) == dict:
        return None
    
    if not 'data' in root:
        return None

    data = root['data']
    data['endPoint'] = url

    yield data

    # Knuppe: Olha, poderia usar o total de paginas que tá no meta... mas
    #         como sei que as financeiras vão fazer api bugada, vou olhar 
    #         somente se existe o link de próxima pagina e boa.
    #
    # totalPages = get(root, 'meta.totalPages', valueType=int, required=False)
    # totalPages = 1 if totalPages is None else totalPages
    # for page in range(2, totalPages):

    nextPage = get(root, 'links.next', valueType=str, required = False)
    if nextPage is None:
        return
    
    if nextPage.startswith('http://') or nextPage.startswith('https://'):
        yield fetchUrlPages(nextPage, cacheDir = cacheDir)
    

def file_was_created_today(file: str) -> bool:
    if not os.path.exists(file):
        return False

    ctime: datetime
    
    if platform.system() == "Windows":
        ctime = datetime.fromtimestamp(os.path.getctime(file))
    else:
        stat = os.stat(file)
        try:
            ctime = datetime.fromtimestamp(stat.st_birthtime)
        except:
            ctime = datetime.fromtimestamp(stat.st_mtime)

    return ctime.date() == date.today()
