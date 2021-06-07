
class OpenBankingException(Exception):
    """
    Error raised when problems arise
    """

class BatchException(OpenBankingException):
    """
    Ocorre devido a um erro no processamento batch de dados públicos.
    """

class InvalidDataException(OpenBankingException):
    """
    Ocorre quando algum dado inválido ou não esperado foi encontrado.
    """

class RequiredFieldException(OpenBankingException):
    """
    Ocorre quando um campo obrigatório não é encontrado nos dados do open-banking de um participante.
    """