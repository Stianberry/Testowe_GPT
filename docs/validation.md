# Walidacja środowiska — 7 października 2026

## Wykonane w bieżącej maszynie

- `scripts/setup.sh`: instalacja przez `uv sync --frozen` i `npm ci`, immutable
  commity narzędzi, kontrola SHA-256 HeyGen CLI, uruchomienie Chromium i testy.
- Początkowe 21 testów: niezależność źródeł, cytat a prawdziwość zarzutu, kontrdowody,
  aktualność informacji, typowe objawy AI slopu, szerszy kontekst klipu,
  rewizje, pliki, akceptacje, ochrona przed duplikatem szkicu, zdjęcie awatara,
  przeglądarka, API oraz rzeczywiste cięcie przez upstream OpenMontage.
- Siedem wybranych narzędzi OpenMontage zaimportowano poprawnie.
- Oficjalny HeyGen CLI v0.9.0 działa. Schemat `avatar create` sprawdzono offline;
  lokalny plik jest przekazywany przez stdin. Wysłanie zdjęcia ma test mock.
- Serwer uruchomiony przez `scripts/start.sh`: health, zapis i odczyt projektu,
  raport jakości, brief oraz blokada akceptacji niegotowego filmu.
- Panel przeglądarkowy wczytuje projekt; przycisk akceptacji jest zablokowany
  dla niegotowego przykładu. Bez publikowania publicznej aplikacji.
- RSS/Atom i przechwytywanie rzeczywistej publicznej strony sprawdzono sieciowo.
  Zapisano pełny screen, wycinek, tekst, URL, hash i stan zasobów.
- HyperFrames: lint, runtime, layout, motion i contrast. Brak błędów i pełne
  wykonanie kontroli w przeglądarce; 3 ostrzeżenia o pojedynczym pliku ze scenami.
- MP4 wyrenderowany: 1080×1920, 30 fps, 12 sekund, 1 159 910 bajtów.
  FFprobe potwierdził parametry; obejrzano klatkę wyciągniętą z pliku i podglądy.
  Przykład jest oznaczony jako dane umowne i nie ma narracji. Nie jest publikacją.
  Tryb raportowany przez renderer: screenshot capture / software GPU; czas 21,2 s.
- Testowy MP4 zarejestrowano w lokalnym projekcie z hashem i powiązaniem z planem.

## Ograniczenia i rozpoznane ostrzeżenia

Starlette zgłasza ostrzeżenie o przyszłej zmianie transportu klienta testowego.
Wszystkie testy wykonały się i przeszły; używany produkcyjny serwer działa.
Ostrzeżenia HyperFrames dotyczą modularności: monolityczny plik demo zawiera
trzy sceny. Brak błędów układu, kontrastu lub animacji. Filmy docelowe można
rozbić na subkompozycje, by wygodniej edytować je na osi czasu.

Pierwsze pobieranie dodatkowego Chromium z cdn.playwright.dev zostało zablokowane
przez politykę sieci. Zastąpiono je dostępnym systemowym Chromium 151,
który przeszedł rzeczywiste testy. Instalator nie wymaga tego pobrania.
Bezpośrednie żądania HTTPS w Chromium napotkały brak zaufania do certyfikatu
proxy. Capture używa zweryfikowanego transportu httpx, zachowując oryginalne
URL i dokumenty. Weryfikacja TLS pozostaje włączona.

Strona GitHub wczytała tekst, ale część zewnętrznych zasobów była zablokowana:
github.githubassets.com, avatars.githubusercontent.com, camo.githubusercontent.com
oraz private-user-images.githubusercontent.com. Metadane zachowały te braki.
Drugi test na oryginalnym dokumencie raw.githubusercontent.com miał komplet
zasobów, pełny screen oraz wycinek. Rozszerzenie sieci w draftcie nie oznacza,
że brakujące zasoby już wczytały się w bieżącym procesie.

## Jeszcze niewykonane

