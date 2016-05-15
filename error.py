class GTRError(Exception):
    pass

class GameRuleError(GTRError):
    pass

class GameActionError(GTRError):
    pass

class ParsingError(GTRError):
    pass
