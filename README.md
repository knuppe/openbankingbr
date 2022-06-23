# OpenBankingBR

Um pacote Python para carregar, analisar e exportar os **dados públicos** expostos pelos participantes do [OpenBanking Brasil](https://openbankingbrasil.org.br/).

> This package is intended to extract public data from the Open Bank Brasil. Since most users of this library will be Brazilians, everything is in Portuguese. 

Dados suportados:

**Participantes**

**Agências** via `/open-banking/channels/v1/branches`
```python
from openbankingbr import OpenBankingBR

ob = OpenBankingBR(cacheDir='./cache')

for participante in ob.participantes:
    for agencia in participante.agencias:
        print(f'Participante: {participante.nome} > agencia código: {agencia.codigo}')

```

**Produtos** via `/open-banking/products-services/v1/*`
```python
from openbankingbr import OpenBankingBR

ob = OpenBankingBR(cacheDir='./cache')

for participante in ob.participantes:
    print(f'Participante: {participante.nome}')
    for produto in participante.produtos:
        print(f'Produto: {produto.tipo} - {produto.nome}')
    
        # Serviços disponíveis no produto
        for servico in produto.servicos:
            print(f'    Serviço > {servico.nome}')
        
        # Pacotes de serviço disponíveis no produto.
        for pacote in produto.pacotes:
            print(f'    Pacote > {pacote.nome}')

```

## Mecanismo de cache

Como esta biblioteca realiza centenas de chamadas em API's das financeiras, existe um mecanimo padrão de salvar os dados retornados pelos end-points das apis em uma pasta de cache com o objetivo de não enviar um request bem sucedido mais de uma vez no mesmo dia para a endpoint/financeira.

Basicamente é um mecanismo de bom senso para não abusar das apis disponibilizadas pelas financeiras, porém você pode desabilitar este comportamento com `cacheDir = None` (mas não recomendo).

## Processamento batch

O objetivo inicial ao criar este pacote foi exportar os dados que são listados pelos participantes periodicamente para realizar análises dos produtos de crédito das instituições financeiras.

Uma forma simples de exportar todos produtos listados:

```python
from openbankingbr.batch import BatchOpenBanking
batch = BatchOpenBanking(
    dataDir  = './data' ,
    cacheDir = './cache',
    ignoraErros = True  ,  
)
batch.todos_dados()
#
# ou... somente os aquivos que interessar.
#
# batch.agencias_csv()
# batch.produtos_csv()
# batch.servicos_csv()
# batch.pacotes_csv()

```

## Notas importantes
### Qualidade dos dados

> Em teoria as APIs são homologadas pelo Bacen, porém na prática consultando as APIs é facilmente observado que **várias** instituições financeiras não seguem o padrão da documentação, não sei como passaram na homologação, mas o fato é que o dado problemático existe. Nesta biblioteca tentei contornar e validar o máximo dos dados, ignorando os valores que são absurdamente fora do [padrão](https://openbanking-brasil.github.io/areadesenvolvedor/) da documentação.

### Segurança

> A validação de certificados SSL teve que ser desabilitada, visto que as financeiras Brasileiras não se dão ao trabalho de ter um certificado SSL válido para as APIs expostas para a internet.