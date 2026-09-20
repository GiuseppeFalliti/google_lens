# Screen Translator

Applicazione desktop per **Windows 10/11** che permette all'utente di selezionare una porzione dello schermo contenente del testo, riconoscerlo tramite OCR, tradurlo e mostrare la traduzione in sovrapposizione sull'area selezionata.

Il progetto deve essere sviluppato inizialmente come MVP, ma con un'architettura abbastanza modulare da poter evolvere successivamente verso una modalità simile a Google Lens, capace di rilevare e tradurre automaticamente più aree testuali presenti sullo schermo.

---

# 1. Obiettivo del progetto

Realizzare un programma Windows che permetta di:

1. avviare l'applicazione;
2. lasciarla attiva in background;
3. premere la hotkey globale:

```text
CTRL + SHIFT + T
```

4. oscurare leggermente lo schermo;
5. selezionare con il mouse una regione rettangolare;
6. catturare l'immagine della regione selezionata;
7. eseguire OCR sull'immagine;
8. tradurre il testo rilevato;
9. visualizzare la traduzione in un overlay nero semitrasparente posizionato sopra la regione selezionata.

L'utente deve poter configurare:

- lingua sorgente;
- lingua destinazione;
- motore di traduzione;
- eventuali credenziali/API URL;
- hotkey;
- comportamento base dell'overlay.

---

# 2. Scope della prima versione

La prima versione deve essere volutamente semplice.

## Funzioni obbligatorie

- Windows 10/11.
- GUI desktop.
- System tray.
- Hotkey globale `CTRL + SHIFT + T`.
- Selezione manuale di una regione dello schermo.
- Supporto multi-monitor.
- Screenshot della regione selezionata.
- OCR del testo.
- Selezione lingua sorgente.
- Selezione lingua destinazione.
- Traduzione tramite provider intercambiabile.
- Provider Argos Translate.
- Provider DeepL.
- Provider LibreTranslate.
- Overlay nero semitrasparente.
- Chiusura overlay con `ESC`.
- Chiusura overlay facendo click fuori dall'area tradotta.
- Nuova selezione premendo nuovamente `CTRL + SHIFT + T`.
- Gestione degli errori senza chiudere l'applicazione.
- Salvataggio delle impostazioni.

## Non richiesto nell'MVP

Non implementare ancora:

- OCR continuo dello schermo;
- traduzione in tempo reale frame-by-frame;
- sostituzione grafica perfetta del testo originale;
- ricostruzione dello sfondo sotto il testo;
- traduzione automatica di tutto lo schermo;
- modelli AI personalizzati;
- acquisizione video;
- account utente;
- server backend;
- database remoto.

Queste funzionalità potranno essere aggiunte successivamente.

---

# 3. Linguaggio e stack

Utilizzare:

```text
Python 3.11 o 3.12
```

Preferire Python 3.11 se una dipendenza OCR/ML presenta problemi di compatibilità con Python 3.12.

## GUI

Utilizzare:

```text
PySide6
```

PySide6 deve gestire:

- finestra principale;
- pagina impostazioni;
- selezione area;
- overlay;
- system tray;
- notifiche/errori UI.

## Screen capture

Utilizzare inizialmente:

```text
mss
```

Motivi:

- semplice;
- veloce;
- compatibile con più monitor;
- adatto a screenshot di regioni arbitrarie.

Incapsulare comunque la cattura schermo dietro un'interfaccia, in modo da poter sostituire in futuro `mss` con `Windows.Graphics.Capture`.

## OCR

Utilizzare:

```text
PaddleOCR
```

L'OCR deve restituire un risultato strutturato, non soltanto una singola stringa.

Ogni elemento rilevato dovrebbe contenere almeno:

```python
{
    "text": "...",
    "confidence": 0.98,
    "box": [...]
}
```

Anche se nell'MVP verrà mostrata una singola traduzione complessiva, conservare bounding box e confidence perché saranno necessarie nelle versioni future.

## Traduzione

Implementare tre provider:

```text
Argos Translate
DeepL
LibreTranslate
```

Il sistema di traduzione deve essere modulare.

Non scrivere logica DeepL, Argos o LibreTranslate direttamente nella GUI.

---

# 4. Architettura generale

Il flusso principale deve essere:

```text
Global Hotkey
      |
      v
Region Selector
      |
      v
Screen Capture
      |
      v
Image preprocessing
      |
      v
OCR Engine
      |
      v
Extracted Text
      |
      v
Translation Service
      |
      v
Selected Translation Provider
      |
      v
Translated Text
      |
      v
Overlay Manager
```

