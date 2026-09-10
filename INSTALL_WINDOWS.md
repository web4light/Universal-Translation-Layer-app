# 🪟 Návod k instalaci a spuštění na Windows

Tento repozitář je plně připraven pro běh na operačním systému **Windows 10 a Windows 11**.

---

## ⚡ Rychlý start na 2 kliknutí (Doporučeno)

1. **Dvakrát klikněte na:**
   ```cmd
   install_windows.bat
   ```
   *Skript automaticky ověří přítomnost Node.js, Pythonu a nainstaluje všechny npm balíčky.*

2. **Pro spuštění dvakrát klikněte na:**
   ```cmd
   start_windows.bat
   ```
   *Otevře se interaktivní menu, kde si jednoduše číslem vyberete, co chcete spustit.*

---

## 📋 Co je potřeba mít nainstalováno na Windows

Pokud na svém počítači ještě nemáte Node.js nebo Python, nainstalujete je nejsnáze přes Windows terminál pomocí `winget`:

```powershell
# 1. Instalace Node.js (LTS verze včetně npm)
winget install OpenJS.NodeJS.LTS

# 2. Instalace Pythonu
winget install Python.Python.3.11

# 3. Instalace Git (pokud ještě nemáte)
winget install Git.Git
```

---

## 🚀 Manuální příkazy z příkazové řádky (CMD / PowerShell)

Přímo v kořeni projektu můžete používat tyto sjednocené cross-platform příkazy:

| Příkaz | Co udělá |
| :--- | :--- |
| `npm run install:all` | Nainstaluje všechny závislosti pro 3D Avatar |
| `npm run dev` | Spustí 3D Avatar (Next.js) na `http://localhost:3000` |
| `npm run build` | Sestaví produkční balíček 3D avatara |
| `npm run dev:studio` | Spustí lokální Hackathon AI Studio na `http://localhost:8088` |
| `npm run ada:build` | Zkompiluje Ada/SPARK jádro (vyžaduje GNAT) |
| `npm run ada:run` | Spustí formální test jádra (funguje automaticky s `.exe`) |

---

## 🧩 Jak nainstalovat Chrome Rozšíření (Asistent v RAM) na Windows

1. Spusťte Google Chrome.
2. Do adresního řádku zadejte: `chrome://extensions`
3. Vpravo nahoře **zapněte přepínač „Režim pro vývojáře“** (*Developer mode*).
4. Klikněte vlevo nahoře na tlačítko **„Načíst rozbalené“** (*Load unpacked*).
5. Vyberte složku:
   ```text
   ...\Universal-Translation-Layer\extension
   ```
6. Rozšíření **Asterisk (*) — Sovereign WebMCP** se ihned aktivuje!
7. Klikněte na ikonu rozšíření nebo otevřete **Postranní panel (Side Panel)**, kde máte k dispozici svého AI asistenta s kompletním kontextem v RAM.

---

## 🛡️ Volitelné: Ada/SPARK vývojové prostředí pro Windows
Pro kompilaci a formální verifikaci SPARK jádra:
- Můžete využít oficiální instalátor Alire: `winget install Alire.Alr`
- Nebo spustit skript `install_ada.bat` v kořeni repozitáře.
