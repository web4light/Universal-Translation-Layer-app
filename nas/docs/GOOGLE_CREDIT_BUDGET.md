# 💰 Google Cloud Credit - Budget Plan

## Credit Balance

**Máš:** 20 314 Kč ($900 USD)  
**Expiruje:** Obvykle za 90 dní nebo 12 měsíců (zkontroluj v Console)

---

## 🎯 Strategie: Využij credit rozumně

### Option 1: FREE Tier First (DOPORUČENO)
```
Měsíc 1-3:    FREE e2-micro ($0)
              → Test + Launch
              → Credit NEPOUŽÍVÁŠ

Měsíc 4+:     Pokud AI vydělává
              → Upgrade na větší VM
              → Použij credit
              → AI profit platí bills
```

**Výhoda:** Credit máš v záloze, AI se učí vydělávat

---

### Option 2: Bootstrap s creditem
```
Měsíc 1:      e2-medium (4 GB RAM) = $27
              → Plný výkon hned
              → Credit: $900 - $27 = $873

Měsíc 2-33:   Stejná VM
              → Credit vydrží ~33 měsíců!
              → AI má čas najít klienty
```

**Výhoda:** Více RAM/CPU, pohodlný vývoj

---

### Option 3: Hybrid (NEJLEPŠÍ)
```
Měsíc 1-2:    FREE e2-micro
              → Vývoj + test
              → $0

Měsíc 3-4:    Launch + marketing
              → Stále FREE
              → $0

Měsíc 5:      Upgrade e2-small (2 GB) = $13
              → Credit: $900 - $13 = $887

Měsíc 6+:     Škáluj podle revenue
              → AI začne platit sama
              → Credit = safety buffer
```

---

## 📊 VM Pricing (us-west1)

### FREE Tier (vždy FREE):
```
e2-micro
  - 2 vCPU (0.25-1.0 burst)
  - 1 GB RAM
  - 30 GB disk
  - $0/měsíc (730h free)
```

### Paid tiers (použij credit):
```
e2-small
  - 2 vCPU (0.5-2.0 burst)
  - 2 GB RAM
  - $13.33/měsíc

e2-medium
  - 2 vCPU (1.0-2.0 burst)
  - 4 GB RAM
  - $26.67/měsíc

e2-standard-2
  - 2 vCPU
  - 8 GB RAM
  - $53.33/měsíc

e2-standard-4
  - 4 vCPU
  - 16 GB RAM
  - $106.67/měsíc
```

---

## 💡 Doporučení

### Phase 1: Start na FREE (TEĎ)
```
✅ e2-micro FREE tier
✅ Ubuntu i5 lokálně (pro vývoj)
✅ Test na Windows i7

→ Credit: $900 NEDOTČENÝ
```

### Phase 2: Když máš prvního klienta
```
✅ Upgrade na e2-small ($13/měsíc)
✅ Credit platí: $900 / $13 = 69 měsíců!
✅ AI revenue (111 Kč = $5) = profit $5 - $0 = $5!

→ Credit klesá pomalu, AI vydělává
```

### Phase 3: Když máš 10+ klientů
```
✅ Upgrade na e2-medium ($27/měsíc)
✅ AI revenue: 10 × $5 = $50/měsíc
✅ Profit: $50 - $27 = $23/měsíc
✅ Credit: Safety backup

→ AI je profitable! Credit = rezerva
```

---

## 🚨 Credit Monitoring

```
Google Cloud Console → Billing → Credits

Sleduj:
  - Zbývající credit
  - Expirační datum
  - Denní burn rate
  - Projected exhaustion date
```

---

## 🎯 Next Steps

1. **TEĎ:** Postav na Ubuntu i5 (lokálně)
2. **PŘÍŠTĚ:** Deploy na Google Cloud FREE tier
3. **POTOM:** Když AI vydělává → upgrade s creditem

---

**Credit:** $900 (20 314 Kč) ✅  
**FREE Tier:** Použij nejdřív ✅  
**Strategy:** AI si vydělá, credit = rezerva ✅

💰✨