La GUI non deve occuparsi direttamente dell'OCR o delle chiamate HTTP.

---

# 5. Struttura consigliata del progetto

Creare indicativamente questa struttura:

```text
screen-translator/
|
|-- main.py
|
|-- src/
|   |
|   |-- app/
|   |   |-- application.py
|   |   |-- tray_manager.py
|   |   `-- hotkey_manager.py
|   |
|   |-- capture/
|   |   |-- screen_capture.py
|   |   |-- mss_capture.py
|   |   `-- region_selector.py
|   |
|   |-- ocr/
|   |   |-- base_ocr.py
|   |   |-- paddle_ocr.py
|   |   `-- models.py
|   |
|   |-- translation/
|   |   |-- base_translator.py
|   |   |-- translation_service.py
|   |   |-- argos_translator.py
|   |   |-- deepl_translator.py
|   |   `-- libretranslate_translator.py
|   |
|   |-- overlay/
|   |   |-- overlay_manager.py
|   |   `-- translation_overlay.py
|   |
|   |-- ui/
|   |   |-- main_window.py
|   |   |-- settings_page.py
|   |   `-- status_widget.py
|   |
|   |-- config/
|   |   |-- settings.py
|   |   `-- settings_manager.py
|   |
|   |-- services/
|   |   `-- translation_pipeline.py
|   |
|   |-- utils/
|   |   |-- logger.py
|   |   |-- geometry.py
|   |   `-- image_utils.py
|   |
|   `-- exceptions.py
|
|-- tests/
|   |-- test_settings.py
|   |-- test_translation_service.py
|   `-- test_geometry.py
|
|-- assets/
|
|-- logs/
|
|-- requirements.txt
|-- requirements-dev.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

La struttura può essere adattata se necessario, ma bisogna mantenere una separazione netta tra:

```text
UI
capture
OCR
translation
overlay
configuration
```

---

# 6. Hotkey globale

La hotkey predefinita è:

```text
CTRL + SHIFT + T
```

Dato che la prima versione è esclusivamente Windows, preferire l'API Win32:

```text
RegisterHotKey
UnregisterHotKey
```

richiamata tramite:

```text
ctypes
```

oppure `pywin32` se realmente necessario.

Non dipendere dal focus della finestra.

La hotkey deve funzionare anche quando:

- l'applicazione è minimizzata;
- la finestra principale è chiusa ma l'app rimane nella tray;
- un'altra applicazione è in foreground.

Creare una classe dedicata:

```python
class HotkeyManager:
    def register(self, hotkey: str) -> None:
        ...

    def unregister(self) -> None:
        ...

    def hotkey_pressed(self):
        ...
```

Il codice Win32 non deve essere sparso nella GUI.

---

# 7. Supporto multi-monitor

Il programma deve supportare configurazioni con più monitor.

Bisogna considerare:

- monitor posizionati a sinistra del monitor principale;
- coordinate Windows negative;
- monitor con risoluzioni diverse;
- scaling DPI differente;
- virtual desktop Windows.

La selezione deve poter attraversare correttamente l'intero desktop virtuale.

Non assumere che:

```text
x >= 0
y >= 0
```

Prestare particolare attenzione alle conversioni tra:

```text
coordinate Qt
coordinate desktop virtuale
coordinate MSS
```

Creare funzioni centralizzate per queste conversioni.

---

# 8. DPI awareness

L'applicazione deve gestire correttamente il DPI scaling di Windows.

È importante evitare che:

```text
selezione utente
```

e:

```text
screenshot acquisito
```

abbiano coordinate differenti.

Configurare l'applicazione come DPI aware prima della creazione della GUI, utilizzando una modalità Windows appropriata, preferibilmente Per-Monitor DPI Aware.

Testare almeno:

```text
100%
125%
150%
```

di scaling.

---

# 9. Selezione area

Quando l'utente preme:

```text
CTRL + SHIFT + T
```

deve partire la modalità selezione.

## Comportamento

1. catturare uno snapshot del desktop;
2. mostrare un overlay fullscreen sul desktop virtuale;
3. oscurare leggermente lo schermo;
4. cambiare il cursore in crosshair;
5. mouse down = inizio selezione;
6. mouse move = aggiornamento rettangolo;
7. mouse up = conferma;
8. `ESC` = annulla.

Durante il drag visualizzare il rettangolo selezionato.

Esempio:

```text
+------------------------------------------------+
|                                                |
|       schermata oscurata                       |
|                                                |
|        +--------------------------+            |
|        |                          |            |
|        |      area selezionata    |            |
|        |                          |            |
|        +--------------------------+            |
|                                                |
+------------------------------------------------+
```