- Aktualny news przez Tavily i pełna redakcyjna produkcja przez `studio agent`.
- Utworzenie i trening własnego awatara, dobór polskiego głosu i test lip sync.
- Upload, szkic i analityka na prawdziwym koncie Postiz. Test HTTP używał mocków.
- Montaż nagrania użytkownika przez video-use — nie dostarczono nagrania.
- Pobieranie konkretnego filmu YouTube — użytkownik nie podał materiału,
  a domeny i dostęp do aktualnego wyszukiwania wymagają konfiguracji.
- Harmonogram na stale działającym serwerze i zewnętrzny panel OpenCreator.

Brakuje kluczy Tavily, DeepSeek, Postiz, opcjonalnych HeyGen/Pexels oraz zdjęć użytkownika.
Źródła w fixture testów i oceny kreatywne są jawnie testowe. Nie stanowią
przeprowadzonego researchu ani obejrzanego filmu redakcyjnego.

## Trwałość

Repozytorium było puste, z prawidłową symboliczną gałęzią bez commita.
Nowe pliki są lokalne; nie wykonano commit/push. Zależności upstream są
cache instalacji w `.tools`, nie dodatkowymi projektami środowiska.
Instrukcje instalacji i startu oraz wymagania dostępu zapisuje się w draftcie.
Draft nie uruchamia instalacji ani nie publikuje konfiguracji. Snapshot wymaga
przeglądu, zapisania zmian i publikacji środowiska przez użytkownika.
Odtworzenie w nowym zadaniu nie zostało sprawdzone; brak zdalnego commita
oznacza, że sam świeży clone nie odtworzy tych nowych plików.

## Aktualizacja: lokalne modele, DeepSeek i ZIP

- 31 testów przeszło po dodaniu adapterów. Nowe testy sprawdzają CPU/CUDA,
  blokadę równoczesnej pracy, limit audio, rzeczywistą normalizację i walidację
  MP4 z fixture modelu, rejestrację materiału i unieważnienie akceptacji.
  DeepSeek ma mock HTTP, walidację identyfikatorów i odrzucanie urwanego JSON;
  propozycja nie zmienia automatycznie zatwierdzonego manifestu.
- SadTalker z przypiętego commita: oddzielny Python 3.10, PyTorch 2.1.2+cpu,
  wagi ze źródeł upstream, `pip check`, importy/inference --help i avatar-doctor.
  Instalator wykonano ponownie: zgodne hashe cache, pakiety i importy przeszły.
  Poprawiono izolację budowania BasicSR, aby nie pobierała innego PyTorch.
- Rzeczywiste generowanie SadTalker na Linux/CPU: 2,0 s filmu ze zdjęcia
  i audio przykładu upstream, 256px, batch 1, bez enhancera. Trwało 237,88 s
  przy ograniczeniu obliczeń do 4 wątków. MP4 ma obraz i audio; adapter
  zarejestrował plik, hashe i potrzebę przeglądu. To test techniczny na obcym
  przykładzie, nie awatar użytkownika ani test polskiej wymowy. Wynik jest
  w lokalnym data/validation/sadtalker-smoke.json; dane testowe nie trafiają do ZIP.
- Pełny `scripts/setup.sh` wykonano po zmianach. Testy przeszły; HyperFrames
  sprawdza kompozycję przez prawdziwy Chromium (ok:true, browserSkipped:false).
- ZIP rozpakowano do nowego katalogu w /tmp, wykonano `uv sync --frozen`,
  założono świeży projekt i odczytano go przez API. ROOT wskazuje nowy katalog.
  Potwierdzono domyślny SadTalker, opcjonalny DeepSeek i bramkę jakości.
  `scripts/start.sh` uruchomił tam serwer, a rzeczywisty /health zwrócił HTTP 200.
- Paczka źródeł ma manifest SHA-256 każdego pliku i kontrolę CRC ZIP.
  Nie zawiera .env, .git, SQLite, zdjęć użytkownika, kluczy, modeli ani cache.

RTX 4070/WSL2, InfiniteTalk CUDA i Mac mini M4 nie są dostępne w tej maszynie.
Nie deklarujemy szybkości, zużycia pamięci ani jakości na tych komputerach.
Polskie audio użytkownika i podobieństwo własnej twarzy wymagają jego materiałów.
DeepSeek nie został wywołany na prawdziwym koncie — klucz jest jeszcze nieobecny.
