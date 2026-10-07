# Kontynuowanie pracy na swoim komputerze

Rozpakuj ZIP. Zawiera kod studia, lockfile, konfigurację lokalnych modeli,
skille własne i instrukcje pobrania przypiętych narzędzi upstream.
Zależności i wagi pobiera instalator. Używaj poleceń w katalogu `Testowe_GPT`.

## Windows + RTX 4070

1. W Windows zainstaluj aktualny sterownik NVIDIA, WSL2 i Ubuntu.
2. Przenieś folder projektu do systemu plików WSL, np. `~/projekty/Testowe_GPT`.
3. Zainstaluj uv, Node.js >=22/npm, Git i FFmpeg. Sprawdź `nvidia-smi` w Ubuntu.

Instrukcje producentów: [uv](https://docs.astral.sh/uv/getting-started/installation/),
[Node.js](https://nodejs.org/en/download), [WSL](https://learn.microsoft.com/windows/wsl/install).
FFmpeg, Git i biblioteki kompilacji można zainstalować przez apt w Ubuntu.
`playwright install --with-deps` poniżej instaluje biblioteki Chromium.

```bash
cd ~/projekty/Testowe_GPT
uv sync --frozen
.venv/bin/python -m playwright install --with-deps chromium
bash scripts/setup.sh
.venv/bin/python scripts/setup_avatars.py sadtalker --device cuda --download-models
.venv/bin/studio avatar-doctor
bash scripts/start.sh
```

Panel działa lokalnie na porcie 8080. W drugim terminalu z tego samego katalogu
można uruchamiać komendy `studio`. Codex CLI jest opcjonalny dla komend awatara
i DeepSeek; potrzebny do pełnej sesji `studio agent`.
ZIP nie zawiera metadanych Git. Przed `studio agent` wykonaj `git init`
w rozpakowanym katalogu, aby Codex miał repozytorium do pracy.

## Klucze i pierwsza próba

Skopiuj `.env.example` do `.env`, uzupełnij klucze w lokalnym edytorze,
następnie zrestartuj panel. Klucze nie są potrzebne do lokalnego awatara.
Nie wysyłaj ich w rozmowie i nie commituj `.env`.

```bash
.venv/bin/studio new avatar-test 'Test awatara' --angle 'Podobieństwo i polska mowa'
# Własne zdjęcie oraz 3–5 sekund własnego nagrania audio:
.venv/bin/studio avatar-local avatar-test /sciezka/portret.png /sciezka/glos.wav
.venv/bin/studio status
```

Najpierw oceń wynik SadTalker. InfiniteTalk ma osobne wymagania CUDA Toolkit,
Flash Attention i dużo większe wagi. Instrukcja: [docs/local-avatars.md](docs/local-avatars.md).
HeyGen jest opcjonalny; brak lokalnego wyniku nie uruchamia płatnego API.
DeepSeek proponuje scenariusz przez `studio propose-script <id>` po zapisaniu
źródeł i ustaleń. Research i akceptacja pozostają osobnymi etapami.

## Mac mini M4, 16 GB

Zainstaluj arm64 uv, Node.js >=22/npm, Git i FFmpeg. Z katalogu projektu:

```bash
uv sync --frozen
.venv/bin/python -m playwright install chromium
bash scripts/setup.sh
.venv/bin/python scripts/setup_avatars.py sadtalker --device cpu --download-models
.venv/bin/studio avatar-doctor
bash scripts/start.sh
```

Mac korzysta z CPU w oficjalnym SadTalker. GPU Apple nie obsługuje CUDA
InfiniteTalk. Generowanie na RTX i przenoszenie plików na Mac jest alternatywą.

## Kontynuowanie z Codex

Otwórz rozpakowany katalog w swoim edytorze/Codex i poproś:

> Przeczytaj AGENTS.md, START_TUTAJ.md i docs/validation.md. Kontynuuj studio
> wideo bez n8n. Najpierw sprawdź CUDA na moim RTX 4070/WSL2 przez avatar-doctor,
> uruchom test SadTalker ze zdjęciem i audio, które wskażę, potem oceń jakość.
> HeyGen jest opcjonalny, DeepSeek pomaga ze scenariuszem. Nie publikuj filmów
> ani nie wysyłaj płatnych generacji bez ustalonego przeze mnie zakresu.

Testy: `.venv/bin/pytest -q`. Aktualny zakres wykonanych prób oraz ograniczenia
są w [docs/validation.md](docs/validation.md). ZIP jest eksportem źródeł;
dotychczasowe lokalne zmiany nie zostały pushnięte do GitHub.
