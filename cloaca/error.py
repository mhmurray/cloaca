class GTRError(Exception):
    pass

class GTRDBError(GTRError):
    pass

class GameRuleError(GTRError):
    pass

class GameActionError(GTRError):
    pass

class ParsingError(GTRError):
    pass

class GameOver(Exception):
    pass
