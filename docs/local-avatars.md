# Lokalny awatar: RTX 4070 / WSL2 i Mac mini M4

Domyślny backend to **SadTalker**. HeyGen pozostaje opcjonalnym dostawcą i nie
jest wywoływany po błędzie lokalnego modelu. InfiniteTalk ma oddzielny adapter
i profil 480p z offloadingiem do RAM. Przypięte commity są w
`config/avatar-tools.lock.json`; modele mają własne środowiska Python 3.10.
Studio nadal używa Python 3.12 i swojego lockfile.

| Komputer | SadTalker | InfiniteTalk |
|---|---|---|
| Windows + WSL2 + RTX 4070 | CUDA; pierwszy wariant do testu | CUDA; eksperymentalny profil małego VRAM |
| Mac mini M4, 16 GB | CPU w oficjalnym upstreamie | Oficjalny upstream nie obsługuje Metal/MPS |
| Bieżący cloud bez NVIDIA | CPU do walidacji | Brak sprzętu do testu CUDA |

16 GB w Macu to pamięć współdzielona przez system, CPU i GPU. Nie oznacza
16 GB dedykowanego VRAM i nie zapewnia zgodności z CUDA. Nie dodano
nieprzetestowanego patcha MPS. Mac może prowadzić research, scenariusze i montaż,
a awatary można generować na PC z RTX i przenosić jako pliki. Pierwsza wersja
nie uruchamia serwera GPU dostępnego w sieci.

## Windows: przygotowanie WSL2

Zainstaluj aktualny sterownik NVIDIA **w Windows**. W PowerShell:

```powershell
wsl --install -d Ubuntu-22.04
wsl --update
```

W Ubuntu sprawdź `nvidia-smi`. To warunek przed instalacją dużego stosu CUDA.
Nie instaluj osobnego sterownika GPU Linux w WSL. Toolkit/nvcc to osobny
element, potrzebny dopiero do budowania Flash Attention dla InfiniteTalk.

Przenieś aktualne pliki tego projektu do katalogu w systemie plików WSL,
np. `~/projekty/Testowe_GPT`. Zmiany z tej sesji nie zostały pushnięte do GitHub;
samo sklonowanie pustego remote nie dostarczy tego kodu. Nie kopiuj `.venv`,
`node_modules` ani gotowych środowisk modeli między systemami.

Potrzebne są: Git, FFmpeg/ffprobe, `uv`, Node.js >=22 i npm. Codex CLI jest
potrzebny do `studio agent`; komendy lokalnego awatara i propozycje DeepSeek
działają bez niego. WSL może potrzebować bibliotek systemowych Chromium:
instaluje je `playwright install --with-deps chromium`.

```bash
cd ~/projekty/Testowe_GPT
uv sync --frozen
.venv/bin/python -m playwright install --with-deps chromium
bash scripts/setup.sh
# SadTalker: oddzielne środowisko CUDA i wagi ze źródeł upstream.
.venv/bin/python scripts/setup_avatars.py sadtalker --device cuda --download-models
.venv/bin/studio avatar-doctor --backend sadtalker
```

Doktor musi wskazać `ready_for_inference: true`, `cuda: true` i nazwę Twojej
karty. Stan „zainstalowane” w panelu nie zastępuje testu CUDA. Instalator
sprawdza importy upstream, zgodność pakietów i wykonuje `pip check`.

## Pierwsze ujęcie

Użyj swojego portretu JPEG/PNG, twarz od przodu, równomierne światło,
co najmniej 256×256, najlepiej 512×512 lub więcej. Przygotuj **3–5 sekund**
czystego polskiego nagrania. Zdjęcie nie dostarcza głosu; DeepSeek jest
modelem tekstowym. Na początek własne audio pozwala ocenić sam lip sync.

```bash
.venv/bin/studio new avatar-test 'Test własnego awatara' --angle 'Ocena podobieństwa i synchronizacji polskiej mowy'
.venv/bin/studio avatar-local avatar-test /sciezka/portret.png /sciezka/glos.wav
```

Film trafi do `data/projects/avatar-test/assets/avatar/<run>/avatar.mp4`.
Adapter normalizuje audio do mono 16 kHz, sprawdza długość filmu oraz ścieżki
audio i video, zapisuje hashe wejść, wersję modelu, czas pracy i log.
Dodaje materiał do manifestu z **niezatwierdzonym** przeglądem praw i jakości.
Nie wpisuje ocen kreatywnych. Zmiana materiałów unieważnia wcześniejszą akceptację.

Domyślnie: 256px, batch 1, spokojny kadr, bez GFPGAN/upscalera, jedno zadanie
naraz, maksymalnie 15 s audio. To ustawienia pierwszego testu, nie deklaracja
jakości docelowego kanału. W `config/avatars.json` można później wybrać 512px,
po pobraniu odpowiadających wag przez `--size 512`. Nie rozciągaj małej twarzy
na cały ekran 1080p — wykorzystaj mały panel prezentera i materiały źródłowe.

Obejrzyj wynik i odsłuchaj audio: podobieństwo, polskie spółgłoski, zęby,
oczy, ruch głowy i artefakty na granicy twarzy. Mierz czas generowania i użycie
pamięci na swoim komputerze. Nie zakładamy tempa realtime ani jakości HeyGen.

