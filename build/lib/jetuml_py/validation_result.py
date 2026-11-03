from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    """Resultado de uma validação. 'silent' indica rejeição sem notificação ao usuário."""
    ok: bool
    message: str = ""
    silent: bool = False

    def __bool__(self) -> bool:
        return self.ok


OK = Result(True)


def reject(message: str, silent: bool = False) -> Result:
    return Result(False, message, silent)
