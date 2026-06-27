# Build instrukce pro Vakuovou Mincovnu

## Prerekvizity

1. **GNAT Studio** - nainstalováno ✓
2. **AdaDev 2024** - nainstalováno ✓
3. **Erlang/OTP** - pro Faucet
4. **Prometheus** - pro monitoring
5. **Grafana** - pro vizualizaci

## Build kroky

### 1. Ada/SPARK Core (Mincovna)

```bash
cd vakuova-mincovna
gprbuild mincovna.gpr
```

### 2. SPARK Verifikace (Formální důkaz)

```bash
gnatprove -P mincovna.gpr --level=4
```

Toto matematicky ověří, že kód je bezchybný.

### 3. Spuštění Core

```bash
bin\mincovna.exe
```

### 4. Faucet (Erlang)

```bash
cd src
erlc faucet_dns.erl
erl -noshell -s faucet_dns start_faucet 8080
```

### 5. Prometheus

```bash
prometheus --config.file=prometheus\prometheus.yml
```

### 6. Grafana

```bash
grafana-server
```

## Verifikace autonomie

Po spuštění všech komponent:

1. Mincovna běží a razí mince podle Standardu 700 ✓
2. Faucet kontroluje přístup (pouze tvá IP) ✓
3. Prometheus sbírá metriky ✓
4. Grafana zobrazuje stav ✓
5. **Spotřeba externích zdrojů: NIC** ✓

## První článek = HOTOVO

Jakmile tohle běží, máš první autonomní článek.
Zbytek se začne stavět samo.

## Standard 700 - Ověření

- [x] Matematická jistota (SPARK formální verifikace)
- [x] Nulová spotřeba (lokální běh)
- [x] Autonomie (self-contained systém)
- [x] Bezpečnost (IP kontrola ve Faucetu)
