# %%

import os
import platform

from . import OpenBankingBR

from .errors import BatchException
from .models import Participante, Produto

from typing import List
from datetime import date, datetime

class BatchOpenBanking():
    """
    Classe destinada para o processamento batch de ingestão dos dados públicos dos
    participantes listados no diretório do Open Banking Brasil.

    ```python 
    # exemplo para baixar os dados    
    bob = BatchOpenBanking(
        dataDir  = './data',
        cacheDir = './cache',

        # caso queira trabalhar no excel mais facilmente, só descomentar
        # encoding     = 'cp1252',
        # csvDelimiter = ';'
    )
    bob.todos_dados()
    bob.limpa_cache_antigo() # remove arquivos de cache com mais de 5 dias de vida.
    ```

    """
    def __init__(self, dataDir: str, cacheDir: str, csvDelimiter: str = ',', encoding = 'utf8', ignoraErros: bool = False):
        """
        Inicializa o objeto com os parâmetros de execução do batch.

        Caso `dataDir` ou `cacheDir` não existam eles serão criados.

        Argumentos:

            dataDir      - Diretório onde será salvo os arquivos processados.
            cacheDir     - Diretório onde é salvo os arquivos de cache usados para não abusar as APIs 
                           disponibilizado pelas instituições financeiras. O comportamento do cache é
                           de fazer o download de cada endPoint uma única vez por dia.
            csvDelimiter - Especifica o delimitador do arquivo csv (caso queira usar outro fora do padrão).
            ignoreErrors - Em vez do exception uma mensagem de erro é logada e vida que segue.
        """
        if not os.path.exists(dataDir):
            os.makedirs(dataDir)
        elif not os.path.isdir(dataDir):
            raise ValueError("O valor especificado no argumento dataDir não é um diretório.")

        if not os.path.exists(cacheDir):
            os.makedirs(cacheDir)
        elif not os.path.isdir(cacheDir):
            raise ValueError("O valor especificado no argumento cacheDir não é um diretório.")

        self.dataDir        = dataDir
        self.cacheDir       = cacheDir
        self.csvDelimiter   = csvDelimiter
        self.ignoraErros    = ignoraErros
        self.encoding       = encoding

    def todos_dados(self):
        """
        Realiza o download de todos os dados publicos disponíveis dos participantes
        registrados no diretório do Open Banking Brasil, salvando os dados em arquivos
        na pasta `dataDir` informada na inicialização do `BatchOpenBanking`.

        Os arquivos serão salvos com o nome no seguinte formato: `yyyymmdd_openbanking_xxx.csv`
        """
        self.agencias_csv()
        self.produtos_csv()
        self.servicos_csv()
        self.pacotes_csv()

    def limpa_cache_antigo(self, idadeMaxima = 5):
        """
        Realiza a limpeza dos arquivos antigos (padrão é `5` ou mais dias de vida) de cache.

        Note que um arquivo de cache só deve ser antigo caso um endpoint não esteja mais
        disponível por uma financeira, e mesmo que o arquivo seja "antigo" ao tentar puxar
        os dados mais recentes, o arquivo de cache será recriado com as informações mais recentes.
        """
    
        if not os.path.exists(self.cacheDir):
            return
        
        if not os.path.isdir(self.cacheDir):
            return

        ctime: datetime
        files = os.listdir(self.cacheDir)
        for file in files:
            if not file.endswith('.json'):
                continue
           
            fileName = os.path.join(self.cacheDir, file)

            if platform.system() == "Windows":
                ctime = datetime.fromtimestamp(os.path.getctime(fileName))
            else:
                stat = os.stat(fileName)
                try:
                    ctime = datetime.fromtimestamp(stat.st_birthtime)
                except:
                    ctime = datetime.fromtimestamp(stat.st_mtime)

            if (date.today() - ctime.date()).days > idadeMaxima:
                try:
                    os.remove(fileName)
                except:
                    continue

    def agencias_csv(self):
        """
        Realiza o download de todas as agências informadas nas apis dos participantes
        no diretório do Open Banking Brasil. Os dados das agências são salvos no arquivo 
        com nome: `yyyymmdd_openbanking_agencias.csv`.
        """
        ob = OpenBankingBR(
            cacheDir = self.cacheDir,
        )

        participantes: List[Participante]
        participantes = None

        hoje = date.today().strftime('%Y%m%d')

        fileName = os.path.join(self.dataDir, f'{hoje}_openbanking_agencias.csv')
        if os.path.exists(fileName):
            os.remove(fileName)
            print(f'Arquivo {fileName} foi apagado para o reprocessamento.')

        with open(fileName, 'w', encoding=self.encoding) as file:

            file.write(self.csvDelimiter.join([
                "DATA_BASE",
                "API",
                "PARTICIPANTE_SEQ",
                "PARTICIPANTE_CNPJ",
                "PARTICIPANTE_NOME",
                "AGENCIA_SEQ",
                "AGENCIA_TIPO",
                "AGENCIA_CODIGO",
                "AGENCIA_DIGITO",
                "AGENCIA_NOME",
                "AGENCIA_TELEFONE",
                "AGENCIA_ENDERECO",
                "AGENCIA_COMPLEMENTO",
                "AGENCIA_BAIRRO",
                "AGENCIA_CIDADE",
                "AGENCIA_UF",
                "AGENCIA_CEP",
                "AGENCIA_CODIGO_IBGE",
                "AGENCIA_LATITUDE",
                "AGENCIA_LONGITUDE",
            ]) + '\n')

            try:
                participantes = [x for x in ob.participantes]
            except:
                if self.ignoraErros:
                    print('Erro: Não foi possível baixar as informações do diretório de participantes do Open Banking Brasil.')
                    return

                raise BatchException("Não foi possível baixar as informações do diretório de participantes do Open Banking Brasil.")

            totalParticipantes = len(participantes)
            totalAgencias = 0

            seqParticipante = 0
            seqAgencia = 0

            for participante in participantes:
                seqAgencia = 0

                seqParticipante += 1
                try:
                    for agencia in participante.agencias:
                        totalAgencias += 1
                        seqAgencia += 1
                        row = [
                            str(hoje),
                            _fix(agencia.endPoint),
                            _fix(seqParticipante),
                            _fix(participante.cnpj),
                            _fix(participante.nome),
                            _fix(seqAgencia),
                            _fix(agencia.tipo),
                            _fix(agencia.codigo),
                            _fix(agencia.digitoVerificador),
                            _fix(agencia.nome),
                            _fix(agencia.telefone),
                            _fix(agencia.endereco),
                            _fix(agencia.enderecoComplemento),
                            _fix(agencia.bairro),
                            _fix(agencia.cidade),
                            _fix(agencia.uf),
                            _fix(agencia.cep),
                            _fix(agencia.codigoIBGE),
                            _fix(agencia.latitude),
                            _fix(agencia.longitude),
                        ]
                        file.write(self.csvDelimiter.join(row) + '\n')

                        continue

                except Exception as e:
                    if self.ignoraErros:
                        print(f"Erro: Participanete ignorado devido a erro no processamento: {e}")
                        continue 
                    
                    raise BatchException(f'Erro: Participanete ignorado devido a erro no processamento: {e}')

            file.flush()

        print('Processamento das agências concluído.')
        print(f"Total de participantes: {totalParticipantes}")
        print(f"Total de agências: {totalAgencias}")
        print('.')

    def produtos_csv(self):
        """
        Realiza o download de todos os produtos disponíveis em todos participantes 
        no diretório do Open Banking Brasil, e salva os dados dos produtos em um 
        arquivo no formato: `yyyymmdd_openbanking_produtos.csv`.
        """

        ob = OpenBankingBR(
            cacheDir = self.cacheDir,
        )

        participantes: List[Participante]
        participantes = None

        hoje = date.today().strftime('%Y%m%d')

        fileName = os.path.join(self.dataDir, f'{hoje}_openbanking_produtos.csv')
        if os.path.exists(fileName):
            os.remove(fileName)
            print(f'Arquivo {fileName} foi apagado para o reprocessamento.')
        
        with open(fileName, 'w', encoding=self.encoding) as file:
            file.write(self.csvDelimiter.join([
                "DATA_BASE",
                "API",
                "PARTICIPANTE_SEQ",
                "PARTICIPANTE_CNPJ",
                "PARTICIPANTE_NOME",
                "PRODUTO_SEQ",
                "PRODUTO_TIPO",
                "PRODUTO_CATEGORIA",
                "PRODUTO_REDE",
                "PRODUTO_NOME",
                "PRODUTO_INDEXADOR",
                "PRODUTO_INDEXADOR_RATE",
                "PRODUTO_TAXA_MINIMA",
                "PRODUTO_TAXA_MAXIMA",
                "PRODUTO_FAIXA1_TAXA",
                "PRODUTO_FAIXA1_CLIENTES",
                "PRODUTO_FAIXA2_TAXA",
                "PRODUTO_FAIXA2_CLIENTES",
                "PRODUTO_FAIXA3_TAXA",
                "PRODUTO_FAIXA3_CLIENTES",
                "PRODUTO_FAIXA4_TAXA",
                "PRODUTO_FAIXA4_CLIENTES",
                "PRODUTO_PROGRAMA_RECOMPENSAS",
            ]) + '\n')

            try:
                participantes = [x for x in ob.participantes]
            except:
                msg = "Não foi possível baixar as informações do diretório de participantes do Open Banking Brasil."
                if self.ignoraErros:
                    print(f'Erro: {msg}')
                    return

                raise BatchException(msg)

            totalParticipantes = len(participantes)
            totalProdutos = 0

            seqParticipante = 0
            seqProduto = 0

            for participante in participantes:
                seqProduto = 0

                seqParticipante += 1
                try:
                    for produto in participante.produtos:
                        seqProduto += 1
                        totalProdutos += 1

                        row = [
                            str(hoje),
                            _fix(produto.endPoint),
                            _fix(seqParticipante),
                            _fix(participante.cnpj),
                            _fix(participante.nome),
                            _fix(seqProduto),
                            _fix(produto.tipo),
                            _fix(produto.categoria),
                            _fix(produto.rede),
                            _fix(produto.nome),
                            _fix(produto.indexador),
                            _fix(produto.indexadorRate),
                            _fix(produto.taxaMinima),
                            _fix(produto.taxaMaxima),
                            _fix(produto.faixa1Taxa),
                            _fix(produto.faixa1Clientes),
                            _fix(produto.faixa2Taxa),
                            _fix(produto.faixa2Clientes),
                            _fix(produto.faixa3Taxa),
                            _fix(produto.faixa3Clientes),
                            _fix(produto.faixa4Taxa),
                            _fix(produto.faixa4Clientes),
                            _fix(produto.programaRecompensas),
                        ]
                        file.write(self.csvDelimiter.join(row) + '\n')
                        continue

                except:
                    if self.ignoraErros:
                        print('Participanete ignorado devido a erro no processamento.')
                        continue

                    raise BatchException("Um erro ocorreu durante o processamento de um participante.")

            file.flush()

        print('Processamento dos produtos concluído.')
        print(f"Total de participantes: {totalParticipantes}")
        print(f"Total de produtos: {totalProdutos}")
        print('.')

    def servicos_csv(self):
        """
        Realiza o download de todos os produtos disponíveis em todos participantes 
        no diretório do Open Banking Brasil, e salva os dados dos serviços em um 
        arquivo no formato: `yyyymmdd_openbanking_servicos.csv`.
        """

        ob = OpenBankingBR(
            cacheDir = self.cacheDir,
        )

        participantes: List[Participante]
        participantes = None

        hoje = date.today().strftime('%Y%m%d')

        fileName = os.path.join(self.dataDir, f'{hoje}_openbanking_servicos.csv')
        if os.path.exists(fileName):
            os.remove(fileName)
            print(f'Arquivo {fileName} foi apagado para o reprocessamento.')
        
        with open(fileName, 'w', encoding=self.encoding) as file:
            file.write(self.csvDelimiter.join([
                "DATA_BASE",
                "API",
                "PARTICIPANTE_SEQ",
                "PARTICIPANTE_CNPJ",
                "PARTICIPANTE_NOME",
                "PRODUTO_SEQ",
                "PRODUTO_TIPO",
                "PRODUTO_CATEGORIA",
                "PRODUTO_NOME",
                "SERVICO_SEQ",
                "SERVICO_NOME",
                "SERVICO_CODIGO",
                "SERVICO_TAXA_MINIMA",
                "SERVICO_TAXA_MAXIMA",
                "SERVICO_FAIXA1_TAXA",
                "SERVICO_FAIXA1_CLIENTES",
                "SERVICO_FAIXA2_TAXA",
                "SERVICO_FAIXA2_CLIENTES",
                "SERVICO_FAIXA3_TAXA",
                "SERVICO_FAIXA3_CLIENTES",
                "SERVICO_FAIXA4_TAXA",
                "SERVICO_FAIXA4_CLIENTES",
                "SERVICO_FATO_GERADOR"
            ]) + '\n')

            try:
                participantes = [x for x in ob.participantes]
            except:
                msg = "Não foi possível baixar as informações do diretório de participantes do Open Banking Brasil."
                if self.ignoraErros:
                    print(f'Erro: {msg}')
                    return

                raise BatchException(msg)

            totalParticipantes = len(participantes)
            totalProdutos = 0
            totalServicos = 0

            seqParticipante = 0
            seqProtudo = 0
            seqServico = 0

            for participante in participantes:
                seqProtudo = 0

                seqParticipante += 1
                try:
                    for produto in participante.produtos:
                        seqServico = 0

                        seqProtudo += 1
                        totalProdutos += 1
                        for servico in produto.servicos:
                            seqServico += 1
                            totalServicos += 1

                            row = [
                                str(hoje),
                                _fix(produto.endPoint),
                                _fix(seqParticipante),
                                _fix(participante.cnpj),
                                _fix(participante.nome),
                                _fix(seqProtudo),
                                _fix(produto.tipo),
                                _fix(produto.categoria),
                                _fix(produto.nome),
                                _fix(seqServico),
                                _fix(servico.nome),
                                _fix(servico.codigo),
                                _fix(servico.taxaMinima),
                                _fix(servico.taxaMaxima),
                                _fix(servico.faixa1Taxa),
                                _fix(servico.faixa1Clientes),
                                _fix(servico.faixa2Taxa),
                                _fix(servico.faixa2Clientes),
                                _fix(servico.faixa3Taxa),
                                _fix(servico.faixa3Clientes),
                                _fix(servico.faixa4Taxa),
                                _fix(servico.faixa4Clientes),
                                _fix(servico.fatoGerador),
                            ]
                            file.write(self.csvDelimiter.join(row) + '\n')
                except:
                    if self.ignoraErros:
                        print('Participanete ignorado devido a erro no processamento de serviços de um produto.')
                        continue

                    raise BatchException("Um erro ocorreu durante o processamento de um participante.")

            file.flush()

        print('Processamento dos produtos concluído.')
        print(f"Total de participantes: {totalParticipantes}")
        print(f"Total de serviços: {totalServicos}")
        print('.')

    def pacotes_csv(self):
        """
        Realiza o download de todos os produtos disponíveis em todos participantes 
        no diretório do Open Banking Brasil, e salva os dados dos pacotes de serviços 
        em um arquivo no formato: `yyyymmdd_openbanking_pacotes.csv`.
        """

        ob = OpenBankingBR(
            cacheDir = self.cacheDir,
        )

        participantes: List[Participante]
        participantes = None

        hoje = date.today().strftime('%Y%m%d')

        fileName = os.path.join(self.dataDir, f'{hoje}_openbanking_pacotes.csv')
        if os.path.exists(fileName):
            os.remove(fileName)
            print(f'Arquivo {fileName} foi apagado para o reprocessamento.')

       
        with open(fileName, 'w', encoding=self.encoding) as file:
            file.write(self.csvDelimiter.join([
                "DATA_BASE",
                "API",
                "PARTICIPANTE_SEQ",
                "PARTICIPANTE_CNPJ",
                "PARTICIPANTE_NOME",
                "PRODUTO_SEQ",
                "PRODUTO_TIPO",
                "PRODUTO_CATEGORIA",
                "PRODUTO_NOME",
                "PACOTE_SEQ",
                "PACOTE_NOME",
                "PACOTE_TAXA_MINIMA",
                "PACOTE_TAXA_MAXIMA",
                "PACOTE_FAIXA1_TAXA",
                "PACOTE_FAIXA1_CLIENTES",
                "PACOTE_FAIXA2_TAXA",
                "PACOTE_FAIXA2_CLIENTES",
                "PACOTE_FAIXA3_TAXA",
                "PACOTE_FAIXA3_CLIENTES",
                "PACOTE_FAIXA4_TAXA",
                "PACOTE_FAIXA4_CLIENTES"
            ]) + '\n')

            try:
                participantes = [x for x in ob.participantes]
            except:
                msg = "Não foi possível baixar as informações do diretório de participantes do Open Banking Brasil."
                if self.ignoraErros:
                    print(f'Erro: {msg}')
                    return

                raise BatchException(msg)
        
            totalParticipantes = len(participantes)
            totalProdutos = 0
            totalPacotes = 0

            seqParticipante = 0
            seqProduto = 0
            seqPacote = 0

            for participante in participantes:
                seqParticipante += 1
                seqProduto = 0
                try:
                    for produto in participante.produtos:
                        seqPacote = 0
                        
                        totalProdutos += 1
                        seqProduto += 1
                        
                        for pacote in produto.pacotes:
                            totalPacotes += 1
                            seqPacote += 1
                            row = [
                                str(hoje),
                                _fix(produto.endPoint),
                                _fix(seqParticipante),
                                _fix(participante.cnpj),
                                _fix(participante.nome),
                                _fix(seqProduto),
                                _fix(produto.tipo),
                                _fix(produto.categoria),
                                _fix(produto.nome),
                                _fix(seqPacote),
                                _fix(pacote.nome),
                                _fix(pacote.taxaMinima),
                                _fix(pacote.taxaMaxima),
                                _fix(pacote.faixa1Taxa),
                                _fix(pacote.faixa1Clientes),
                                _fix(pacote.faixa2Taxa),
                                _fix(pacote.faixa2Clientes),
                                _fix(pacote.faixa3Taxa),
                                _fix(pacote.faixa3Clientes),
                                _fix(pacote.faixa4Taxa),
                                _fix(pacote.faixa4Clientes),
                            ]
                            file.write(self.csvDelimiter.join(row) + '\n')
                except:
                    if self.ignoraErros:
                        print('Participanete ignorado devido a erro no processamento dos pacotes de serviço de um produto.')
                        continue

                    raise BatchException("Um erro ocorreu durante o processamento dos pacotes de serviço de um participante.")

            file.flush()

        print('Processamento dos pacotes de produtos concluído.')
        print(f"Total de participantes: {totalParticipantes}")
        print(f"Total de produtos: {totalProdutos}")
        print(f"Total de pacotes: {totalPacotes}")
        print('.')

def _fix(value) -> str:
    if value == None:
        return ""
    
    if type(value) == str:
        if value == 'NA':
            return ""

        # RFC-4180, paragraph "If double-quotes are used to enclose fields, then a double-quote 
        # appearing inside a field must be escaped by preceding it with another double quote."
        return "\"" + value.replace('\n', ' ').replace('\"', '\"\"') + "\""

    return str(value)

# %%
