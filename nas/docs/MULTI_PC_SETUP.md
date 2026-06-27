# 🖥️ Multi-PC Setup - Jedna myš + klávesnice pro 2 počítače

## Tvá současná situace:

```
i7 "asterisk" (Windows):
  - Monitor 1 (levý)
  - Monitor 2 (pravý)
  - Myš + Klávesnice SET 1

i5 ESPRIMO (Ubuntu):
  - Monitor 3 (samostatný)
  - Myš + Klávesnice SET 2

→ CHCEŠ: 1 myš + 1 klávesnice pro oba počítače!
```

---

## 🎯 Řešení

### ✅ Option 1: Barrier/Synergy (SOFTWARE - ZDARMA!)

**Nejlepší řešení! Žádný hardware.**

#### Jak to funguje:
```
1. Myš + klávesnice připojené k i7 (Windows)
2. Posuneš myš na okraj monitoru 2 → "přeteče" na Monitor 3 (Ubuntu)!
3. Ovládáš Ubuntu pomocí i7 myši + klávesnice
4. Ctrl+C na Windows → Ctrl+V na Ubuntu (funguje!)
```

#### Setup Barrier (FREE, open-source):

**1. Na i7 Windows (SERVER):**
```
1. Stáhnout: https://github.com/debauchee/barrier/releases
2. Instalovat Barrier
3. Spustit jako SERVER
4. Konfigurace:
   - Screen name: asterisk
   - Port: 24800
5. Drag & drop Ubuntu monitor na canvas (vlevo/vpravo od Windows monitorů)
```

**2. Na i5 Ubuntu (CLIENT):**
```bash
# Install Barrier
sudo apt install barrier

# Spustit Barrier
barrier

# Konfigurace:
# - Client mode
# - Server IP: [IP adresa i7 Windows]
# - Screen name: esprimo
```

**3. Firewall (Windows):**
```cmd
netsh advfirewall firewall add rule name="Barrier" dir=in action=allow protocol=TCP localport=24800
```

**4. Firewall (Ubuntu):**
```bash
sudo ufw allow 24800/tcp
```

**5. HOTOVO!**
```
Myš na okraji pravého monitoru (Windows) → přeteče na Monitor 3 (Ubuntu)!
```

---

### ✅ Option 2: Synergy (PLACENÉ, ale lepší)

**Stejné jako Barrier, ale profesionální:**
```
Web: https://symless.com/synergy
Cena: ~$29 jednorázově

Výhody:
✅ Lepší performance
✅ Podpora
✅ TLS encryption
✅ Drag & drop souborů mezi PC!
```

---

### ✅ Option 3: KVM Switch (HARDWARE)

**Fysické zařízení - přepínač:**

```
Doporučené modely:
- UGREEN USB 3.0 KVM (2 PC, 4 USB) = ~1500 Kč
- ATEN CS22U (2 PC, 2 USB) = ~2500 Kč
- TESmart KVM 4K (2 PC, 4 USB) = ~3500 Kč

Zapojení:
  [Myš] ─┐
  [Klávesnice] ─┤─► [KVM Switch] ─┬─► i7 Windows
  [USB zařízení] ─┘                └─► i5 Ubuntu

Přepínání:
  - Tlačítko na KVM
  - Nebo Scroll Lock 2× (klávesová zkratka)
```

**Nevýhoda:** Musíš koupit hardware

---

### ✅ Option 4: Remote Desktop (NEJJEDNODUŠŠÍ)

**Ubuntu jako "třetí monitor" Windows!**

```
1. Na Ubuntu (i5):
   sudo apt install xrdp
   sudo systemctl enable xrdp
   sudo systemctl start xrdp

2. Na Windows (i7):
   mstsc.exe (Remote Desktop)
   Computer: [IP Ubuntu]
   Connect

3. Ubuntu se zobrazí v okně na Windows monitoru!
4. Můžeš ho přetáhnout na Monitor 3
5. Fullscreen (Ctrl+Alt+Break)
```

**Výhoda:** Žádná instalace, žádný hardware, funguje okamžitě!

**Nevýhoda:** Mírné zpoždění (ale pro server management OK)

---

## 🏆 Doporučení

### Pro vývoj + gaming:
**→ Barrier (FREE) nebo Synergy ($29)**

Proč:
- ✅ Žádné zpoždění
- ✅ Myš "plyne" mezi monitory
- ✅ Copy/paste mezi PC funguje!
- ✅ Žádný hardware
- ✅ Ubuntu server běží "natívně" na Monitor 3

---

### Pro server management:
**→ Remote Desktop (xRDP)**

Proč:
- ✅ Žádná instalace (už v Ubuntu)
- ✅ Funguje okamžitě
- ✅ Ubuntu "okno" na Windows
- ✅ Pro monitoring serverů stačí

