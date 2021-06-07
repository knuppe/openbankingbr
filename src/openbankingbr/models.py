from .errors import OpenBankingException, InvalidDataException
from .utils import get, getInt, fetchUrlPages
from .spec import nomeProdutos, chaveCategorias

from typing import List, Iterator, Generator
from datetime import date

import re 

class DataObject():
    """
    Objeto base com informações dos dados retornados de uma api do Open Banking Brasil.
    """
    def __init__(self, openBaking, dados: dict):
        if not isinstance(dados, dict):
            raise InvalidDataException("O parâmetro de dados do objeto não é um dicionário")

        self.openBaking = openBaking
        self.dados      = dados

    @property
    def endPoint(self) -> str:
        """
        Retorna o end-point da API onde os dados do Open Banking foram obtidos.
        """
        if 'endPoint' in self.dados:
            return self.dados['endPoint']
        
        return None

class Participante(DataObject):
    """
    Representa uma empresa participante listada no diretório do Open Banking Brasil.
    """

    def __init__(self, openBaking, data: dict):
        DataObject.__init__(self, openBaking, data)
        
        if not 'AuthorisationServers' in data:
            raise InvalidDataException("AuthorisationServers não está definido nos dados do participante.")
        elif type(data['AuthorisationServers']) != list:
            raise InvalidDataException("AuthorisationServers não é uma lista")

        self._endpoints = list()
        for server in data['AuthorisationServers']:
            if 'ApiResources' in server and isinstance(server['ApiResources'], list):
                for api in server['ApiResources']:
                    if 'ApiDiscoveryEndpoints' in api and isinstance(api['ApiDiscoveryEndpoints'], list):
                        for endPoint in api['ApiDiscoveryEndpoints']: 
                            if 'ApiEndpoint' in endPoint and type(endPoint['ApiEndpoint']) == str:
                                self._endpoints.append(endPoint['ApiEndpoint'])

    @property
    def nome(self) -> str:
        """
        Retorna o nome (OrganisationName) do participante.
        """
        return str(self.dados['OrganisationName'])

    @property
    def cnpj(self) -> int:
        """
        Retorna o CNPJ numérico com base no `RegistrationNumber` do participante.
        """
        res = re.sub(r'[^\d]+', '', self.dados['RegistrationNumber'])
        return 0 if not res else int(res)        

    @property
    def registrationId(self) -> str:
        """
        Retorna a identificação de registro do participante.
        """
        return str(self.dados['RegistrationId'])
    
    @property
    def registrationNumber(self) -> str:
        """
        Retorna o "número" de registro no participante (CNPJ) no formato que a API retorna.

        Note que existem algumas instituições que mandam o CNPJ formatado. Por este motivo existe 
        a propriedade `.cnpj` que retorna um `int` com o valor tratado.
        """
        return get(self.dados, 'RegistrationNumber', valueType=str, required=True)

    @property
    def identificador(self) -> str:
        """
        Retorna o identificador unico do participante.
        """
        return get(self.dados, 'OrganisationId', valueType=str, required=True)

    @property
    def apiEndPoints(self) -> List[str]:
        """
        Retorna uma lista com todos endereços endpoint das API expostas pelo participante.
        """
        return self._endpoints

    @property
    def agencias(self):
        """
        Gera uma lista com todas as agencias (postos de atendimento) do participante no Open Banking Brasil.

        Exemplo de uso:
        ```python
        for agencia in participante.agencias:
            print(agencia.nome)
        ```        
        """
        for endPoint in self._endpoints:
            if not endPoint.endswith('/open-banking/channels/v1/branches'):
                continue

            for page in fetchUrlPages(endPoint, self.openBaking.cacheDir):
                if not 'brand' in page:
                    continue
            
                brand = page['brand']
                if not 'companies' in brand:
                    continue

                for company in brand['companies']:
                    branches = get(company, 'branches', valueType=list, required=True)

                    for branch in branches:
                        branch['endPoint'] = page['endPoint']

                        yield Agencia(self, branch)

            break                         

    @property
    def produtos(self):
        """
        Gera uma lista com todos os produtos oferecidos pelo participante.

        Exemplo de uso:
        ```python
        for produto in participante.produtos:
            print(produto)
        ```
        """

        # 'personal-accounts', 'business-accounts', 'personal-credit-cards', 'business-credit-cards', 'personal-loans', 'business-loans', 'personal-financings', 'business-financings', 'personal-invoice-financings', 'business-invoice-financings', 'personal-unarranged-account-overdraft', 'business-unarranged-account-overdraft', 

        for endPoint in self._endpoints:
            if not '/open-banking/products-services/v1/' in endPoint:
                continue

            keys = [
                "personalAccounts",
                "businessAccounts",
                "personalCreditCards",
                "businessCreditCards",
                "personalLoans",
                "businessLoans",
                "personalFinancings",
                "businessFinancings",
                "personalInvoiceFinancings",
                "businessInvoiceFinancings",
                "personalUnarrangedAccountOverdraft",
                "businessUnarrangedAccountOverdraft",
            ]

            for page in fetchUrlPages(endPoint, self.openBaking.cacheDir):
                if not 'brand' in page:
                    continue
            
                brand = page['brand']
                if not 'companies' in brand:
                    continue

                key = None
                for company in brand['companies']:
                    for k in keys:
                        if not k in company:
                            continue
                        
                        key = k
                        break

                    if key is None:
                        continue

                    if not type(company[key]) == list:
                        continue

                    for item in company[key]:
                        item['endPoint'] = page['endPoint']
                        
                        if 'interestRates' in item and type(item['interestRates']) == list:
                            interestSequence = 0
                            for interestRate in item['interestRates']:
                                interestSequence += 1
                                interestRate['interestSequence'] = interestSequence
                                yield Produto(self, key, item, interestRate)

                        elif 'interest' in item and type(item['interest']) == dict:             # falta de padrão da api é foda...
                            if 'rates' in item['interest'] and type(item['interest']['rates']) == list:
                                interestSequence = 0
                                for interestRate in item['interest']['rates']:
                                    interestSequence += 1
                                    interestRate['interestSequence'] = interestSequence
                                    yield Produto(self, key, item, interestRate)
                        else:
                            yield Produto(self, key, item)
    @property
    def status(self) -> str:
        """
        Retorna o status do registro do diretório da organização.
        """
        return get(self.dados, 'Status', valueType=str, required=True)

