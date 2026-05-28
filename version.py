
from dataclasses import dataclass
from enum import StrEnum


class BuildType(StrEnum):
    DEVELOPEMENT = "d",
    PREVIEW = "p",
    ALPHA = "a",
    BETA = "b",
    FINAL = "f",


@dataclass(frozen=True)
class Version():
    major: int
    minor: int
    patch: int
    type: BuildType | None
    build: int | None

    def __str__(self) -> str:
        return self.to_str()
    
    def to_str(self, sep: str = ".") -> str:
        version = f"{self.major}{sep}{self.minor}{sep}{self.patch}"
        
        if self.type and self.build is not None:
            version += f"{self.type.value}{self.build}"
        elif self.type is not None:
            version += f"{self.type.value}"
        elif self.build is not None:
            version += f"{sep}{self.build}"
        
        return version