Il rettangolo selezionato deve essere trasformato in coordinate del desktop reale e passato al modulo di capture.

---

# 10. Screen Capture API

Definire un'interfaccia:

```python
from abc import ABC, abstractmethod

class ScreenCapture(ABC):

    @abstractmethod
    def capture_region(self, x: int, y: int, width: int, height: int):
        pass
```

Implementazione iniziale:

```python
class MSSScreenCapture(ScreenCapture):
    ...
```

Il risultato deve essere convertibile facilmente in:

```text
PIL Image
numpy.ndarray
```

senza scrivere file temporanei su disco.

Lo screenshot deve rimanere in memoria.

---

# 11. Pre-processing immagine

Creare un modulo leggero di preprocessing.

Per l'MVP utilizzare solo tecniche che migliorano realmente l'OCR:

- conversione RGB;
- eventuale resize;
- eventuale contrast enhancement;
- eventuale grayscale.

Non applicare filtri aggressivi per default.

Esporre il preprocessing come funzione separata:

```python
def preprocess_for_ocr(image):
    ...
```

In futuro dovrà essere possibile confrontare facilmente più strategie.

---

# 12. OCR abstraction

Creare:

```python
from abc import ABC, abstractmethod

class OCREngine(ABC):

    @abstractmethod
    def recognize(self, image) -> "OCRResult":
        pass
```

Definire strutture dati.

Esempio:

```python
from dataclasses import dataclass

@dataclass
class OCRTextBlock:
    text: str
    confidence: float
    box: list[tuple[float, float]]

@dataclass
class OCRResult:
    blocks: list[OCRTextBlock]
    full_text: str
```

Implementare:

```python
class PaddleOCREngine(OCREngine):
    ...
```

---

# 13. PaddleOCR

Configurare PaddleOCR principalmente per OCR di testo UI, giochi e applicazioni desktop.

Non inizializzare il modello ad ogni traduzione.

Il modello OCR deve essere caricato una volta all'avvio o al primo utilizzo e poi riutilizzato.

Per evitare che l'avvio della GUI sembri bloccato, considerare lazy initialization.

Esempio:

```text
prima richiesta
     |
     +--> carica modello
     |
     +--> OCR

richieste successive
     |
     +--> riusa modello
```

La GUI non deve bloccarsi durante l'OCR.

Eseguire OCR e traduzione su worker/thread separato.

---

# 14. Preparazione del testo OCR

Prima della traduzione:

1. eliminare stringhe vuote;
2. rimuovere spazi inutili;
3. ordinare i blocchi OCR in modo coerente;
4. preservare il più possibile righe e punteggiatura;
5. non tradurre se non è stato rilevato testo.

Per l'MVP è possibile unire i blocchi in:

```text
full_text
```

prima di inviarli al traduttore.

---

# 15. Translation Provider abstraction

Creare una classe astratta comune.

Esempio:

```python
from abc import ABC, abstractmethod

class TranslationProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        pass
```

Implementazioni:

```text
ArgosTranslator
DeepLTranslator
LibreTranslateTranslator
```

La GUI deve comunicare solamente con:

```text
TranslationService
```

e non direttamente con i provider.

---

# 16. Translation Service

Implementare una classe:

```python
class TranslationService:

    def __init__(self, providers, settings):
        ...

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        ...
```

Responsabilità:

- recuperare il provider selezionato;
- validare configurazione;
- eseguire traduzione;
- convertire errori specifici in errori comuni;
- gestire timeout;
- preparare in futuro cache e fallback.

---

# 17. Argos Translate

Argos Translate deve essere il provider offline.

Caratteristiche:

- nessuna API remota obbligatoria;
- modelli installati localmente;
- traduzione eseguita sul PC.

Il programma deve verificare se esiste il modello richiesto.

Esempio:

```text
English -> Italian
```

Se non è installato:

```text
Modello di traduzione English → Italian non installato.
```

Per l'MVP non scaricare modelli silenziosamente senza informare l'utente.

È accettabile aggiungere nella GUI un pulsante:

```text
Download language model
```

oppure una procedura guidata.

Il codice di download/installazione deve stare nel modulo Argos e non nella GUI.

---

# 18. DeepL

DeepL deve essere un provider opzionale.

Configurazione richiesta:

```text
API key
API endpoint/configurazione account
```

Non inserire API key nel codice.

Non committare credenziali nel repository.

Leggere la chiave tramite:

