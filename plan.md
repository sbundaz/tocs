# Review "lock della profondità TOC" + fix bug + aggiornamento test/doc

## Contesto
L'obiettivo della modifica è evitare di dover ripassare `--depth N` ad ogni
: la prima voesecuzionelta che viene specificato, il valore viene scritto come
riga `<!-- depth=N -->` dentro il blocco TOC (`generate_toc` in
`tocs/main.py:55-102`); nelle esecuzioni successive senza `--depth` questo
marker viene letto e riapplicato ("lock"). `--clear-depth` deve rimuovere il
lock e tornare a generare la TOC senza limite di profondità.

Ho verificato la logica eseguendo `pytest -q` e alcuni casi manuali. La logica
di lock/override/clear è corretta, ma sono emersi **2 bug reali** introdotti
nel corso delle modifiche di questa sessione, quindi non procedo direttamente
con l'aggiornamento di test/doc come richiesto ("se l'implementazione è ok
senza bug procedi") senza prima sistemarli.

## Bug trovati (da correggere prima di tutto)

1. **`create_toc_row` non ha più un default per `max_depth`**
   (`tocs/main.py:9-11`): l'annotazione di tipo aggiunta in questa sessione ha
   perso il valore di default `= None`. Rompe 8 test esistenti che chiamano
   `create_toc_row(header, {})` con solo 2 argomenti
   (`TypeError: missing 1 required positional argument: 'max_depth'`).
   Fix: `max_depth: int | None = None`.

2. **`IndexError` non gestito in `generate_toc`** (`tocs/main.py:76-78`):
   `original_lines[init_toc_position + 1]` viene letto senza controllare che
   esista una riga successiva. Se `<!-- init-tocs -->` è l'ultima riga del
   file (file troncato/malformato), il programma va in traceback invece di
   restituire il consueto errore "Missing or invalid TOC markers" (verificato
   riproducendo il caso a mano). Fix: controllare
   `init_toc_position + 1 < len(original_lines)` prima del match.

## Nit (miglioria, non bloccante)

3. Il parsing del numero usa uno slice hardcoded `[11:-4]`
   (`tocs/main.py:79`) invece di un gruppo di cattura nella regex — fragile se
   il testo del marker cambia ancora. Passo a
   `re.fullmatch(r"<!-- depth=(\d+) -->", ...)` e uso `match.group(1)`.

4. `--depth N --clear-depth` insieme: `clear_depth` fa `continue` prima del
   controllo su `max_depth`, quindi `--depth` viene silenziosamente ignorato.
   Non aggiungo una validazione nuova (fuori scope, comportamento comunque
   deterministico) ma lo documento esplicitamente in README/help.

## Modifiche

- `tocs/main.py`
  - Ripristinare `max_depth: int | None = None` in `create_toc_row`.
  - Guardia sui limiti prima di leggere `original_lines[init_toc_position + 1]`.
  - Regex con gruppo di cattura per estrarre il numero, niente slice manuale.

- `tests/fixtures/lorem_ipsum_depth_2_output.md`
  - Aggiornare l'output atteso includendo la riga `<!-- depth=2 -->` che ora
    viene scritta nel blocco TOC (comportamento nuovo e voluto).

- `tests/test_toc.py`
  - Nuovo test: seconda esecuzione senza `--depth` mantiene il lock
    (rigenera con lo stesso `max_depth` letto dal marker).
  - Nuovo test: `--clear-depth` rimuove il marker e la TOC torna completa
    (nessun limite di profondità).
  - Nuovo test di regressione per il bug #2: file con `<!-- init-tocs -->`
    come ultima riga → deve restituire l'errore standard, non un traceback.

- `README.md`
  - Documentare `--clear-depth`.
  - Spiegare il comportamento di "lock": una volta impostato `--depth`,
    viene ricordato nei run successivi finché non si passa un nuovo
    `--depth` o `--clear-depth`.

## Verifica
- `pytest -q` deve passare tutti i test (attualmente 9 falliscono: 8 per il
  bug #1, 1 per il fixture da aggiornare).
- Test manuale: `echo '<!-- init-tocs -->' > /tmp/edge.md && python3 tocs/main.py /tmp/edge.md` deve stampare l'errore standard invece di un traceback.
