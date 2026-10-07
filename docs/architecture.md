# Plan studia wideo AI

Stan rozpoznania: 7 października 2026 r. Dokument opisuje zaakceptowaną architekturę. Lokalna implementacja jest w tym
repozytorium; aktualny zakres i wyniki testów opisują README.md oraz validation.md.
Usługi zewnętrzne wymagają kluczy i testu na koncie użytkownika.

## Cel i zaakceptowane preferencje

- Cały proces od wyszukiwania tematów do filmu i analizy wyników.
- Bez n8n.
- Polskie newsy, dyskusje, kontrowersje i wydarzenia ze świata twórców internetowych.
- Weryfikacja istotnych informacji w kilku niezależnych źródłach.
- Animacje, wizualizacje liczb, osi czasu i mechanizmów w HyperFrames.
- Opcjonalny montaż własnych nagrań przez video-use.
- Własny awatar tworzony ze zdjęć.
- Postiz do kalendarza, publikacji i dostępnych statystyk.

Przykłady wskazane przez użytkownika służą określeniu formatu. Nie stanowią
zweryfikowanego opisu wydarzeń ani ustalenia zarzutów wobec konkretnych osób.

## Podział odpowiedzialności

| Element | Rola |
|---|---|
| OpenCreator | Opcjonalny panel projektów, rozmów, harmonogramów i wyników zadań Codex. |
| Codex | Agent wykonujący zadania i korzystający z narzędzi wyszukiwania, skilli oraz lokalnych programów. |
| OpenMontage | Plan produkcji, scenariusz, sceny, dobór materiałów, montaż, kontrola jakości i zapis postępu. |
| HyperFrames | Animacje, wykresy, osie czasu, cytaty, infografiki, napisy i kompozycja. |
| SadTalker / InfiniteTalk | Lokalny awatar ze zdjęcia i audio; RTX 4070 przez WSL2, SadTalker CPU na Macu. |
| HeyGen | Opcjonalne utworzenie awatara i renderowanie prezentera przez API. |
| DeepSeek | Opcjonalne propozycje scenariusza z zebranego manifestu, do przeglądu. |
| video-use | Ścieżka dla własnych nagrań: transkrypcja, wybór ujęć, cięcia, napisy i oprawa. |
| Postiz | Przyjęcie gotowych materiałów, szkice, harmonogram publikacji oraz dostępne metryki. |

OpenMontage jest sterowane instrukcjami dla agenta; nie jest samodzielnym,
stale działającym monitorem newsów. Harmonogram i wykonujący go runtime muszą
działać na komputerze lub serwerze. Nie należy zakładać ciągłego działania
tej sesji środowiska cloud.

OpenCreator dokumentuje harmonogramy z trwałymi rozmowami i wykonywaniem
szeregowym (`queue` albo `skip`). Połączenie jego zadań z OpenMontage,
HyperFrames i Postiz jest projektem integracji, a nie sprawdzonym już gotowym
pakietem instalowanym jednym poleceniem.

## Własny awatar

OpenCreator v3.2.5 oznacza narzędzie Digital Avatar jako **In development**.
Nie należy opierać gotowego awatara użytkownika na tej funkcji.

Oficjalne skille HeyGen dokumentują trzy ścieżki:

- `photo`: awatar ze zdjęcia prawdziwej osoby.
- `prompt`: postać wygenerowana z opisu.
- `digital_twin`: awatar z krótkiego nagrania wideo.

Lokalnie zaczynamy od SadTalker; konfigurację opisuje `local-avatars.md`.
InfiniteTalk wymaga NVIDIA/CUDA i testu pamięci. Mac mini M4 pozostaje
komputerem do researchu i montażu oraz opcjonalnego SadTalker CPU.
Poniższy opis HeyGen dotyczy alternatywnej integracji, nie wymaganego dostawcy.