- impostazioni locali;
- variabile d'ambiente;
- oppure file `.env` ignorato da Git.

Esempio:

```env
DEEPL_API_KEY=
```

Gestire correttamente:

- chiave mancante;
- chiave invalida;
- quota/rate limit;
- timeout;
- errore di rete;
- lingua non supportata.

Non assumere nel codice l'esistenza di una quota gratuita permanente: l'accesso e i limiti dipendono dal piano DeepL dell'utente.

---

# 19. LibreTranslate

Implementare un provider HTTP configurabile.

Impostazioni:

```text
Base URL
API key opzionale
```

Esempio di configurazione:

```text
http://localhost:5000
```

Deve essere possibile utilizzare:

- server LibreTranslate self-hosted;
- istanze remote compatibili.

Non hardcodare un'istanza pubblica come dipendenza obbligatoria.

La API key deve essere opzionale perché dipende dalla configurazione del server.

---

# 20. Lingue

L'utente ha scelto modalità:

```text
Source language selectable
Target language selectable
```

Nella GUI devono quindi esistere due combobox:

```text
From: [English]
To:   [Italian]
```

Per la prima release includere almeno:

```text
English
Italian
French
German
Spanish
Portuguese
```

L'architettura deve però permettere di aggiungere altre lingue facilmente.

Creare mapping separati tra codici applicativi e codici provider.

Esempio:

```python
LANGUAGES = {
    "English": "en",
    "Italian": "it",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
}
```

Se DeepL o un altro provider utilizza codici differenti, effettuare la conversione nel provider.

---

# 21. GUI principale

Creare una GUI semplice, moderna e funzionale.

Layout indicativo:

```text
+--------------------------------------------------+
| Screen Translator                               |
+--------------------------------------------------+
|                                                  |
| Translation                                     |
|                                                  |
| From:       [ English          v ]               |
| To:         [ Italian          v ]               |
|                                                  |
| Provider:   [ Argos Translate  v ]               |
|                                                  |
| [ Provider Settings ]                            |
|                                                  |
| ------------------------------------------------ |
|                                                  |
| Hotkey                                           |
| [ CTRL + SHIFT + T             ]                 |
|                                                  |
| [ Translate screen region ]                      |
|                                                  |
| ------------------------------------------------ |
|                                                  |
| Status: Ready                                    |
|                                                  |
+--------------------------------------------------+
```

Aggiungere eventualmente tabs:

```text
General
Translation
Advanced
```

ma evitare una UI eccessivamente complessa.

---

# 22. Provider settings

La GUI deve cambiare i campi visualizzati in base al provider.

## Argos

Mostrare:

```text
Installed language models
Download model
```

## DeepL

Mostrare:

```text
API Key
```

La API key deve essere mascherata.

## LibreTranslate

Mostrare:

```text
Base URL
API Key (optional)
```

---

# 23. System tray

Quando l'utente chiude la finestra principale, l'applicazione deve poter continuare nella system tray.

Tray menu:

```text
Screen Translator

Translate region
Open
Settings
Exit
```

`Exit` deve:

1. unregister hotkey;
2. chiudere overlay;
3. terminare worker;
4. chiudere correttamente QApplication.

---

# 24. Translation pipeline

Creare un servizio centrale:

```python
class TranslationPipeline:
    ...
```

Flusso:

```text
Region
  |
  v
Capture
  |
  v
Preprocess
  |
  v
OCR
  |
  +--> no text --> UI notification
  |
  v
Translation
  |
  +--> error --> UI notification
  |
  v
Overlay
```

La GUI non deve implementare questo flusso direttamente.

Possibile API:

```python
result = pipeline.translate_region(
    region=region,
    source_language="en",
    target_language="it",
)
```

Risultato:

```python
@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    region: Rect
    ocr_result: OCRResult
    provider: str
```

---

# 25. Threading

OCR e rete non devono bloccare il main thread Qt.

Utilizzare:

```text
QThread
```

oppure:

```text
QThreadPool + QRunnable
```

Preferire una soluzione semplice e robusta.

Durante elaborazione mostrare uno stato:

```text
Recognizing text...
```

poi:

```text
Translating...
```

Non lasciare la GUI congelata.

Impedire che l'utente avvii decine di richieste simultanee.

Per l'MVP può esserci una sola pipeline attiva alla volta.

---

# 26. Overlay della traduzione

Per questa versione utilizzare il comportamento A:

```text
rettangolo nero semitrasparente
+
testo tradotto
```

L'overlay deve essere:

