from __future__ import annotations
from dataclasses import dataclass
import abc
import datetime

@dataclass
class CallInfo:
    name: str = ""
    activity: str = ""
    address: str = ""
    spam_text: str = ""
    date = datetime.datetime.now()


class CallInfoProvider(abc.ABC):

    @abc.abstractmethod
    def reverse_search(self, number: str) -> CallInfo | None:
        pass


class CallInfoProviderToto(CallInfoProvider):

    def reverse_search(self, number: str) -> CallInfo | None:
        return CallInfo(name="Toto Dupond", activity="Particulier", address="01 rue de la paix MONTREUIL 93100", spam_text="Pas de spam")
    
class CallInfoProviderDummy(CallInfoProvider):

    def reverse_search(self, number: str) -> CallInfo | None:
        return None
    
class CallInfoService:

    def __init__(self, provider: CallInfoProvider):
        self.provider = provider

    def reverse_search(self, number: str) -> CallInfo | None:
        return self.provider.reverse_search(number)