Dla HeyGen pierwszym wariantem jest `photo`. Dokumentacja podaje JPEG
lub PNG, minimum 512×512, wyraźną twarz od przodu i dobre oświetlenie.
Zdjęcie nie dostarcza głosu. Początkowo można dobrać polski głos; użycie
własnego głosu wymaga osobnego materiału audio i wybranej usługi klonowania.
Naturalność, podobieństwo, polska wymowa i synchronizacja ust wymagają testu
krótkiego filmu przed seryjną produkcją.

OpenMontage ma w kodzie adapter `heygen_avatar` do pracy z istniejącymi
awatarami: odkrywania wariantów wyglądu, generowania filmu ze skryptu lub
audio oraz wznawiania zadań. Adapter jest oznaczony jako beta. Utworzenie
tożsamości przez skill HeyGen i używanie jej przez OpenMontage trzeba
zweryfikować na koncie użytkownika.

## Proces redakcyjny i produkcyjny

1. **Wyszukanie tematów.** Agent sprawdza uzgodnione źródła, świeżość publikacji
   oraz oryginalne wypowiedzi i odróżnia nowe zdarzenie od wznowienia starego.
   Wymaga działającego narzędzia wyszukiwania aktualnej sieci; samo zainstalowanie
   OpenMontage nie zapewnia dostępu do wszystkich serwisów.
2. **Karta tematu.** Zapisuje źródła, daty publikacji i pobrania, chronologię,
   konkretne cytaty, stanowiska stron oraz pytania pozostające bez odpowiedzi.
   Cytat z filmu ma również znacznik czasu.
3. **Weryfikacja twierdzeń.** Każde istotne twierdzenie jest powiązane ze źródłem
   i oznaczone jako fakt, zarzut, opinia lub informacja niepotwierdzona.
   Powielenie jednej wiadomości przez kilka portali nie jest niezależnym
   potwierdzeniem. Kluczowe twierdzenia weryfikuje się w 2–3 niezależnych
   źródłach, szukając w pierwszej kolejności materiału pierwotnego i stanowisk
   zainteresowanych osób. Agent aktywnie sprawdza także dementi, sprostowania
   i dowody sprzeczne. Komentarze odbiorców służą badaniu reakcji.
   Jeżeli dostępne jest tylko jedno źródło, informacja nie jest przedstawiana
   jako wielokrotnie potwierdzona: trafia do ręcznej oceny albo zostaje
   przedstawiona wyłącznie jako jasno przypisane doniesienie lub wypowiedź.
   Oryginalna wypowiedź potwierdza to, co ktoś powiedział; sama nie dowodzi
   prawdziwości zawartego w niej zarzutu.
4. **Scenariusz.** Początkowa propozycja formatu: 60–90 sekund, pion 9:16,
   hook → kontekst → chronologia → stanowiska → wniosek. To ustawienie do testu,
   a nie potwierdzona preferencja użytkownika dotycząca długości.
5. **Plan scen.** Zdefiniowany cel każdego ujęcia: prezenter, materiał źródłowy,
   cytat, oś czasu, wykres lub ilustracja mechanizmu. Wizualizowane liczby mają
   źródło, jednostkę i okres. Obraz generowany jest ilustracją, a nie dowodem
   autentycznego zdarzenia.
6. **Materiały.** HeyGen renderuje krótkie wejścia prezentera, HyperFrames
   wizualizuje treść, a opcjonalnie video-use opracowuje nagrania użytkownika.
   Przy materiałach zewnętrznych zapisuje się źródło i uprawnienie do użycia.
7. **Montaż i ocena.** Kontrola sensu cięć, tempa, napisów, polskiej wymowy,
   głośności, czytelności, synchronizacji ust oraz zgodności ze scenariuszem.
8. **Przekazanie do Postiz.** Film, okładka, opis i kanały trafiają początkowo
   jako szkic do przeglądu. Publikacja wymaga skonfigurowanych kont i przyjętej
   przez użytkownika polityki publikowania.
9. **Ocena wyników.** Zbierane są metryki dostępne dla danego kanału; agent
   porównuje formaty i aktualizuje zalecenia do kolejnych materiałów.