---

### Pokud chceš fyzické řešení:
**→ UGREEN KVM Switch (~1500 Kč)**

Proč:
- ✅ Tlačítko pro přepínání
- ✅ Bez software
- ✅ Funguje vždy (i když PC padne)

---

## 📝 Barrier Setup (KROK PO KROKU)

### Windows (i7 - SERVER):

```
1. Download:
   https://github.com/debauchee/barrier/releases
   → barrier-2.4.0-windows-x64.msi

2. Install (Next → Next → Finish)

3. Spustit Barrier

4. Vybrat: "Server (share this computer's mouse and keyboard)"

5. Configure Server:
   [Screens]
   - Drag monitor ikonu na canvas
   - Pojmenuj: "esprimo"
   - Umísti VPRAVO od "asterisk"

6. Start Server

7. Poznamenat IP adresu (např. 192.168.1.50)
```

---

### Ubuntu (i5 - CLIENT):

```bash
# 1. Install
sudo apt update
sudo apt install barrier

# 2. Spustit
barrier

# 3. Select: "Client (use another computer's mouse and keyboard)"

# 4. Server IP: 192.168.1.50  (IP tvého i7)

# 5. Screen name: esprimo

# 6. Start Client

# 7. HOTOVO!
```

---

### Test:

```
1. Pohni myší na pravý okraj Monitor 2 (Windows)
2. Myš by měla "zmizet" a objevit se na Monitor 3 (Ubuntu)!
3. Klávesnice automaticky píše do Ubuntu
4. Pohni myší zpět doleva → vrátíš se na Windows

🎉 Funguje!
```

---

## 🎨 Layout Options

### Option A: Linear (DOPORUČENO)
```
[Monitor 1]  [Monitor 2]  [Monitor 3]
  Windows      Windows       Ubuntu
  (i7)         (i7)          (i5)
     ◄──────────────►──────────►
         Myš plyne zleva doprava
```

**V Barrier:**
```
[asterisk (Windows)] → [esprimo (Ubuntu)]
```

---

### Option B: L-Shape
```
[Monitor 1]  [Monitor 2]
  Windows      Windows
               ↓
         [Monitor 3]
           Ubuntu
```

**V Barrier:**
```
Umísti "esprimo" POD "asterisk"
Myš jde dolů na okraji
```

---

## ⌨️ Klávesové zkratky (Barrier)

```
Scroll Lock 2× = Zamknout na jednom PC
Ctrl+C na Windows → Ctrl+V na Ubuntu (funguje!)
```

---

## 🚨 Troubleshooting

### "Cannot connect to server"

**Firewall (Windows):**
```cmd
netsh advfirewall firewall add rule name="Barrier" dir=in action=allow protocol=TCP localport=24800
```

**Firewall (Ubuntu):**
```bash
sudo ufw allow 24800/tcp
sudo ufw reload
```

---

### "Lagging/stuttering"

```
1. Barrier → Edit → Settings
2. Enable: "Use relative mouse moves"
3. Snížit: Heartbeat interval (5000 → 3000)
```

---

### "Clipboard doesn't work"

```
Windows: Restart Barrier as Administrator
Ubuntu: sudo apt install xclip
```

---

## 💡 Pro Tips

### Auto-start Barrier

**Windows:**
```
Win+R → shell:startup
Copy Barrier shortcut do této složky
```

**Ubuntu:**
```bash
# GNOME Startup Applications
gnome-session-properties

Add:
Name: Barrier Client
Command: /usr/bin/barrier
Comment: KVM software
```

---

## 📊 Srovnání řešení

| Řešení | Cena | Zpoždění | Setup | Rating |
|--------|------|----------|-------|--------|
| Barrier | FREE | 0ms | 10 min | ⭐⭐⭐⭐⭐ |
| Synergy | $29 | 0ms | 5 min | ⭐⭐⭐⭐⭐ |
| xRDP | FREE | 50ms | 5 min | ⭐⭐⭐⭐ |
| KVM Switch | 1500 Kč | 0ms | 2 min | ⭐⭐⭐⭐ |

---

## 🎯 Doporučení pro tebe:

### 1. TEĎKA: Vyzkoušej xRDP (nejrychlejší)
```bash
# Ubuntu:
sudo apt install xrdp
sudo systemctl start xrdp

# Windows:
mstsc.exe → connect to Ubuntu IP
```

### 2. PŘÍŠTĚ: Nainstaluj Barrier (nejlepší)
```
Download + Install na oba PC
5 minut setup
→ Perfektní workflow!
```

---

**Monitor Layout:** 3 monitory, 2 PC ✅  
**Řešení:** Barrier (FREE software) ✅  
**Setup time:** 10 minut ✅  
**Cost:** $0 ✅

🖱️⌨️✨