- frameless;
- always on top;
- posizionato sulla regione originariamente selezionata;
- con sfondo nero semitrasparente;
- testo bianco;
- padding interno;
- font leggibile;
- word wrapping;
- dimensionamento automatico ragionevole.

Esempio:

```text
+---------------------------------------+
|                                       |
|  Ti serve la chiave blu per aprire    |
|  questa porta.                        |
|                                       |
+---------------------------------------+
```

Utilizzare un'opacità iniziale indicativa intorno al:

```text
75-85%
```

senza hardcodare il valore in punti sparsi.

Salvarlo nelle impostazioni.

---

# 27. Comportamento overlay

L'overlay deve chiudersi con:

```text
ESC
```

Deve chiudersi anche se l'utente fa click fuori dalla regione tradotta.

Una nuova pressione di:

```text
CTRL + SHIFT + T
```

deve:

1. chiudere l'overlay attuale;
2. iniziare una nuova selezione.

Non mostrare più overlay sovrapposti nell'MVP.

---

# 28. Click fuori dall'overlay

Poiché l'overlay occupa solamente la regione tradotta, per rilevare il click esterno usare una soluzione controllata.

Sono accettabili:

### Soluzione A

una finestra Qt trasparente che copre il desktop virtuale e contiene il pannello di traduzione;

oppure:

### Soluzione B

un listener mouse globale Windows.

Preferire la soluzione Qt se non causa problemi con input e multi-monitor.

Evitare dipendenze invasive senza necessità.

---

# 29. Gestione stato

Definire uno stato applicativo semplice.

Esempio:

```text
IDLE
SELECTING
CAPTURING
OCR
TRANSLATING
SHOWING_OVERLAY
ERROR
```

Evitare doppie selezioni simultanee.

Esempio:

```python
class AppState(Enum):
    IDLE = "idle"
    SELECTING = "selecting"
    PROCESSING = "processing"
    SHOWING_OVERLAY = "showing_overlay"
```

---

# 30. Configurazione

Salvare le impostazioni utente localmente.

Possibili soluzioni:

```text
QSettings
```

oppure JSON.

Preferire:

```text
QSettings
```

per i valori normali dell'applicazione.

Configurazione minima:

```text
source_language
target_language
translation_provider
global_hotkey
overlay_opacity
start_minimized
libretranslate_url
```

Prestare attenzione alle API key.

Per l'MVP possono essere memorizzate localmente, ma isolare il codice in modo che in futuro possano essere salvate tramite Windows Credential Manager.

Non loggare mai chiavi API.

---

# 31. Logging

Implementare logging su file.

Directory indicativa:

```text
logs/
```

Loggare:

- startup;
- shutdown;
- registrazione hotkey;
- OCR duration;
- translation duration;
- provider;
- errori;
- eccezioni.

Non loggare per default:

- API key;
- token;
- password.

Evitare anche di salvare automaticamente screenshot dell'utente.

I log non devono contenere immagini catturate.

---

# 32. Error handling

Definire eccezioni applicative comuni.

Esempio:

```python
class ScreenTranslatorError(Exception):
    pass

class CaptureError(ScreenTranslatorError):
    pass

class OCRError(ScreenTranslatorError):
    pass

class TranslationError(ScreenTranslatorError):
    pass

class TranslationConfigurationError(TranslationError):
    pass
```

La GUI deve mostrare errori leggibili.

Esempi:

```text
No text detected in the selected area.
```

```text
DeepL API key is missing.
```

```text
Unable to connect to LibreTranslate.
```

```text
The selected Argos language model is not installed.
```

Non mostrare traceback Python all'utente finale.

Il traceback deve finire nel log.

---

# 33. Timeout e rete

Per DeepL e LibreTranslate impostare timeout.

Non lasciare richieste HTTP indefinite.

Indicativamente:

```text
connect timeout: 5s
read timeout: 15s
```

Utilizzare una libreria HTTP come:

```text
httpx
```

oppure `requests`.

Preferire `httpx` se non aggiunge complessità inutile.

---

# 34. Cache traduzioni

La cache non è obbligatoria per il primo prototipo, ma progettare il servizio in modo che possa essere aggiunta.

Una futura chiave cache potrebbe essere:

```text
provider
source_language
target_language
source_text
```

Esempio:

```python
(
    "deepl",
    "en",
    "it",
    "You need the blue key."
)
```

Non implementare database per l'MVP.

In futuro è sufficiente una cache LRU in memoria.

---

# 35. Sicurezza e privacy

L'applicazione acquisisce contenuti dello schermo.

Perciò:

- non salvare screenshot automaticamente;
- non inviare immagini ai provider di traduzione;
- inviare soltanto il testo OCR;
- Argos deve poter funzionare completamente offline;
- indicare chiaramente quando viene utilizzato un provider online;
- non inserire credenziali nel repository;
- non stampare API key nei log.

PaddleOCR deve lavorare localmente.

Lo screenshot deve essere eliminato dalla memoria quando non più necessario.

---

# 36. Performance

Target ragionevole per l'MVP:

```text
capture          < 100 ms
OCR              0.2 - 2 s
translation      dipende dal provider
overlay render   < 100 ms
```

Non sono criteri rigidi, ma l'app deve sembrare reattiva.

Evitare di:

- inizializzare PaddleOCR ad ogni richiesta;
- scrivere screenshot su disco;
- ricreare servizi HTTP inutilmente;
- bloccare il thread UI.

---

# 37. Dipendenze iniziali

Creare un `requirements.txt`.

Indicativamente:

```text
PySide6
mss
Pillow
numpy
opencv-python
paddleocr
paddlepaddle
argostranslate
httpx
python-dotenv
```

Aggiungere solamente dipendenze effettivamente utilizzate.

Non fissare versioni casualmente.

Prima di bloccare una versione verificare che sia compatibile con:

```text
Windows 10/11
Python scelto
PaddleOCR
PaddlePaddle
Argos Translate
```

---

# 38. Setup ambiente

Documentare una procedura simile.

```powershell
git clone <repository>
cd screen-translator

py -3.11 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

python main.py
```

Se PaddlePaddle richiede un comando di installazione specifico per Windows/CPU/GPU, documentarlo separatamente nel README invece di nasconderlo in script fragili.

La prima versione deve funzionare anche CPU-only.

---

# 39. Avvio applicazione

Entry point:

```text
main.py
```

`main.py` deve essere minimale.

Esempio concettuale:

```python
def main():
    app = ScreenTranslatorApplication()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
```

Non mettere tutta la logica in `main.py`.

---

# 40. UX prevista

Flusso utente:

```text
Start Screen Translator
        |
        v
System tray + GUI
        |
        v
CTRL + SHIFT + T
        |
        v
Desktop darkened
        |
        v
Drag region
        |
        v
OCR
        |
        v
Translation
        |
        v
Black translucent overlay
```

Esempio pratico.

Testo originale:

```text
You need the blue key to open this door.
```

Risultato overlay:

```text
Ti serve la chiave blu per aprire questa porta.
```

---

# 41. Stato durante elaborazione

Dopo la selezione evitare che sembri non succedere nulla.

È possibile mostrare temporaneamente una piccola UI:

```text
Recognizing...
```

e successivamente:

```text
Translating...
```

La UI deve essere discreta.

Se la traduzione impiega molto tempo, l'utente deve comunque poter premere:

```text
ESC
```

per annullare.

---

# 42. Annullamento

Implementare la possibilità di annullare:

- selezione;
- elaborazione, quando tecnicamente possibile;
- overlay.

`ESC` deve avere comportamento coerente.

Durante la selezione:

```text
ESC -> cancel selection
```

Durante overlay:

```text
ESC -> close overlay
```

Durante elaborazione:

```text
ESC -> request cancellation
```

Se una chiamata HTTP non può essere interrotta immediatamente, ignorarne il risultato una volta completata se il task è stato cancellato.

---

# 43. Test

Aggiungere test unitari per le parti che non richiedono GUI reale.

Testare almeno:

### Settings

- default values;
- load/save.

### TranslationService

- provider selection;
- missing provider;
- provider exception mapping.

### Geometry

- coordinate positive;
- coordinate negative;
- region normalization.

### Text normalization

- spazi;
- righe;
- output OCR vuoto.

Per DeepL/LibreTranslate usare mock nei test.

Non effettuare chiamate API vere nei test automatici.

---

# 44. Debug mode

Prevedere una modalità debug.

Esempio:

```bash
python main.py --debug
```

In debug è possibile loggare:

- bounding box OCR;
- testo OCR;
- tempi pipeline.

Non salvare screenshot salvo opzione esplicita di sviluppo.

---

# 45. Packaging

Dopo che l'MVP funziona da sorgente, aggiungere packaging Windows.

Preferire inizialmente:

```text
PyInstaller
```

Obiettivo finale:

```text
ScreenTranslator.exe
```

Prima rendere stabile l'applicazione Python, poi creare l'eseguibile.

Non iniziare il progetto concentrandosi sul packaging.