Wynikiem weryfikacji jest tabela: twierdzenie → źródło pierwotne → niezależne
potwierdzenie → stanowisko drugiej strony/dementi → daty i znaczniki czasu →
status → dozwolone sformułowanie w scenariuszu. Przy każdej kontroli zapisuje
się również datę sprawdzenia. Ponowna kontrola odbywa się przed planowaną
publikacją, aby uwzględnić nowe sprostowanie lub zmianę sytuacji.

OpenMontage dokumentuje obowiązkowe punkty akceptacji, w tym propozycję,
scenariusz, plan scen, materiały i publikację. Nie należy przedstawiać
domyślnego procesu jako całkowicie bezobsługowego ani zakładać, że bramki
zostały już dostosowane do projektu.

## Wyszukiwanie i przygotowanie materiałów wizualnych

Research obejmuje od początku zarówno informacje, jak i potencjalne materiały
do pokazania. Przed finalnym scenariuszem sprawdza się dostępność kluczowych
ujęć i zrzutów; później każda scena dostaje własne zapotrzebowanie na materiał.

### Źródła i sposób wyboru

| Typ materiału | Sposób pozyskania | Zastosowanie |
|---|---|---|
| Fragment oryginalnego filmu, wywiadu lub podcastu | Wyszukanie oryginalnej publikacji, transkrypcja z czasami, wybór fragmentu, odsłuch i obejrzenie szerszego kontekstu | Pokazanie konkretnej wypowiedzi lub zdarzenia. |
| Screen artykułu lub publicznego posta | Otwarcie rzeczywistej strony i zrzut przez przeglądarkę, np. Playwright; zapis pełnego kontekstu oraz wycinka do montażu | Nagłówek, cytat, stanowisko, data i źródło. |
| Zdjęcie osoby, produktu lub wydarzenia | Pierwszeństwo dla oficjalnych publikacji i materiałów prasowych; weryfikacja osoby, daty oraz pochodzenia zdjęcia | Identyfikacja rzeczywistego bohatera i konkretnego wydarzenia. |
| Materiał ilustracyjny/B-roll | Wyszukiwanie po scenie i intencji w Pexels, Pixabay, Wikimedia Commons lub innych dostępnych bibliotekach; sprawdzenie warunków konkretnego zasobu | Tło i wizualne wyjaśnienie ogólnego pojęcia. |
| Wykres, oś czasu, diagram | Dane i daty z karty tematu → kompozycja w HyperFrames | Wyjaśnienie skali, chronologii lub mechanizmu. |
| Obraz generowany przez AI | Generacja z briefu sceny, oznaczenie jako ilustracja, kontrola spójności wizualnej | Ilustracja pojęcia, metafora lub tło. |

Dla każdego miejsca w filmie agent wyszukuje zwykle 3–5 kandydatów i ocenia:

- zgodność z konkretną wypowiedzią narratora i celem sceny;
- autentyczność, datę i właściwą osobę lub wydarzenie, gdy materiał jest źródłowy;
- jakość obrazu i audio oraz przydatność do pionowego kadru;
- czytelność tekstu po wyświetleniu na telefonie;
- spójność z oprawą kanału i różnorodność względem sąsiednich ujęć;
- dostępność i podstawę użycia materiału.

Agent ogląda podglądy i wybrane fragmenty; nie wybiera wyłącznie na podstawie
tytułu, nazwy pliku albo opisu wyszukiwarki. Wyszukiwanie semantyczne pomaga
dobierać stock, ale nie potwierdza autentyczności wydarzenia ani tożsamości.

### Przygotowanie do montażu

- Przy filmie źródłowym zapisuje się link, autora, datę i zakres czasowy.
  Wycinek zachowuje sens wypowiedzi; krótszy montaż wymaga sprawdzenia kontekstu.
- Screen artykułu zachowuje autentyczną treść. W montażu można wyróżnić zdanie,
  zbliżyć fragment lub umieścić zrzut w ramce, zachowując podpis źródła i datę.
  Nie tworzy się imitacji artykułu ani dopisanego cytatu.