class Agencia(DataObject):
    """
    Represnta uma agencia (Posto de Atendimento) de um participante do Open Banking Brasil.
    """

    def __init__(self, participante, data: dict):
        DataObject.__init__(self, participante.openBaking, data)

        assert(isinstance(participante, Participante))

        self._participante = participante

    @property
    def tipo(self) -> str:
        """
        Retorna o tipo da agência, segundo a regulamentação do Bacen, na Resolução Nº 4072, de 26 de
        abril de 2012: agência de instituições financeiras e demais instituições, autorizadas
        a funcionar pelo Banco Central do Brasil, destinada à prática das atividades para as 
        quais a instituição esteja regularmente habilitada.
        """
        return get(self.dados, 'identification.type', valueType=str)

    @property
    def codigo(self) -> int:
        """
        Retorna o código identificador da agência. Ex. '3006','3035', '1382', '2516', '2856'.
        """
        return getInt(self.dados, 'identification.code')

    @property
    def digitoVerificador(self) -> str:
        """
        Retorna o dígito verificador do código da agência.
        """
        digito = get(self.dados, 'identification.checkDigit', valueType=str)
        return None if digito == 'NA' else digito

    @property
    def nome(self) -> str:
        """
        Retorna o nome da agência.
        """
        return get(self.dados, 'identification.name', valueType=str)

    @property
    def servicos(self) -> List[str]:
        """
        Retorna uma lista com os códigos dos serviços oferecidos na agência.
        """
        items = list()
        servicecs = get(self.dados, 'services', valueType=list, required=False)
        if servicecs != None:
            for service in servicecs:
                code = get(service, 'code', valueType=str)
                if code:
                    items.append(code)

        return items
    
    @property
    def acessoAoPublico(self) -> bool:
        """
        Indica se a instalação da agência tem acesso restrito a clientes. Se `False` o acesso é restrito aos clientes.
        """
        return get(self.dados, 'availability.isPublicAccessAllowed', valueType=bool) == True

    @property
    def endereco(self) -> str:
        """
        Retorna o endereço onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.address', valueType=str, required=False)

    @property
    def enderecoComplemento(self) -> str:
        """
        Retorna o complemento do endereço onde a agência está localizada.
        """
        valor = get(self.dados, 'postalAddress.additionalInfo', valueType=str, required=False)
        return None if valor == 'NA' else valor

    @property
    def cep(self) -> int:
        """
        Retorna o CEP onde a agência está localizada.
        """
        return getInt(self.dados, 'postalAddress.postCode')

    @property
    def cidade(self) -> str:
        """
        Retorna a cidade onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.townName', valueType=str, required=False)

    @property
    def uf(self) -> str:
        """
        Retorna o estado onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.countrySubDivision', valueType=str, required=False)

    @property
    def bairro(self) -> str:
        """
        Retorna o bairro onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.districtName', valueType=str, required=False)

    @property
    def codigoIBGE(self) -> int:
        """
        Retorna o código do IBGE da cidade onde a agência está localizada.
        """
        return getInt(self.dados, 'postalAddress.ibgeCode')

    @property
    def latitude(self) -> float:
        """
        Retorna a latitude onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.geographicCoordinates.latitude', valueType=float, required=False)

    @property
    def longitude(self) -> float:
        """
        Retorna a longitude onde a agência está localizada.
        """
        return get(self.dados, 'postalAddress.geographicCoordinates.longitude', valueType=float, required=False)

    @property
    def telefone(self) -> str:
        """
        Retorna o telefone da agência.

        Note que este campo é construido com regras priorizando um telefone fixo depois telefone móvel.
        """
        phones = get(self.dados, 'phones', valueType=list, required=False)
        if phones is None:
            return None
        
        for tipo in ['FIXO', 'MOVEL']:
            for phone in phones:
                if get(phone, 'type') == tipo:
                    valor = ""
                    if 'countryCallingCode' in phone:
                        i = getInt(phone, 'countryCallingCode')
                        if i != None:
                            valor += i.__str__()

                    if 'areaCode' in phone:
                        i = getInt(phone, 'areaCode').__str__()
                        if i != None:
                            valor += i.__str__()
                    
                    if 'number' in phone:
                        i = getInt(phone, 'number').__str__()
                        if i != None:
                            valor += i.__str__()
                
                    if len(valor) > 3:
                        return valor

        return None


class Servico(DataObject):
    """
    Representa o detalhamento de uma tarifa de serviço cobrada em um produto.
    """
    def __init__(self, openBaking, dados: dict):
        DataObject.__init__(self, openBaking, dados)

        self._taxa     = [None, None, None, None]
        self._clientes = [None, None, None, None]

        if get(dados, 'prices', valueType=list, required=False) != None:
            for price in dados['prices']:
                if price['interval']    == '1_FAIXA':
                    self._taxa[0]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[0] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '2_FAIXA':
                    self._taxa[1]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[1] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '3_FAIXA':
                    self._taxa[2]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[2] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '4_FAIXA':
                    self._taxa[3]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[3] = get(price, 'customers.rate', valueType=float, required=False)

    @property
    def nome(self) -> str:
        """
        Obtem o nome do serviço.
        """
        return get(self.dados, 'name', valueType=str, required=True)

    @property
    def codigo(self) -> str:
        """
        Obtem o codigo do serviço.
        """
        return get(self.dados, 'code', valueType=str, required=False)

    @property
    def fatoGerador(self) -> str:
        """
        Fatos geradores de cobrança que incidem sobre o produto.
        """
        return get(self.dados, 'chargingTriggerInfo', valueType=str, required=False)

    @property
    def faixa1Taxa(self) -> float:
        """
        Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste serviço.

        Segundo Normativa nº 32, BCB, de 2020: Distribuição de frequência relativa dos valores de tarifas 
        cobradas dos clientes, de que trata o § 2º do art. 3º da Circular nº 4.015, de 2020, deve dar-se 
        com base em quatro faixas de igual tamanho, com explicitação dos valores sobre a mediana em cada 
        uma dessas faixas. Informando: 1ª faixa, 2ª faixa , 3ª faixa e 4ª faixa
        """
        return self._taxa[0]

    @property
    def faixa2Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste serviço."""
        return self._taxa[1]

    @property
    def faixa3Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste serviço."""
        return self._taxa[2]

    @property
    def faixa4Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste serviço."""
        return self._taxa[3]

    @property
    def faixa1Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 1."""
        return self._clientes[0]

    @property
    def faixa2Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 2."""
        return self._clientes[1]

    @property
    def faixa3Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 3."""
        return self._clientes[2]

    @property
    def faixa4Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 4."""
        return self._clientes[3]

    @property
    def taxaMaxima(self) -> float:
        """Taxa máxima cobrada pelo serviço."""
        return get(self.dados, 'maximum.value', valueType=float)

    @property
    def taxaMinima(self) -> float:
        """Taxa mínima cobrada pelo serviço."""
        return get(self.dados, 'minimum.value', valueType=float)



