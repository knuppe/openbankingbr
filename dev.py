
# %%

from openbankingbr.batch import BatchOpenBanking

bob = BatchOpenBanking(
    dataDir  = './data' ,
    cacheDir = './cache',
)
bob.todos_dados()


# %%