- Drobny tekst z całej strony zastępuje się w warstwie montażowej czytelnym,
  wiernym cytatem z widocznym wskazaniem źródła; oryginalny screen zostaje w aktach.
- Materiały źródłowe i ilustracyjne są oznaczone osobno. Stock, ilustracja AI
  albo archiwalne ujęcie nie jest przedstawiane jako zapis omawianego zdarzenia.
- Liczby na wykresach mają źródło, okres i jednostkę; wykres przedstawia dane
  bez zmieniania skali w celu wywołania silniejszego wrażenia.
- Najpierw pobiera się lekki materiał do oceny. Wybrane ujęcia przygotowuje się
  w jakości odpowiedniej do finalnego filmu, bez zakładania, że upscale odtworzy
  utracone szczegóły.

### Rejestr materiałów

Każdy zasób ma wpis: identyfikator, scena, rola źródłowa/ilustracyjna,
oryginalny URL, autor, data publikacji i pobrania, znacznik czasu lub wycinek,
lokalny plik, parametry techniczne, licencja/zgoda/podstawa cytatu,
wymagany podpis, status oceny i zastosowane modyfikacje. Zweryfikowane pliki
można ponownie wykorzystać w kolejnych produkcjach z zachowaniem metadanych.

Publiczna dostępność filmu lub zdjęcia nie daje automatycznie uprawnienia do
publikowania go we własnym materiale. Krótki fragment z podpisem również nie
jest automatycznie dopuszczalny. Warunki licencji, zgoda albo zasadność cytatu
w materiale komentującym wymagają ustalenia dla konkretnego użycia.
Nie ma uniwersalnej liczby sekund gwarantującej możliwość wykorzystania klipu.

### Co już istnieje, a co wymaga integracji

W kodzie OpenMontage są `transcript_fetcher`, `video_downloader`,
`direct_clip_search`, `corpus_builder` i `clip_search`. Pobieranie mediów
zależy od dostępności źródła; jego obecność w kodzie nie potwierdza, że każde
wideo YouTube będzie dostępne z tej maszyny. Downloader domyślnie używa
720p do analizy i udostępnia także ustawienie 1080p.

HyperFrames dokumentuje skill `media-use` do przygotowania obrazów, ikon,
logotypów, muzyki i innych materiałów. Przechwytywanie artykułów w przeglądarce,
rejestr źródeł i praw oraz specyficzny dla polskich newsów dobór autentycznych
materiałów mają zostać spięte w proponowanym własnym skillu researchu wizualnego.
Nie zostały jeszcze wdrożone ani sprawdzone na przykładowym newsie.

## Skille

Istniejące pakiety do wykorzystania etapami:

- HyperFrames: `faceless-explainer`, `talking-head-recut`, `embedded-captions`,
  `hyperframes-animation`, `hyperframes-audio` oraz `media-use`.
- video-use: workflow montażu nagrań użytkownika.
- HeyGen: `heygen-avatar` i `heygen-video`.
- iart-ai/tiktok-video-skills: `short-form-video` oraz `caption-animation`.
- OpenMontage: dyrektorzy etapów, reviewer i zapis checkpointów.
- Remotion Agent Skills: opcjonalnie dla kompozycji wykonanych w Remotion.

Proponowane własne skille do opracowania, **jeszcze nieistniejące w tym
projekcie**:

- Research polskich newsów: monitoring, ocena świeżości i karty tematów.
- Research wizualny: materiały źródłowe, screeny, fragmenty wideo, B-roll,
  ocena kandydatów i rejestr pochodzenia zasobów.
- Weryfikacja redakcyjna: źródła, chronologia, cytaty, status twierdzeń.
- Scenariusz kanału: stała osobowość narratora, rytm i format serii.
- Ocena filmu: kontrola techniczna i redakcyjna gotowego materiału.
- Przekazanie do Postiz i analiza wyników.

Każdy etap ma jednego prowadzącego i jasno określone wejście oraz wynik.
Nie należy uruchamiać wielu skilli jednocześnie z konkurencyjnymi zasadami
montażu, akceptacji i renderowania.