## InfiniteTalk na RTX

Najpierw zakończ test SadTalker. InfiniteTalk korzysta z bazy Wan 14B i może
zajmować dziesiątki GB na dysku oraz dużo pamięci RAM podczas offloadingu.
Typowa desktopowa RTX 4070 ma 12 GB VRAM; sprawdź faktyczną wartość przez
`nvidia-smi`. Niska liczba parametrów utrzymywanych na GPU nie gwarantuje,
że cała konfiguracja zmieści się w RAM/VRAM Twojego komputera.

Zainstaluj CUDA Toolkit dla WSL zgodnie z [instrukcją NVIDIA](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).
Przypięty stos używa PyTorch CUDA 12.1; sprawdź `nvcc --version` i zgodność
toolkitu przed budowaniem Flash Attention. Instalator ogranicza kompilację
do dwóch równoległych zadań.

```bash
.venv/bin/python scripts/setup_avatars.py infinitetalk --device cuda --download-models
.venv/bin/studio avatar-doctor --backend infinitetalk
.venv/bin/studio avatar-local avatar-test /sciezka/portret.png /sciezka/glos.wav --backend infinitetalk
```

Profil: 480p, `num_persistent_param_in_dit=0`, `t5_cpu`, offload modelu,
40 kroków, bez LoRA. Pierwsza próba 3–5 s. Jeśli pojawi się OOM, zatrzymaj
próbę i oceń RAM/VRAM; nie przeskakuj automatycznie do płatnego API.
Kwantyzacja wymaga osobnych zgodnych wag i nie jest deklarowana jako gotowa
tylko na podstawie dodania flagi `int8`.

Pobieranie przez Hugging Face używa jego mechanizmu cache; repozytoria wag
mogą się zmieniać niezależnie od kodu. Zapisz identyfikatory rewizji użytych
wag przed właściwą produkcją. Commity kodu są przypięte; wagi InfiniteTalk
nie mają jeszcze zablokowanych rewizji w repozytorium studia.

## Mac mini M4

Zainstaluj natywne arm64 narzędzia: uv, Node.js >=22, npm, Git i FFmpeg.
Z katalogu projektu wykonaj:

```bash
uv sync --frozen
.venv/bin/python -m playwright install chromium
bash scripts/setup.sh
.venv/bin/python scripts/setup_avatars.py sadtalker --device cpu --download-models
.venv/bin/studio avatar-doctor --backend sadtalker
```

Studio wykrywa systemowy Chromium lub przeglądarkę Playwright. Na Macu nie
instaluje binarki HeyGen przeznaczonej dla Linux; opcjonalnie zainstaluj
oficjalny HeyGen CLI dla macOS i udostępnij go w PATH.
Dokumentacja SadTalker opisuje test na M1, a jego kod wybiera CUDA lub CPU.
Ta sesja nie ma sprzętu M4 i nie potwierdza szybkości ani wykorzystania 16 GB.

## Klucze i DeepSeek

W cloud dodaj klucz w ustawieniach środowiska. Lokalnie możesz skopiować
`.env.example` do `.env` i uzupełnić wartości w edytorze. `.env` jest ignorowany
przez Git i ładowany przez CLI oraz panel; eksportowane zmienne i ustawienia
cloud mają pierwszeństwo. Nie umieszczaj kluczy w poleceniach ani logach.

`DEEPSEEK_API_KEY` odblokowuje `studio propose-script <id>`; `DEEPSEEK_MODEL`
wybiera model (domyślnie `deepseek-chat`, alias zależny od dostawcy).
Propozycja korzysta z ustaleń, dowodów i allowed_wording w manifeście;
nie wykonuje wyszukiwania. Odpowiedź JSON i identyfikatory są walidowane,
a wynik zapisany w `proposals/` do przeglądu. Program nie dopisuje go
automatycznie do scen, nie potwierdza prawdziwości narracji i nie akceptuje filmu.
Po przeglądzie przenieś wybrane sceny do manifestu przez `studio import`.
Brak klucza DeepSeek nie blokuje lokalnego awatara.

## Źródła i stan testów

- [SadTalker: macOS](https://github.com/OpenTalker/SadTalker/blob/cd4c0465ae0b54a6f85af57f5c65fec9fe23e7f8/docs/install.md)
- [SadTalker: wybór CPU/CUDA](https://github.com/OpenTalker/SadTalker/blob/cd4c0465ae0b54a6f85af57f5c65fec9fe23e7f8/inference.py#L139)
- [InfiniteTalk: oficjalne wymagania i low VRAM](https://github.com/MeiGen-AI/InfiniteTalk/tree/50aa0a94184315407a991ae804d9b58d6d311ba8)
- [DeepSeek: API](https://api-docs.deepseek.com/api/create-chat-completion)

Testy adapterów używają fixture modelu z prawdziwym FFmpeg, a DeepSeek mock HTTP.
Wyniki rzeczywistej instalacji i generowania są osobno w `docs/validation.md`.
CUDA/RTX i M4 wymagają testu na docelowych komputerach.
