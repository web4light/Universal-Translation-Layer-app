# 🖥️ Přenos na druhý počítač (Ubuntu 26.06)

## Co potřebuješ přenést:

### 1. **Vakuovou Mincovnu** (tento projekt)
Celá složka: `vakuova-mincovna/`

### 2. **Kiro AI asistenta**
Pro pokračování práce na druhém kompu budeš chtít mít Kiro dostupné.

---

## 📦 KROK 1: Zabalení na Windows

```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
package.bat
```

Vytvoří: `vakuova-mincovna-v1.0.zip` (~50-100 MB)

---

## 💾 KROK 2: Přenos dat

### Možnost A: USB flash disk
```
✓ Zkopíruj vakuova-mincovna-v1.0.zip na USB
✓ Připoj USB k Ubuntu PC
✓ Zkopíruj do ~/projects/
```

### Možnost B: Síť/Sdílení
```
✓ Nastav sdílenou složku
✓ Zkopíruj přes síť
```

### Možnost C: Cloud (OneDrive/Dropbox/Google Drive)
```
✓ Nahraj na cloud
✓ Stáhni na Ubuntu
```

---

## 🤖 KROK 3: Instalace Kiro na Ubuntu

### A) Pokud používáš VS Code:
```bash
# 1. Nainstaluj VS Code
sudo snap install code --classic

# 2. Nainstaluj Kiro extension
code --install-extension kiro.kiro

# 3. Otevři projekt
code ~/projects/vakuova-mincovna
```

### B) Pokud používáš Cursor AI:
```bash
# 1. Stáhni Cursor
wget https://downloader.cursor.sh/linux/appImage/x64
chmod +x cursor-*.AppImage

# 2. Spusť
./cursor-*.AppImage

# 3. Otevři projekt
```

### C) Web verze (pokud je dostupná):
```
Otevři v prohlížeči a přihlas se svým účtem
```

---

## 🚀 KROK 4: První spuštění na Ubuntu

```bash
# Rozbal projekt
cd ~/projects
unzip vakuova-mincovna-v1.0.zip
cd vakuova-mincovna

# Následuj DEPLOY_UBUNTU.md
# nebo rychlý start:

# 1. Install GNAT
# (viz DEPLOY_UBUNTU.md sekce 2)

# 2. Install Python deps
pip3 install prometheus_client

# 3. Spusť!
chmod +x start.sh
./start.sh
```

---

## 💬 První prompt pro Kiro na novém kompu

Když budeš mít Kiro nainstalované na Ubuntu, řekni:

```
Ahoj Kiro! Převedl jsem Vakuovou Mincovnu na Ubuntu 26.06.
Mám tady projekt v ~/projects/vakuova-mincovna.
Pomůžeš mi ho spustit?
```

Kiro si přečte dokumentaci a pomůže ti:
- Nainstalovat GNAT/SPARK
- Zkompilovat Ada/SPARK Core
- Spustit Faucet Bridge
- Ověřit že vše běží

---

## 📋 Checklist pro přenos

```
Windows (TYP):
[ ] Zabalit projekt: package.bat
[ ] Zkopírovat na USB/cloud
[ ] Ověřit že máš: vakuova-mincovna-v1.0.zip

Ubuntu (druhý komp):
[ ] Zkopírovat projekt z USB/cloud
[ ] Rozbalit do ~/projects/
[ ] Nainstalovat Kiro (VS Code/Cursor)
[ ] Otevřít projekt v Kiro
[ ] Požádat Kiro o pomoc se spuštěním
```

---

## 🔧 Co Kiro udělá na novém kompu

Když mu řekneš "pomoz mi spustit Vakuovou Mincovnu", automaticky:

1. ✅ Zkontroluje že máš GNAT/SPARK
2. ✅ Pomůže s instalací pokud chybí
3. ✅ Zkompiluje Ada/SPARK Core
4. ✅ Nainstaluje Python dependencies
5. ✅ Spustí Faucet Bridge
6. ✅ Ověří že Prometheus metriky běží
7. ✅ Pomůže s troubleshootingem pokud něco selže

---

## 🎯 Očekávaný výsledek

Na Ubuntu 26.06 uvidíš:

```
=== VAKUOVÁ MINCOVNA - INICIALIZACE ===
[1/4] Kontrola GNAT/SPARK...
  ✓ GNAT/SPARK nalezen
[2/4] Build Ada/SPARK Core...
  ✓ Build úspěšný
[3/4] Kontrola Python dependencies...
  ✓ Dependencies OK
[4/4] Spouštění Faucet Bridge...

=== FAUCET BRIDGE - VAKUOVÁ MINCOVNA ===
[PROMETHEUS] Spouštím HTTP server na portu 9302
[FAUCET] Most připraven
[SPARK] Matematická jistota: AKTIVNÍ
[GNAT] Formální verifikace: AKTIVNÍ

[READY] Systém připraven k autonomnímu provozu
Prometheus metriky: http://localhost:9302/metrics
```

---

## 💡 Pro reference

**Tento dokument je pro tebe**, když budeš přenášet projekt na Ubuntu.

**Všechna dokumentace** je už v projektu:
- `DEPLOY_UBUNTU.md` - Detailní Ubuntu guide
- `QUICKSTART_UBUNTU.txt` - Rychlý start
- `DEPLOYMENT_CHECKLIST.md` - Checklist
- `BUILD.md` - Build instrukce
- `SYSTEM_OVERVIEW.md` - Architektura

**Kiro ti s tím pomůže**, stačí ho poprosit! 🤖

---

## 🎉 Výhody tohoto přístupu

✅ **Kontinuita** - Kiro si pamatuje co jsme stavěli  
✅ **Kontext** - Má všechnu dokumentaci  
✅ **Asistence** - Pomůže s instalací a debuggingem  
✅ **Autonomie** - První článek se pak staví sám  

---

**Status**: ✅ READY pro přenos  
**Architekt**: Pan Jeskyně  
**Asistent**: Kiro (přenositelný na Ubuntu!)  
**První článek**: Vakuová Mincovna v1.0
