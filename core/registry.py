"""Finds every Pet subclass in the species/ package, so new animals need no wiring."""

import importlib
import inspect
import pkgutil

import species
from core.pet import Pet


def discover() -> dict[str, type[Pet]]:
    for module in pkgutil.iter_modules(species.__path__):
        importlib.import_module(f"species.{module.name}")

    found: dict[str, type[Pet]] = {}

    def collect(cls: type[Pet]):
        for sub in cls.__subclasses__():
            if sub.species and not inspect.isabstract(sub):
                found[sub.species] = sub
            collect(sub)

    collect(Pet)
    return found