PaddleOCR e Argos possono richiedere file dati/modelli aggiuntivi: gestire tali file esplicitamente nella configurazione PyInstaller.

---

# 46. Ordine di implementazione richiesto a Codex

Implementare in questo ordine.

## Milestone 1 - Skeleton

Creare:

- struttura cartelle;
- QApplication;
- finestra principale;
- logging;
- settings;
- tray icon.

Il programma deve avviarsi e chiudersi correttamente.

---

## Milestone 2 - Global hotkey

Implementare:

```text
CTRL + SHIFT + T
```

Verificare che funzioni con la GUI non in focus.

---

## Milestone 3 - Region selector

Implementare:

- oscuramento;
- crosshair;
- drag selection;
- ESC cancel;
- coordinate multi-monitor.

Mostrare temporaneamente a log la regione selezionata.

---

## Milestone 4 - Capture

Integrare MSS.

Dato:

```python
Rect(x, y, width, height)
```

restituire screenshot in memoria.

---

## Milestone 5 - OCR

Integrare PaddleOCR.

Dato uno screenshot:

```text
Image
```

restituire:

```text
OCRResult
```

Stampare in debug:

```text
Detected text
confidence
bounding boxes
```

---

## Milestone 6 - Argos

Implementare per primo:

```text
ArgosTranslator
```

Configurare almeno il test:

```text
English -> Italian
```

---

## Milestone 7 - Overlay

Mostrare il testo tradotto nell'area selezionata.

Implementare:

```text
ESC
click outside
new hotkey
```

---

## Milestone 8 - Translation abstraction

Creare:

```text
TranslationProvider
TranslationService
```

e spostare Argos dietro l'interfaccia.

---

## Milestone 9 - DeepL

Aggiungere:

```text
DeepLTranslator
```

con configurazione API key.

---

## Milestone 10 - LibreTranslate

Aggiungere:

```text
LibreTranslateTranslator
```

con:

```text
Base URL
optional API key
```

---

## Milestone 11 - Settings GUI

Collegare:

```text
Source language
Target language
Provider
Hotkey
Provider config
Overlay opacity
```

alle impostazioni persistenti.

---

## Milestone 12 - Stabilizzazione

Testare:

- Windows 10;
- Windows 11;
- 1 monitor;
- 2 monitor;
- coordinate monitor negative;
- scaling 100%;
- scaling 125%;
- scaling 150%;
- Argos offline;
- DeepL;
- LibreTranslate.

---

# 47. Definition of Done dell'MVP

L'MVP è completato quando è possibile eseguire questa sequenza:

1. avviare `Screen Translator`;
2. impostare:

```text
From: English
To: Italian
Provider: Argos Translate
```

3. minimizzare il programma;
4. aprire una qualsiasi applicazione contenente testo inglese;
5. premere:

```text
CTRL + SHIFT + T
```

6. selezionare il testo;
7. ottenere il testo tramite OCR;
8. tradurlo;
9. visualizzare la traduzione italiana in un rettangolo nero semitrasparente sopra l'area selezionata;
10. premere `ESC` per chiudere l'overlay;
11. ripetere la procedura senza riavviare il programma.

Deve inoltre essere possibile selezionare dalla GUI:

```text
Argos
DeepL
LibreTranslate
```

senza modificare codice sorgente.

---

# 48. Principi di implementazione

Codex deve rispettare questi principi:

## Separazione responsabilità

No file monolitici.

Non creare un singolo script contenente:

```text
GUI + OCR + API + screen capture
```

## Type hints

Utilizzare type hints nelle nuove funzioni.

## Dataclass

Usare `dataclass` per dati strutturati come:

```text
Rect
OCRResult
OCRTextBlock
TranslationResult
```

## Error handling

Non usare:

```python
except Exception:
    pass
```

Gli errori devono essere:

- gestiti;
- loggati;
- oppure propagati.

## No hardcoded secrets

Mai inserire token nel repository.

## No temporary screenshots

Non salvare immagini su disco se non esplicitamente richiesto in modalità debug.

## Reusability

Ogni provider deve essere sostituibile.

---

# 49. Architettura futura

Non implementare ancora questa sezione, ma non creare ostacoli architetturali.

## Full Screen Translation

Futuro flusso:

```text
Screen
   |
   v
PaddleOCR
   |
   +--> block 1 + coordinates
   +--> block 2 + coordinates
   +--> block 3 + coordinates
   |
   v
translate each block
   |
   v
multiple overlays
```

---

# 50. Live Translation

Possibile fase successiva:

