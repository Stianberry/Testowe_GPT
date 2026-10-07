"""Use selected actual upstream tools; avoid importing optional GPU/provider stacks."""
from dataclasses import asdict
import importlib
import inspect
from pathlib import Path
import sys


MODULES = {
    "video_trimmer": "tools.video.video_trimmer",
    "video_downloader": "tools.analysis.video_downloader",
    "transcript_fetcher": "tools.analysis.transcript_fetcher",
    "direct_clip_search": "tools.video.direct_clip_search",
    "heygen_avatar": "tools.avatar.heygen_avatar",
    "export_bundle": "tools.publishers.export_bundle",
    "frame_sampler": "tools.analysis.frame_sampler",
}


def tool(name: str):
    root = Path(__file__).resolve().parent.parent / ".tools/openmontage"
    if not root.is_dir():
        raise ValueError("Uruchom scripts/setup.sh, aby zainstalować przypięte OpenMontage")
    if name not in MODULES:
        raise ValueError("Narzędzie nie jest w przetestowanym zestawie adapterów")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tools.base_tool import BaseTool
    module = importlib.import_module(MODULES[name])
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if cls is not BaseTool and issubclass(cls, BaseTool) and cls.__module__ == module.__name__ and not inspect.isabstract(cls):
            instance = cls()
            if instance.name == name:
                return instance
    raise ValueError("Nie znaleziono narzędzia w przypiętej wersji")


def describe() -> list[dict]:
    result = []
    for name in MODULES:
        try:
            instance = tool(name)
            result.append({"name": name, "loaded": True, "schema": instance.input_schema})
        except (ValueError, ImportError, AttributeError) as error:
            result.append({"name": name, "loaded": False, "error": str(error)})
    return result


def execute(name: str, inputs: dict) -> dict:
    import jsonschema
    instance = tool(name)
    jsonschema.validate(inputs, instance.input_schema)
    return asdict(instance.execute(inputs))