class Pacote(DataObject):
    """
    Representa um pacote de serviços oferecido para um produto.
    """
    def __init__(self, openBaking, dados: dict):
        DataObject.__init__(self, openBaking, dados)

        self._taxa     = [None, None, None, None]
        self._clientes = [None, None, None, None]

        if get(dados, 'prices', valueType=list, required=False) != None:
            for price in dados['prices']:
                if price['interval']    == '1_FAIXA':
                    self._taxa[0]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[0] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '2_FAIXA':
                    self._taxa[1]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[1] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '3_FAIXA':
                    self._taxa[2]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[2] = get(price, 'customers.rate', valueType=float, required=False)
                elif price['interval']  == '4_FAIXA':
                    self._taxa[3]     = get(price, 'value'         , valueType=float, required=False)
                    self._clientes[3] = get(price, 'customers.rate', valueType=float, required=False)

    @property
    def nome(self) -> str:
        """
        Obtem o nome do pacote de serviços.
        """
        return get(self.dados, 'name', valueType=str, required=True)

    @property
    def faixa1Taxa(self) -> float:
        """
        Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste pacote.

        Segundo Normativa nº 32, BCB, de 2020: Distribuição de frequência relativa dos valores de tarifas 
        cobradas dos clientes, de que trata o § 2º do art. 3º da Circular nº 4.015, de 2020, deve dar-se 
        com base em quatro faixas de igual tamanho, com explicitação dos valores sobre a mediana em cada 
        uma dessas faixas. Informando: 1ª faixa, 2ª faixa , 3ª faixa e 4ª faixa
        """
        return self._taxa[0]

    @property
    def faixa2Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste pacote."""
        return self._taxa[1]

    @property
    def faixa3Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste pacote."""
        return self._taxa[2]

    @property
    def faixa4Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste pacote."""
        return self._taxa[3]

    @property
    def faixa1Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 1."""
        return self._clientes[0]

    @property
    def faixa2Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 2."""
        return self._clientes[1]

    @property
    def faixa3Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 3."""
        return self._clientes[2]

    @property
    def faixa4Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 4."""
        return self._clientes[3]

    @property
    def taxaMaxima(self) -> float:
        """Taxa máxima cobrada pelo pacote."""
        return get(self.dados, 'maximum.value', valueType=float)

    @property
    def taxaMinima(self) -> float:
        """Taxa mínima cobrada pelo pacote."""
        return get(self.dados, 'minimum.value', valueType=float)


class Produto(DataObject):
    """
    Representa um produto negociado por um participante do Open Banking Brasil.
    """
    def __init__(self, participante, key: str, data: dict, interestRate: dict = None):
        DataObject.__init__(self, participante.openBaking, data)

        assert(isinstance(participante, Participante))

        self._key = key
        self._participante = participante
        self._taxa       = [None, None, None, None]
        self._jurosRate   = None
        self._clientes  = [None, None, None, None]
        self._jutosTipo   = None
        self._minimumRate = None 
        self._maximumRate = None

        if interestRate != None:
            self._jurosRate = get(interestRate, "rate", valueType=float, required=False)
            self._jutosTipo = get(interestRate, "referentialRateIndexer", valueType=str, required=False)

            if self._jutosTipo == 'NA':
                self._jutosTipo = None

            if 'applications' in interestRate:
                for app in interestRate['applications']:
                    if app['interval']    == '1_FAIXA':
                        self._taxa[0]     = get(app, 'indexer.rate'  , valueType=float, required=False)
                        self._clientes[0] = get(app, 'customers.rate', valueType=float, required=False)
                    elif app['interval']  == '2_FAIXA':
                        self._taxa[1]     = get(app, 'indexer.rate'  , valueType=float, required=False)
                        self._clientes[1] = get(app, 'customers.rate', valueType=float, required=False)
                    elif app['interval']  == '3_FAIXA':
                        self._taxa[2]     = get(app, 'indexer.rate'  , valueType=float, required=False)
                        self._clientes[2] = get(app, 'customers.rate', valueType=float, required=False)
                    elif app['interval']  == '4_FAIXA':
                        self._taxa[3]     = get(app, 'indexer.rate'  , valueType=float, required=False)
                        self._clientes[3] = get(app, 'customers.rate', valueType=float, required=False)

            self._minimumRate = get(interestRate, 'minimumRate', valueType=float, required=False)
            self._maximumRate = get(interestRate, 'maximumRate', valueType=float, required=False)

    @property
    def nome(self) -> str:
        """
        Retorna o nome associado ao produto.
        """
        if self._key in ['personalUnarrangedAccountOverdraft', 'businessUnarrangedAccountOverdraft']:
            return 'Adiantamento a Depositante'

        if 'type' in self.dados:
            productType = self.dados['type']

            if productType in nomeProdutos:
                return nomeProdutos[productType]
        
        if 'name' in self.dados and type(self.dados['name']) == str:
            return self.dados['name']

        return None

    @property
    def tipo(self) -> str:
        """
        Retorna o tipo do produto.
        """
        if self._key in ['personalCreditCards', 'businessCreditCards']:
            return get(self.dados, 'identification.product.type', required=True, valueType=str)

        if 'type' in self.dados and type(self.dados['type']) == str:
            return self.dados['type']

        if self._key in ['personalUnarrangedAccountOverdraft', 'businessUnarrangedAccountOverdraft']:
            return 'ADP'

        return 'UNKNOWN'

    @property
    def categoria(self) -> str:
        """
        Retorna uma categoria do produto calculada internamente na biblioteca.
        """
        if self._key in chaveCategorias:
            return chaveCategorias[self._key]
        
        return 'Outros'

    @property
    def indexador(self) -> str:
        """
        Retorna o tipo da taxa referencial ou indedxador.
        """
        return self._jutosTipo

    @property
    def indexadorRate(self) -> float:
        """
        Percentual que incide sobre a composição das taxas de juros remuneratórios.
        """
        return self._jurosRate

    @property
    def jurosSeq(self) -> int:
        """
        Retorna um campo sequencial que identica qual o valor sequencial de juros 
        é os 
        """
        seq = get(self.dados, 'interestSequence', valueType=int, required=False)
        return 1 if seq is None else seq

    @property
    def faixa1Taxa(self) -> float:
        """
        Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste produto.

        Segundo Normativa nº 32, BCB, de 2020: Distribuição de frequência relativa dos valores de tarifas 
        cobradas dos clientes, de que trata o § 2º do art. 3º da Circular nº 4.015, de 2020, deve dar-se 
        com base em quatro faixas de igual tamanho, com explicitação dos valores sobre a mediana em cada 
        uma dessas faixas. Informando: 1ª faixa, 2ª faixa , 3ª faixa e 4ª faixa
        """
        return self._taxa[0]

    @property
    def faixa2Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste produto."""
        return self._taxa[1]

    @property
    def faixa3Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste produto."""
        return self._taxa[2]

    @property
    def faixa4Taxa(self) -> float:
        """Percentual que corresponde a mediana da taxa efetiva cobrada do cliente pela contratação deste produto."""
        return self._taxa[3]

    @property
    def faixa1Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 1."""
        return self._clientes[0]

    @property
    def faixa2Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 2."""
        return self._clientes[1]

    @property
    def faixa3Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 3."""
        return self._clientes[2]

    @property
    def faixa4Clientes(self) -> float:
        """Percentual de clientes com a taxa descrita na faixa 4."""
        return self._clientes[3]

    @property
    def participante(self) -> Participante:
        """Retorna o participanete que oferece este produto."""
        return self._participante

    @property
    def taxaMaxima(self) -> float:
        """Taxa máxima efetiva dos contratos deste produto."""
        return self._maximumRate

    @property
    def taxaMinima(self) -> float:
        """Taxa mínima efetiva dos contratos deste produto.."""
        return self._minimumRate

    @property
    def rede(self) -> bool:
        """
        Retorna a rede ao qual o produto pertence.
        """
        return get(self.dados, "identification.creditCard.network", valueType=str, required=False)

    @property
    def programaRecompensas(self) -> bool:
        """Retorna `True` se o produto possui programa de recompensas."""
        return get(self.dados, "rewardsProgram.hasRewardProgram", valueType=bool, required=False)

    @property
    def servicos(self) -> Generator[Servico, None, None]:
        """
        Gera uma lista com o detalhamento das tarifas de serviço cobradas no produto.
        """
        if 'fees' in self.dados and type(self.dados['fees']) == dict:
            fees = self.dados['fees']
            for key in ['priorityServices', 'otherServices', 'services']:
                if key in fees and type(fees[key]) == list:
                    for service in fees[key]:
                        yield Servico(self.openBaking, service)

    @property
    def pacotes(self) -> Generator[Servico, None, None]:
        """
        Gera uma lista com os pacotes de serviços ofertados para o produto.
        """
        if 'serviceBundles' in self.dados and type(self.dados['serviceBundles']) == list:
            for bundle in self.dados['serviceBundles']:
                if type(bundle) == dict:
                    yield Pacote(self.openBaking, bundle)

    def __repr__(self):
        return f'Produto {self.tipo} > {self.nome}'