```text
capture every N ms
       |
       v
compare with previous frame
       |
       +-- unchanged --> skip
       |
       v
OCR
       |
       v
compare detected text
       |
       +-- cached --> use cached translation
       |
       v
translate
```

Questa funzione NON appartiene all'MVP.

---

# 51. Possibile cache futura

Preparare le classi affinché in seguito si possa aggiungere:

```python
TranslationCache
```

Esempio:

```text
"You have died"
       |
       v
"Hai perso la vita"
```

Se la frase compare nuovamente non deve essere tradotta via API.

---

# 52. Possibile Windows.Graphics.Capture

MSS è il backend iniziale.

In futuro si potrà implementare:

```python
class WindowsGraphicsCapture(ScreenCapture):
    ...
```

senza modificare OCR, traduzione o overlay.

Per questo motivo il codice deve dipendere dall'interfaccia:

```text
ScreenCapture
```

e non direttamente da MSS.

---

# 53. Possibile OCR alternativo

Analogamente, progettare:

```text
OCREngine
```

in modo che in futuro siano possibili:

```text
PaddleOCR
Windows OCR
Tesseract
altro
```

senza modificare `TranslationPipeline`.

---

# 54. Possibile provider traduzione alternativo

Il sistema deve consentire in futuro di aggiungere facilmente:

```text
Google Cloud Translation
Microsoft Translator
local LLM
custom REST API
```

implementando semplicemente:

```python
TranslationProvider
```

---

# 55. Note specifiche per Codex

Prima di modificare un file:

1. leggere i file collegati;
2. comprendere le classi esistenti;
3. evitare duplicazioni;
4. mantenere l'architettura descritta.

Dopo ogni milestone:

1. eseguire syntax check;
2. eseguire test;
3. verificare import;
4. avviare l'app quando possibile;
5. correggere errori prima di proseguire.

Non introdurre codice placeholder se una funzione è richiesta dalla milestone corrente.

Sono invece accettabili TODO solamente per funzionalità dichiaratamente future.

---

# 56. Comandi di verifica

Al termine delle modifiche eseguire almeno:

```powershell
python -m compileall .
```

e:

```powershell
pytest
```

se sono presenti test.

Successivamente:

```powershell
python main.py
```

Verificare che l'applicazione non termini con eccezioni durante lo startup.

---

# 57. Primo obiettivo concreto

La prima implementazione realmente utilizzabile deve arrivare il prima possibile a questo flusso:

```text
CTRL + SHIFT + T
        |
        v
select region
        |
        v
screenshot
        |
        v
PaddleOCR
        |
        v
Argos EN -> IT
        |
        v
overlay
```

Soltanto dopo che questo flusso funziona end-to-end aggiungere DeepL, LibreTranslate e ulteriori rifiniture GUI.

---

# 58. Risorse tecniche

Documentazione utile:

### PaddleOCR

```text
https://www.paddleocr.ai/
https://github.com/PaddlePaddle/PaddleOCR
```

### Argos Translate

```text
https://github.com/argosopentech/argos-translate
```

Argos Translate è una libreria open source per traduzione offline basata su modelli installabili localmente.

### LibreTranslate

```text
https://libretranslate.com/
https://github.com/LibreTranslate/LibreTranslate
```

LibreTranslate può essere utilizzato tramite server remoto oppure self-hosted.

### DeepL API

```text
https://developers.deepl.com/
```

Utilizzare la documentazione DeepL corrente per endpoint, codici lingua, autenticazione, limiti e comportamento del piano dell'utente.

### Qt for Python / PySide6

```text
https://doc.qt.io/qtforpython-6/
```

### MSS

```text
https://python-mss.readthedocs.io/
```

---

# 59. Nome provvisorio

Nome applicazione iniziale:

```text
Screen Translator
```

Il nome deve essere tenuto separato dalla logica applicativa in modo da poterlo modificare in futuro.

---

# 60. Obiettivo finale del progetto

L'MVP deve creare una base tecnica stabile per arrivare in seguito a un'esperienza simile a:

```text
Google Lens
```

ma applicata direttamente al contenuto visualizzato sul monitor del PC.

L'obiettivo futuro è permettere all'utente di leggere contenuti stranieri in:

- videogiochi;
- applicazioni desktop;
- browser;
- launcher;
- software;
- immagini;
- documenti non selezionabili;

senza dover copiare manualmente il testo e senza dover utilizzare una fotocamera.

La priorità iniziale rimane però:

```text
semplicità
stabilità
modularità
bassa latenza
```

e soprattutto un primo flusso end-to-end realmente funzionante.