## Publikacja i analityka

Postiz dokumentuje bezpośredni dostęp przez MCP i API. n8n nie jest potrzebne.
Zakres metryk różni się między platformami. Dokumentacja wymienia m.in.
wyświetlenia i interakcje dla TikToka/Instagrama oraz czas oglądania i średni
procent obejrzenia dla YouTube. Nie należy zakładać dostępności identycznej
krzywej retencji na każdym kanale.

Postiz Cloud zmniejsza zakres prac przy aplikacjach deweloperskich platform.
Self-hosting wymaga własnego wdrożenia i odpowiednich integracji/OAuth.
Wybór wariantu pozostaje otwarty.

## Pierwszy test integracji

Proponowany pilot: jeden polski film 60–90 s o zweryfikowanym wydarzeniu,
z awatarem użytkownika, jedną osią czasu i jedną wizualizacją danych lub
cytatu. Ocenia się podobieństwo awatara, głos, polską wymowę, synchronizację
napisów, tempo, źródła oraz możliwość zapisania szkicu w Postiz.

Po takim teście można oszacować koszt filmu, czas produkcji i zakres
niezbędnych poprawek. Na tym etapie nie ma podstaw do gwarancji kosztu,
jakości ani wysokiej retencji.

Do faktycznego wdrożenia pozostają: wybór miejsca działania i budżetu,
dostęp do wyszukiwania, konto/usługa awatara i głosu, zdjęcie użytkownika,
docelowe kanały oraz połączenie Postiz. Sekrety dostarcza się przez właściwe
ustawienia usług lub środowiska, nigdy w treści dokumentu ani w repozytorium.

## Źródła sprawdzone przy projektowaniu

- [OpenCreator v3.2.5: status narzędzi i harmonogramy](https://github.com/krillinai/OpenCreator/blob/v3.2.5/README.md)
- [OpenMontage: architektura](https://github.com/calesthio/OpenMontage/blob/main/PROJECT_CONTEXT.md)
- [OpenMontage: bramki jakości i akceptacji](https://github.com/calesthio/OpenMontage/blob/main/README.md#production-governance)
- [OpenMontage: adapter HeyGen](https://github.com/calesthio/OpenMontage/blob/main/tools/avatar/heygen_avatar.py)
- [HeyGen: tworzenie awatara](https://github.com/heygen-com/skills/blob/master/heygen-avatar/references/avatar-creation.md)
- [HyperFrames: skille i workflow](https://github.com/heygen-com/hyperframes)
- [video-use](https://github.com/browser-use/video-use)
- [TikTok Video Skills](https://github.com/iart-ai/tiktok-video-skills)
- [HyperFrames: media-use](https://github.com/heygen-com/hyperframes/blob/main/skills/media-use/SKILL.md)
- [OpenMontage: wyszukiwanie stocków](https://github.com/calesthio/OpenMontage/blob/main/tools/video/direct_clip_search.py)
- [OpenMontage: dobór klipów do scen](https://github.com/calesthio/OpenMontage/blob/main/tools/video/clip_search.py)
- [OpenMontage: transkrypcje YouTube](https://github.com/calesthio/OpenMontage/blob/main/tools/analysis/transcript_fetcher.py)
- [OpenMontage: pobieranie filmów](https://github.com/calesthio/OpenMontage/blob/main/tools/analysis/video_downloader.py)
- [Postiz: narzędzia MCP](https://github.com/gitroomhq/postiz-docs/blob/main/mcp/tools.mdx)
- [Postiz: zakres analityki](https://github.com/gitroomhq/postiz-docs/blob/main/general/analytics.mdx)

Licencje zależności i materiałów stosuje się niezależnie. HyperFrames ma
Apache 2.0, video-use MIT, OpenMontage/Postiz AGPL, a Remotion własną licencję.
video-talkcraft wymaga zgody autora na użycie komercyjne i nie jest przyjęte
jako domyślna zależność tego planu.
