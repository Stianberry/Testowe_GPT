# Studio redakcyjne wideo AI

Lokalny proces od researchu do szkicu w Postiz, sterowany przez Codex,
bez n8n. Projekt powstał pod polskie newsy i wyjaśnianie kontrowersji:
niezależne źródła, rzeczywiste materiały, własna narracja i świadomy montaż.

## Uruchomienie

Na własnym komputerze zacznij od [START_TUTAJ.md](START_TUTAJ.md).
Windows: WSL2 + RTX 4070. Mac mini M4: lokalny montaż i SadTalker CPU.
Szczegóły modeli i pierwszego ujęcia: [lokalne awatary](docs/local-avatars.md).

```bash
cd /workspace/Testowe_GPT
bash scripts/setup.sh
bash scripts/start.sh
```

Panel udostępnia projekty, karty źródeł i materiałów w manifeście, raport
jakości, brief dla agenta i akceptację obejrzanego filmu. Serwer nasłuchuje
lokalnie na porcie 8080. To aplikacja do pracy w środowisku, bez publicznego wdrożenia.
Test gotowości: `curl --fail http://127.0.0.1:8080/health`.

## Co działa

- Projekty i historia rewizji w SQLite, ochrona przed równoczesnym nadpisaniem.
- Research przez Tavily; RSS i import publicznych URL jako alternatywa.
- Przechwytywanie rzeczywistych stron: pełny screen, wycinek, tekst, URL i hash.
- Pobieranie materiału przez yt-dlp, napisy oraz dokładne cięcie FFmpeg.
- Dostęp do siedmiu wybranych narzędzi rzeczywistego OpenMontage.
- Kompozycje i rendering HyperFrames; wyrenderowany test 1080×1920, 30 fps.
- Lokalny awatar ze zdjęcia + audio: adaptery SadTalker i InfiniteTalk,
  odseparowane środowiska, kontrola CUDA/CPU, długości audio i wynikowego filmu.
- Opcjonalny HeyGen CLI i wejście awatara ze zdjęcia lokalnego lub URL.
- DeepSeek: propozycja scenariusza z istniejących ustaleń do przeglądu.
- Adapter Postiz: kanały, upload, szkice i dostępne metryki.
- Kontrola rzetelności i typowych objawów AI slopu, osobna ocena kreatywna.
- Akceptacja powiązana z projektem i plikami. Zmiany unieważniają zgodę.

Tavily, DeepSeek, opcjonalny HeyGen, Pexels i Postiz wymagają własnego dostępu.
Lokalne modele nie wymagają klucza HeyGen. Adaptery Postiz
przetestowano przez mock HTTP, nie na koncie użytkownika. Tworzenie awatara
i aktualny research przez Tavily nie zostały jeszcze wykonane. OpenCreator
pozostaje opcjonalnym panelem zewnętrznym; jego Digital Avatar jest w rozwoju.

## Pierwszy film

```bash
.venv/bin/studio new pierwszy-film 'Tytuł tematu' --angle 'Co konkretnie chcemy wyjaśnić?'
.venv/bin/studio research 'Temat, oryginalna wypowiedź, oświadczenie, sprostowanie'
.venv/bin/studio brief pierwszy-film > data/projects/pierwszy-film/brief.md
# Uruchomienie agenta po wybraniu realnego tematu i skonfigurowaniu źródeł:
.venv/bin/studio agent pierwszy-film
```

Agent korzysta ze skilla [editorial-video](.agents/skills/editorial-video/SKILL.md)
i zainstalowanych skilli OpenMontage, HyperFrames, HeyGen i video-use.
`studio agent` korzysta z istniejącego logowania Codex i zachowuje sandbox.
Sesja produkcyjna z realnym newsem wymaga testu; obecna walidacja sprawdza
lokalne narzędzia i kontrolę przekazania filmu, nie autonomiczną pracę redakcji.

Manifest można wyeksportować, poprawić i zapisać. W scenach wpisuje się źródła,
wybrane materiały, kandydatów, cel, narrację i uzasadnienie wyboru.

```bash
.venv/bin/studio export pierwszy-film > data/projects/pierwszy-film/project.json
.venv/bin/studio import data/projects/pierwszy-film/project.json --revision 1
.venv/bin/studio render pierwszy-film
.venv/bin/studio quality pierwszy-film
.venv/bin/studio approve pierwszy-film --reviewer 'Redaktor'
.venv/bin/studio postiz-channels
.venv/bin/studio postiz-draft pierwszy-film ID_KANALU --caption opis.txt --settings ustawienia-kanalu.json
```

Ostatnie polecenie tworzy wyłącznie szkic. Ustawienia są zależne od platformy;
np. YouTube potrzebuje `__type`, `title` i `type`. Przed wywołaniem sprawdź
aktualny schemat dla podłączonego kanału. Harmonogram i publikacja są w Postiz.
Ponowienie niepewnego wysłania jest blokowane do wyjaśnienia wyniku w Postiz.

## Materiały i awatar

```bash
.venv/bin/studio capture pierwszy-film zrodlo-1 https://publiczna-strona.pl/artykul --selector article
.venv/bin/studio download pierwszy-film https://www.youtube.com/watch?v=IDENTYFIKATOR
.venv/bin/studio clip pierwszy-film downloads/film.mp4 assets/cytat.mp4 --start 120 --end 129
.venv/bin/studio stock 'konkretne znaczenie sceny'
# Domyślnie lokalny SadTalker, po instalacji środowiska modelu:
.venv/bin/studio avatar-doctor
.venv/bin/studio avatar-local pierwszy-film /sciezka/do/portretu.png /sciezka/do/glosu.wav
# Alternatywnie po osobnej instalacji InfiniteTalk/CUDA:
.venv/bin/studio avatar-local pierwszy-film /sciezka/do/portretu.png /sciezka/do/glosu.wav --backend infinitetalk
# Opcjonalny HeyGen:
.venv/bin/studio avatar-photo 'Mój awatar' /sciezka/do/mojego-zdjecia.png
# DeepSeek po zapisaniu źródeł i ustaleń w manifeście:
.venv/bin/studio propose-script pierwszy-film
.venv/bin/studio om-tools
```

Źródło musi mieć ustaloną datę, wydawcę i grupę pierwotnego pochodzenia.
Screen zachowuje prawdziwy dokument i kontekst. Brakujące zasoby sieciowe
są zapisywane w metadanych; taki screen trzeba sprawdzić przed użyciem.
Zdjęcie awatara: JPEG/PNG, najlepiej ≥512×512, twarz od przodu, dobre światło.
Zdjęcie nie dostarcza głosu. Polski głos i lip sync wymagają próbki filmowej.

## Test techniczny i utrzymanie

```bash
.venv/bin/pytest -q
HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium npm run video:check
HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium npm run video:render
```

Przykład w `examples/quality-demo` to 12 sekund animacji z danymi umownymi,
bez narracji. Nie jest pilotem kanału ani materiałem do publikacji.

Pakiety mają lockfile, repozytoria upstream immutable commity, a HeyGen CLI
zweryfikowane sumy SHA-256. Dane, zależności i klucze są poza Git.
Automatyczne wykrywanie tematów: `studio discover --config config/research.json`.
To pojedyncze uruchomienie; codzienny harmonogram wymaga stale działającego
serwera lub runnera. Sesja cloud nie zapewnia pracy 24/7.

Szczegóły: [jakość](docs/quality.md), [integracje](docs/integrations.md),
[architektura](docs/architecture.md), [walidacja](docs/validation.md).
Źródła można spakować przez `.venv/bin/python scripts/package_source.py`.
